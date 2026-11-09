"""Step 5 of the pipeline: predict whether a cart session ends in a purchase."""
import json
import os
import pickle
import time

import numpy as np
import pandas as pd
from pyspark.ml import Pipeline
from pyspark.ml.classification import GBTClassifier, LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.sql import functions as F
from sklearn import ensemble, linear_model
from sklearn import metrics as skm
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler as SkScaler

FEATURE_COLS = ["n_views", "n_carts", "avg_price", "max_price", "n_products", "n_brands", "duration_secs", "is_weekend"]


def build_session_dataset(clean):
    """One row per cart session. Features use ONLY view and cart events (no data leakage)."""
    features = (
        clean.filter("event_type != 'purchase'")
        .groupBy("user_session")
        .agg(
            F.sum((F.col("event_type") == "view").cast("int")).alias("n_views"),
            F.sum((F.col("event_type") == "cart").cast("int")).alias("n_carts"),
            F.round(F.avg("price"), 2).alias("avg_price"),
            F.max("price").alias("max_price"),
            F.countDistinct("product_id").alias("n_products"),
            F.countDistinct("brand").alias("n_brands"),
            (F.unix_timestamp(F.max("event_ts")) - F.unix_timestamp(F.min("event_ts"))).alias("duration_secs"),
            F.max(F.col("is_weekend").cast("int")).alias("is_weekend"),
        )
        .filter("n_carts >= 1")
    )
    labels = clean.groupBy("user_session").agg(
        F.max((F.col("event_type") == "purchase").cast("double")).alias("label"))
    return features.join(labels, "user_session").fillna(0)


def train_spark_models(train, test):
    """Train three Spark MLlib models. Returns (results_rows, fitted_models)."""
    assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol="raw_features")
    scaler = StandardScaler(inputCol="raw_features", outputCol="scaled", withMean=True, withStd=True)
    logistic = LogisticRegression(featuresCol="scaled", maxIter=50, regParam=0.01)
    forest = RandomForestClassifier(featuresCol="raw_features", numTrees=60, maxDepth=7, seed=42)
    boosted = GBTClassifier(featuresCol="raw_features", maxIter=30, maxDepth=5, seed=42)
    candidates = {
        "Logistic Regression": [assembler, scaler, logistic],
        "Random Forest": [assembler, forest],
        "Gradient Boosted Trees": [assembler, boosted],
    }
    auc_eval = BinaryClassificationEvaluator(labelCol="label", metricName="areaUnderROC")
    acc_eval = MulticlassClassificationEvaluator(labelCol="label", metricName="accuracy")

    models, rows = {}, []
    for name, stages in candidates.items():
        t0 = time.time()
        model = Pipeline(stages=stages).fit(train)
        fit_secs = time.time() - t0
        prediction = model.transform(test)
        models[name] = model
        rows.append({"Framework": "Spark MLlib", "Algorithm": name, "AUC": auc_eval.evaluate(prediction),
                     "Accuracy": acc_eval.evaluate(prediction), "Train time (s)": fit_secs})
    return rows, models


def train_sklearn_models(train, test):
    """Train three scikit-learn models on the same split. Returns (rows, models, X_test)."""
    train_pdf, test_pdf = train.toPandas(), test.toPandas()
    x_train, y_train = train_pdf[FEATURE_COLS], train_pdf["label"].astype(int)
    x_test, y_test = test_pdf[FEATURE_COLS], test_pdf["label"].astype(int)
    models = {
        "Logistic Regression": make_pipeline(SkScaler(), linear_model.LogisticRegression(max_iter=1000)),
        "Random Forest": ensemble.RandomForestClassifier(n_estimators=200, max_depth=10, n_jobs=-1, random_state=42),
        "Hist Gradient Boosting": ensemble.HistGradientBoostingClassifier(max_iter=200, random_state=42),
    }
    rows = []
    for name, model in models.items():
        t0 = time.time()
        model.fit(x_train, y_train)
        fit_secs = time.time() - t0
        rows.append({
            "Framework": "scikit-learn", "Algorithm": name,
            "AUC": skm.roc_auc_score(y_test, model.predict_proba(x_test)[:, 1]),
            "Accuracy": skm.accuracy_score(y_test, model.predict(x_test)),
            "Train time (s)": fit_secs,
        })
    return rows, models, x_test


def run_ml(clean, models_dir, min_rows=50):
    """Full ML step. Returns a dictionary, or {'skipped': reason} when there is too little data."""
    ml_df = build_session_dataset(clean).cache()
    n_rows = ml_df.count()
    classes = ml_df.select("label").distinct().count()
    if n_rows < min_rows or classes < 2:
        ml_df.unpersist()
        return {"skipped": f"not enough data ({n_rows} cart sessions, {classes} class(es))"}

    train, test = ml_df.randomSplit([0.8, 0.2], seed=42)
    train.cache()
    test.cache()

    spark_rows, spark_models = train_spark_models(train, test)
    sk_rows, sk_models, x_test = train_sklearn_models(train, test)
    results = pd.DataFrame(spark_rows + sk_rows).sort_values("AUC", ascending=False).reset_index(drop=True)

    importance = pd.DataFrame({
        "Feature": FEATURE_COLS,
        "Importance": spark_models["Random Forest"].stages[-1].featureImportances.toArray(),
    }).sort_values("Importance", ascending=False).reset_index(drop=True)

    # save the scikit-learn models as .pkl files (+ the feature order) and check one can be reloaded
    os.makedirs(models_dir, exist_ok=True)
    for name, model in sk_models.items():
        file_name = name.lower().replace(" ", "_") + ".pkl"
        with open(os.path.join(models_dir, file_name), "wb") as f:
            pickle.dump(model, f)
    with open(os.path.join(models_dir, "feature_columns.json"), "w", encoding="utf-8") as f:
        json.dump(FEATURE_COLS, f, indent=2)

    best_sk = results[results["Framework"] == "scikit-learn"].iloc[0]["Algorithm"]
    with open(os.path.join(models_dir, best_sk.lower().replace(" ", "_") + ".pkl"), "rb") as f:
        reloaded = pickle.load(f)
    reload_ok = bool(np.array_equal(reloaded.predict(x_test), sk_models[best_sk].predict(x_test)))

    ranges = {}
    for column in FEATURE_COLS:
        values = x_test[column].astype(float)
        ranges[column] = {"min": float(values.min()), "median": float(values.median()),
                          "p95": float(values.quantile(0.95)), "max": float(values.max())}

    summary = {
        "feature_ranges": ranges,
        "best_sklearn": best_sk,
        "cart_sessions": n_rows,
        "purchased_share": float(ml_df.agg(F.avg("label")).first()[0]),
        "results": results,
        "importance": importance,
        "best_model": results.iloc[0]["Algorithm"],
        "best_framework": results.iloc[0]["Framework"],
        "best_auc": float(results.iloc[0]["AUC"]),
        "reload_ok": reload_ok,
    }
    ml_df.unpersist()
    train.unpersist()
    test.unpersist()
    return summary

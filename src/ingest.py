"""Step 1 and 2 of the pipeline: read ANY clickstream CSV, translate it to standard columns, clean it, add features."""
import os

from pyspark.sql import functions as F

from src.mapping import FIELDS

STANDARD_COLUMNS = list(FIELDS)          # the names every later step relies on


def spark_path(path):
    """Absolute path with forward slashes (Spark accepts this form on Windows, macOS and Linux)."""
    return os.path.abspath(path).replace("\\", "/")


def load_raw(spark, path, delimiter=","):
    """Read the CSV with its header. Every column is text for now (we cast it later, safely)."""
    reader = spark.read.option("header", True).option("sep", delimiter).option("mode", "PERMISSIVE")
    return reader.csv(spark_path(path))


def _column(name):
    """Column reference that also works for names with spaces or dots."""
    return F.col("`" + name.replace("`", "``") + "`")


def standardize(raw, column_map, event_map):
    """Rename the user's columns to the standard names and fix their types.

    * missing optional columns become empty (NULL) columns
    * price becomes a number, ids become text (so any id format works)
    * event values (for example 'click', 'order') are translated to view / cart / purchase
    """
    expressions = []
    for field in STANDARD_COLUMNS:
        source = column_map.get(field)
        if source and source in raw.columns:
            value = F.trim(_column(source))
        else:
            value = F.lit(None).cast("string")
        if field == "price":
            value = value.cast("double")
        elif field == "event_type":
            pairs = [F.lit(x) for kv in event_map.items() for x in kv]
            lookup = F.create_map(*pairs) if pairs else F.create_map(F.lit(""), F.lit(""))
            value = lookup[F.lower(value)]                     # NULL when the value is not mapped
        expressions.append(value.alias(field))
    return raw.select(expressions)


def convert_timestamp(df):
    """Turn the time text into a real timestamp `event_ts`.

    Understands '2020-09-24 11:57:06 UTC', ISO times like '2020-09-24T11:57:06', and unix seconds / milliseconds.
    """
    text = F.regexp_replace(F.col("event_time"), r"\s*UTC$", "")
    epoch = (F.when(F.length(text) == 13, text.cast("double") / 1000)
              .when(F.length(text) == 10, text.cast("double")))
    event_ts = F.coalesce(F.to_timestamp(text, "yyyy-MM-dd HH:mm:ss"), F.to_timestamp(text),
                          F.timestamp_seconds(epoch))
    return df.withColumn("event_ts", event_ts).drop("event_time")


def missing_value_report(df):
    """Return {column: number of missing values} using one pass over the data."""
    expressions = []
    for column_name in df.columns:
        missing_only = F.when(F.col(column_name).isNull(), column_name)
        expressions.append(F.count(missing_only).alias(column_name))
    return df.select(expressions).first().asDict()


def data_issues(df):
    """Count rows that cannot be used, and say why (shown to the user)."""
    row = df.agg(
        F.count("*").alias("rows"),
        F.sum(F.col("event_ts").isNull().cast("int")).alias("unreadable_time"),
        F.sum(F.col("event_type").isNull().cast("int")).alias("unmapped_event_type"),
        F.sum(F.col("user_session").isNull().cast("int")).alias("missing_session"),
        F.sum((F.col("price").isNull() | (F.col("price") <= 0)).cast("int")).alias("missing_or_invalid_price"),
    ).first().asDict()
    return {k: int(v or 0) for k, v in row.items()}


def clean(df):
    """Keep usable rows: known event type, readable time, session, valid price. Remove duplicates."""
    return (
        df.dropna(subset=["user_session", "event_ts", "event_type"])
        .filter(F.col("price") > 0)
        .dropDuplicates()
        .fillna({"brand": "unknown", "category_code": "unknown", "product_id": "unknown"})
    )


def add_features(df):
    """Add date, category and price features used by the analysis."""
    parts = F.split("category_code", r"\.")
    return (
        df
        .withColumn("event_date", F.to_date("event_ts"))
        .withColumn("year_month", F.date_format("event_ts", "yyyy-MM"))
        .withColumn("hour", F.hour("event_ts"))
        .withColumn("dow", F.dayofweek("event_ts"))                  # 1 = Sunday ... 7 = Saturday
        .withColumn("day_name", F.date_format("event_ts", "E"))
        .withColumn("is_weekend", F.col("dow").isin(1, 7))
        .withColumn("main_category", F.element_at(parts, 1))
        .withColumn("leaf_category", F.element_at(parts, -1))
        .withColumn(
            "price_tier",
            F.when(F.col("price") < 20, "budget")
            .when(F.col("price") < 100, "mid")
            .when(F.col("price") < 500, "high")
            .otherwise("premium"),
        )
        .withColumn("revenue", F.when(F.col("event_type") == "purchase", F.col("price")).otherwise(F.lit(0.0)))
    )


def build_clean_dataset(spark, path, column_map, event_map, delimiter=",", row_limit=None):
    """Run the whole ingestion step.

    Returns (clean_df, quality_info, prepared_df). `prepared_df` is the standardised data BEFORE
    cleaning (used by the RDD cross-check).
    """
    raw = load_raw(spark, path, delimiter)
    if row_limit:
        raw = raw.limit(int(row_limit))
    prepared = convert_timestamp(standardize(raw, column_map, event_map)).cache()

    issues = data_issues(prepared)
    rows_before = issues["rows"]
    if rows_before == 0:
        raise ValueError("The file has no data rows.")
    missing = missing_value_report(prepared)
    cleaned = add_features(clean(prepared)).cache()
    rows_after = cleaned.count()                      # also fills the cache
    if rows_after == 0:
        raise ValueError(
            "No usable rows are left after cleaning. Rows with problems: "
            f"unreadable time = {issues['unreadable_time']}, event type not mapped = {issues['unmapped_event_type']}, "
            f"missing session = {issues['missing_session']}, "
            f"missing or invalid price = {issues['missing_or_invalid_price']}. "
            "Check the column choices and the event-type mapping.")
    quality = {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_removed": rows_before - rows_after,
        "issues": issues,
        "missing_values": missing,
    }
    return cleaned, quality, prepared

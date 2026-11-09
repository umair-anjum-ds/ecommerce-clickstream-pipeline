"""Predict: model leaderboard, what drives a purchase, and a what-if simulator."""
import os
import pickle

import pandas as pd
import streamlit as st

from src import demo, ml
from ui import charts, state, theme

PRESETS = ["Typical session", "Casual browser", "Serious shopper"]


@st.cache_resource(show_spinner=False)
def demo_model():
    """Train a small model from the bundled demo sessions (fast, and works with any scikit-learn version)."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    sessions = demo.demo_sessions()
    model = HistGradientBoostingClassifier(max_iter=150, random_state=0)
    return model.fit(sessions[ml.FEATURE_COLS], sessions["label"].astype(int))


@st.cache_resource(show_spinner=False)
def saved_model(path):
    with open(path, "rb") as f:                       # a file this app created itself during the analysis
        return pickle.load(f)


def load_model(info):
    if info.get("demo"):
        return demo_model()
    name = info["ml"]["best_sklearn"].lower().replace(" ", "_") + ".pkl"
    path = os.path.join(info["output_dir"], "models", name)
    return saved_model(path) if os.path.exists(path) else None


def slider_for(name, label, ranges, preset, as_int=False, scale=1.0, unit=""):
    """A slider whose range and default come from the real data. `scale` converts seconds to minutes."""
    r = ranges[name]
    low, high = r["min"] / scale, max(r["p95"], r["median"]) / scale
    default = {"Typical session": r["median"], "Casual browser": r["min"] + (r["median"] - r["min"]) * 0.3,
               "Serious shopper": r["p95"]}[preset] / scale
    if as_int:
        low, high, default = int(round(low)), max(int(round(high)), int(round(low)) + 1), int(round(default))
        return st.slider(label, low, high, min(max(default, low), high), key=f"sim_{preset}_{name}")
    high = max(high, low + 1e-6)
    step = max((high - low) / 100, 0.01)
    return st.slider(label + unit, float(low), float(high), float(min(max(default, low), high)), step=float(step),
                     key=f"sim_{preset}_{name}")


def render():
    info = state.require_results("Predict")
    ml_info = info.get("ml")
    theme.page_title("Predict", "Will a cart session end in a purchase? Models trained on your data.",
                     [("Demo data", "amber")] if info.get("demo") else [(state.source_label(info), "violet")])
    if not ml_info:
        theme.empty_state("Model training was switched off", "Run the analysis again with 'Train prediction models' ticked.")
        return
    if "skipped" in ml_info:
        theme.empty_state("Not enough data to train models",
                          f"{ml_info['skipped']}. Training needs sessions that ended in a purchase and sessions "
                          "that did not.")
        return

    theme.kpi_grid([
        {"label": "Best model", "value": ml_info["best_model"], "sub": ml_info["best_framework"],
         "tone": "violet", "icon": "★"},
        {"label": "Best AUC", "value": f"{ml_info['best_auc']:.3f}", "sub": "0.5 guessing, 1.0 perfect",
         "tone": "green", "icon": "%"},
        {"label": "Cart sessions", "value": f"{ml_info['cart_sessions']:,}", "sub": "used for training and testing",
         "tone": "cyan", "icon": "◎"},
        {"label": "Purchased share", "value": f"{ml_info['purchased_share']:.1%}", "sub": "of cart sessions",
         "tone": "amber", "icon": "✓"},
    ])

    left, right = st.columns([3, 2])
    with left, st.container(key="card-models"):
        theme.card_title("Model leaderboard", "Spark MLlib and scikit-learn on the same train/test split")
        charts.show(charts.auc_chart(ml_info["results"]), 260)
    with right, st.container(key="card-importance"):
        theme.card_title("What drives a purchase?", "Feature importance (Random Forest)")
        charts.show(charts.importance_bars(ml_info["importance"]), 260)

    st.dataframe(ml_info["results"].round(3), hide_index=True, width="stretch", column_config={
        "AUC": st.column_config.ProgressColumn("AUC", min_value=0.5, max_value=1.0, format="%.3f"),
        "Accuracy": st.column_config.ProgressColumn("Accuracy", min_value=0.0, max_value=1.0, format="%.3f"),
        "Train time (s)": st.column_config.NumberColumn("Train time (s)", format="%.2f"),
    })

    # ---------------------------------------------------------- what-if simulator
    theme.section("What-if simulator", "Describe a cart session and see how likely it is to end in a purchase.")
    model = load_model(info)
    if model is None:
        st.info("The saved model file was not found, so the simulator is not available for this run.")
        return
    ranges = ml_info["feature_ranges"]
    with st.container(key="card-sim"):
        preset = st.radio("Start from", PRESETS, horizontal=True)
        a, b, c = st.columns(3)
        with a:
            n_views = slider_for("n_views", "Product views", ranges, preset, as_int=True)
            n_carts = slider_for("n_carts", "Cart events", ranges, preset, as_int=True)
            n_products = slider_for("n_products", "Different products", ranges, preset, as_int=True)
        with b:
            avg_price = slider_for("avg_price", "Average price", ranges, preset)
            max_price = slider_for("max_price", "Highest price", ranges, preset)
            n_brands = slider_for("n_brands", "Different brands", ranges, preset, as_int=True)
        with c:
            minutes = slider_for("duration_secs", "Session length", ranges, preset, scale=60.0, unit=" (minutes)")
            weekend = st.toggle("Weekend", value=False)
        row = pd.DataFrame([{"n_views": n_views, "n_carts": n_carts, "avg_price": avg_price, "max_price": max_price,
                             "n_products": n_products, "n_brands": n_brands, "duration_secs": minutes * 60,
                             "is_weekend": int(weekend)}])[ml.FEATURE_COLS]
        probability = float(model.predict_proba(row)[0, 1])
        ring, text = st.columns([1, 2], vertical_alignment="center")
        with ring:
            theme.probability_ring(probability)
        with text:
            base = ml_info["purchased_share"]
            st.markdown(f"This session has a **{probability:.0%}** chance of ending in a purchase. "
                        f"Across all cart sessions, **{base:.0%}** end in a purchase.")
            st.caption("Use it to rank carts: send reminders to carts with a medium chance, protect those that are "
                       "already likely to buy.")

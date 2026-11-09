"""Ready-made demo results, so the app can show a full dashboard instantly (no upload, no waiting).

The files in the `demo` folder come from running the real pipeline on generated data
(`python scripts/build_demo.py`). They are plain JSON and CSV, so they load on any pandas version.
"""
import json
import os

import pandas as pd

from src.spark_session import PROJECT_ROOT

DEMO_DIR = os.path.join(PROJECT_ROOT, "demo")
TABLE_NAMES = ["revenue_by_category", "top_brands", "monthly_trend", "daily_revenue", "hourly_activity",
               "weekday_revenue", "price_tier_purchases", "segment_summary"]


def demo_available():
    return os.path.exists(os.path.join(DEMO_DIR, "info.json"))


def load_demo():
    """Return an `info` dictionary shaped exactly like the one run_pipeline.run() returns."""
    with open(os.path.join(DEMO_DIR, "info.json"), encoding="utf-8") as f:
        info = json.load(f)
    info["tables"] = {name: pd.read_csv(os.path.join(DEMO_DIR, "tables", f"{name}.csv")) for name in TABLE_NAMES}
    info["tables"]["daily_revenue"]["event_date"] = pd.to_datetime(info["tables"]["daily_revenue"]["event_date"])
    ml = info.get("ml")
    if ml and "skipped" not in ml:
        ml["results"] = pd.read_csv(os.path.join(DEMO_DIR, "ml_results.csv"))
        ml["importance"] = pd.read_csv(os.path.join(DEMO_DIR, "ml_importance.csv"))
    info["demo"] = True
    info["source"] = "Demo data (synthetic)"
    info["output_dir"] = None
    info["reports_dir"] = None
    info["chart_files"] = []
    return info


def demo_sessions():
    """Cart sessions (features + label) used to train the what-if simulator in demo mode."""
    return pd.read_csv(os.path.join(DEMO_DIR, "ml_sessions.csv"))

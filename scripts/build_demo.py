"""Rebuild the demo folder from a real pipeline run on generated data.

Usage:  python scripts/build_demo.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generate_sample_data import generate  # noqa: E402
from src import demo, ingest, mapping, ml, run_pipeline  # noqa: E402
from src.spark_session import get_spark  # noqa: E402


def main():
    work = tempfile.mkdtemp(prefix="demo_build_")
    csv_path = os.path.join(work, "events.csv")
    generate(csv_path, sessions=8000, seed=11)

    info = run_pipeline.run(csv_path, os.path.join(work, "out"), os.path.join(work, "reports"), stop_spark=False)

    os.makedirs(os.path.join(demo.DEMO_DIR, "tables"), exist_ok=True)
    for name, table in info["tables"].items():
        table.to_csv(os.path.join(demo.DEMO_DIR, "tables", f"{name}.csv"), index=False)

    ml_info = dict(info["ml"])
    ml_info.pop("results").to_csv(os.path.join(demo.DEMO_DIR, "ml_results.csv"), index=False)
    ml_info.pop("importance").to_csv(os.path.join(demo.DEMO_DIR, "ml_importance.csv"), index=False)

    # sessions for the what-if simulator (the model is trained from these when the demo is opened)
    spark = get_spark()
    column_map, event_map, delimiter = mapping.resolve(csv_path)
    clean, _, _ = ingest.build_clean_dataset(spark, csv_path, column_map, event_map, delimiter)
    sessions = ml.build_session_dataset(clean).drop("user_session").toPandas()
    sessions.to_csv(os.path.join(demo.DEMO_DIR, "ml_sessions.csv"), index=False)

    wanted = ["kpis", "funnel", "quality", "rdd", "column_map", "event_map", "seconds", "warnings"]
    keep = {key: info[key] for key in wanted}
    keep["ml"] = ml_info
    keep["input"] = "demo (synthetic data)"
    with open(os.path.join(demo.DEMO_DIR, "info.json"), "w", encoding="utf-8") as f:
        json.dump(keep, f, indent=2, default=str)
    spark.stop()
    print("Demo files written to", demo.DEMO_DIR)


if __name__ == "__main__":
    main()

"""Run the whole clickstream pipeline on ANY user file.

    python -m src.run_pipeline --input my_events.csv
    python -m src.run_pipeline --input my_events.csv --mapping my_mapping.json

Steps: map columns -> ingest and clean -> analysis -> RDD cross-check -> Parquet -> machine learning
-> charts -> report.
"""
import argparse
import json
import os
import shutil
import sys
import time

from src import analysis, charts, ingest, mapping, ml, rdd_crosscheck, report
from src.spark_session import get_spark


def _print_progress(fraction, message):
    print(f"[pipeline] {fraction:>4.0%}  {message}", flush=True)


def save_parquet(clean, path):
    """Write the cleaned data as Parquet, one folder per month."""
    clean.write.mode("overwrite").partitionBy("year_month").parquet(ingest.spark_path(path))


def run(input_path, output_dir, reports_dir, skip_ml=False, skip_rdd=False, stop_spark=True,
        column_map=None, event_map=None, delimiter=None, row_limit=None, progress=None):
    """Run every step and return the dictionary of results.

    column_map : {standard field: column name in the user's file}. Detected automatically when None.
    event_map  : {value in the file: 'view' | 'cart' | 'purchase'}. Detected automatically when None.
    row_limit  : analyse only the first N rows (quick preview of a huge file).
    progress   : function(fraction, message), for example to drive a progress bar.
    """
    progress = progress or _print_progress
    started = time.time()
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    progress(0.02, "Checking the columns of your file")
    column_map, event_map, delimiter = mapping.resolve(input_path, column_map, event_map, delimiter)

    tables_dir = os.path.join(output_dir, "tables")
    charts_dir = os.path.join(output_dir, "charts")
    models_dir = os.path.join(output_dir, "models")
    for folder in (tables_dir, charts_dir, reports_dir):
        os.makedirs(folder, exist_ok=True)

    progress(0.05, "Starting the Spark engine")
    spark = get_spark()
    prepared = None
    info = {"input": input_path, "column_map": column_map, "event_map": event_map, "delimiter": delimiter,
            "warnings": []}
    try:
        progress(0.08, "1/6 Reading and cleaning the data")
        clean, info["quality"], prepared = ingest.build_clean_dataset(
            spark, input_path, column_map, event_map, delimiter, row_limit)

        progress(0.25, "2/6 Business analysis")
        info["kpis"] = analysis.kpis(clean)
        info["funnel"] = analysis.funnel(clean)
        rfm = analysis.rfm_segments(clean)
        tables = {
            "revenue_by_category": analysis.revenue_by_category(clean).toPandas(),
            "top_brands": analysis.top_brands(clean).toPandas(),
            "monthly_trend": analysis.monthly_trend(clean).toPandas(),
            "daily_revenue": analysis.daily_revenue(clean).toPandas(),
            "hourly_activity": analysis.hourly_activity(clean).toPandas(),
            "weekday_revenue": analysis.weekday_revenue(clean).toPandas(),
            "price_tier_purchases": analysis.price_tier_purchases(clean).toPandas(),
            "segment_summary": analysis.segment_summary(rfm).toPandas(),
        }
        info["tables"] = tables
        for name, pdf in tables.items():
            pdf.to_csv(os.path.join(tables_dir, f"{name}.csv"), index=False)

        if skip_rdd:
            progress(0.50, "3/6 RDD cross-check skipped")
        else:
            progress(0.50, "3/6 RDD cross-check")
            info["rdd"] = rdd_crosscheck.run_rdd_crosscheck(spark, prepared)

        progress(0.62, "4/6 Saving the cleaned data as Parquet")
        try:
            save_parquet(clean, os.path.join(output_dir, "events_parquet"))
        except Exception as error:                       # the analysis itself does not depend on this file
            reason = (str(error).strip().splitlines() or ["unknown reason"])[0][:200]
            info["warnings"].append(
                "The cleaned data could not be saved as Parquet, so that file is missing. Everything else is "
                "unaffected. On Windows this usually means winutils / HADOOP_HOME is not set up (see the README). "
                f"Reason: {reason}")

        if skip_ml:
            progress(0.70, "5/6 Machine learning skipped")
        else:
            progress(0.70, "5/6 Training the purchase-prediction models")
            info["ml"] = ml.run_ml(clean, models_dir)

        progress(0.92, "6/6 Drawing charts and writing the report")
        chart_files = charts.save_business_dashboard(tables, info["funnel"], charts_dir)
        if info.get("ml") and "skipped" not in info["ml"]:
            chart_files += charts.save_model_chart(info["ml"]["results"], charts_dir)
            info["ml"]["results"].to_csv(os.path.join(tables_dir, "model_results.csv"), index=False)
        info["chart_files"] = chart_files
        for chart in chart_files:                                   # PNGs are copied next to the report
            shutil.copy(chart, reports_dir)
        with open(os.path.join(reports_dir, "summary.md"), "w", encoding="utf-8") as f:
            f.write(report.build_summary(info))
        with open(os.path.join(output_dir, "metrics.json"), "w", encoding="utf-8") as f:
            json.dump({"kpis": info["kpis"], "funnel": info["funnel"], "quality": info["quality"],
                       "column_map": column_map, "event_map": event_map,
                       "best_auc": info.get("ml", {}).get("best_auc")}, f, indent=2, default=str)
        info["seconds"] = round(time.time() - started, 1)
        info["output_dir"], info["reports_dir"] = output_dir, reports_dir
        progress(1.0, f"Done in {info['seconds']} s")
        return info
    finally:
        if prepared is not None:
            prepared.unpersist()
        if stop_spark:
            spark.stop()


def main(argv=None):
    parser = argparse.ArgumentParser(description="E-commerce clickstream pipeline (works on your own CSV)")
    parser.add_argument("--input", default=os.environ.get("EVENTS_CSV", "data/events.csv"))
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--reports", default="reports")
    parser.add_argument("--mapping", help='JSON file: {"columns": {"event_time": "my_time_col", ...}, '
                                          '"events": {"click": "view", "order": "purchase"}}')
    parser.add_argument("--delimiter", help="Column separator (detected automatically when omitted)")
    parser.add_argument("--row-limit", type=int, help="Analyse only the first N rows")
    parser.add_argument("--skip-ml", action="store_true")
    parser.add_argument("--skip-rdd", action="store_true")
    args = parser.parse_args(argv)

    column_map = event_map = None
    if args.mapping:
        with open(args.mapping, encoding="utf-8") as f:
            user_mapping = json.load(f)
        column_map, event_map = user_mapping.get("columns"), user_mapping.get("events")
    try:
        run(args.input, args.output, args.reports, args.skip_ml, args.skip_rdd,
            column_map=column_map, event_map=event_map, delimiter=args.delimiter, row_limit=args.row_limit)
    except (ValueError, FileNotFoundError) as error:
        print(f"[pipeline] ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

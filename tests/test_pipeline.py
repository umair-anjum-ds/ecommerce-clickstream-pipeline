"""Automated tests on the standard sample file. They run on every push through GitHub Actions."""
import os

import pytest

from src import analysis, ingest, mapping, ml, rdd_crosscheck, run_pipeline


@pytest.fixture(scope="module")
def prepared(spark, sample_csv):
    column_map, event_map, delimiter = mapping.resolve(sample_csv)
    clean, quality, prep = ingest.build_clean_dataset(spark, sample_csv, column_map, event_map, delimiter)
    return clean, quality, prep


def test_standard_columns_are_created(spark, sample_csv):
    column_map, event_map, delimiter = mapping.resolve(sample_csv)
    raw = ingest.load_raw(spark, sample_csv, delimiter)
    standard = ingest.standardize(raw, column_map, event_map)
    assert standard.columns == ingest.STANDARD_COLUMNS
    assert raw.count() > 1000


def test_timestamp_is_real_timestamp(prepared):
    clean, _, _ = prepared
    assert dict(clean.dtypes)["event_ts"] == "timestamp"
    assert clean.filter("event_ts IS NULL").count() == 0


def test_cleaning_rules(prepared):
    clean, quality, _ = prepared
    assert clean.filter("price <= 0").count() == 0
    assert clean.filter("user_session IS NULL").count() == 0
    assert clean.filter("brand IS NULL OR category_code IS NULL").count() == 0
    assert quality["rows_after"] <= quality["rows_before"]


def test_revenue_comes_only_from_purchases(prepared):
    clean, _, _ = prepared
    assert clean.filter("event_type != 'purchase' AND revenue != 0").count() == 0


def test_kpis_are_consistent(prepared):
    clean, quality, _ = prepared
    k = analysis.kpis(clean)
    assert k["total_events"] == quality["rows_after"]
    assert k["unique_sessions"] <= k["total_events"]
    assert k["total_revenue"] > 0


def test_funnel_rates_are_between_0_and_1(prepared):
    clean, _, _ = prepared
    f = analysis.funnel(clean)
    for key in ("view_to_cart_rate", "cart_to_purchase_rate", "cart_abandonment_rate"):
        assert 0.0 <= f[key] <= 1.0
    assert abs(f["cart_to_purchase_rate"] + f["cart_abandonment_rate"] - 1.0) < 1e-9


def test_rfm_segments_are_valid(prepared):
    clean, _, _ = prepared
    segments = {r["segment"] for r in analysis.rfm_segments(clean).select("segment").distinct().collect()}
    assert segments <= {"Champions", "Big new spenders", "At risk / lapsed", "Regular"}


def test_rdd_matches_dataframe(spark, prepared):
    clean, _, prep = prepared
    k = analysis.kpis(clean)
    rdd = rdd_crosscheck.run_rdd_crosscheck(spark, prep)
    assert rdd["bad_rows"] == 0
    assert abs(rdd["revenue"] - k["total_revenue"]) / k["total_revenue"] < 0.01     # within 1%
    assert rdd["scored_users"] > 0


def test_session_dataset_has_no_leakage(prepared):
    clean, _, _ = prepared
    ml_df = ml.build_session_dataset(clean)
    assert set(ml.FEATURE_COLS) <= set(ml_df.columns)
    assert {r["label"] for r in ml_df.select("label").distinct().collect()} <= {0.0, 1.0}
    assert ml_df.filter("n_carts < 1").count() == 0


def test_full_pipeline_end_to_end(sample_csv, tmp_path):
    out, reports = str(tmp_path / "out"), str(tmp_path / "reports")
    info = run_pipeline.run(sample_csv, out, reports, stop_spark=False, progress=lambda f, m: None)
    assert os.path.exists(os.path.join(reports, "summary.md"))
    assert os.path.exists(os.path.join(reports, "business_dashboard.png"))
    assert os.path.exists(os.path.join(out, "metrics.json"))
    assert os.path.isdir(os.path.join(out, "events_parquet"))
    assert "ml" in info
    if "skipped" not in info["ml"]:
        assert info["ml"]["reload_ok"] is True
        assert os.path.exists(os.path.join(out, "models", "feature_columns.json"))

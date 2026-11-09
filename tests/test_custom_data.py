"""Tests that the pipeline works on a USER's own file: other column names, order, delimiter, time format, labels."""
import csv
import os
import random

import pytest

from src import export, mapping, run_pipeline


def write_user_file(path, sessions=500, purchases=True, delimiter=";"):
    """A file that looks nothing like the original: other names, other order, ISO times, text ids."""
    random.seed(3)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(["Amount", "Customer", "Visit", "Action", "When", "SKU", "Product Category"])
        for s in range(sessions):
            for step in range(random.randint(1, 8)):
                r = random.random()
                action = "click" if r < 0.8 else ("add_to_basket" if r < 0.93 else ("order" if purchases else "click"))
                when = f"2021-01-{1 + s % 28:02d}T{(step * 3) % 24:02d}:15:00"
                writer.writerow([round(random.uniform(5, 900), 2), f"cust-{s % 200}", f"visit-{s}", action, when,
                                 f"sku-{random.randint(1, 80)}",
                                 random.choice(["computers.notebook", "electronics.tablet", ""])])


def test_mapping_detects_other_names(tmp_path):
    path = str(tmp_path / "user.csv")
    write_user_file(path)
    column_map, event_map, delimiter = mapping.resolve(path)
    assert delimiter == ";"
    assert column_map["price"] == "Amount"
    assert column_map["user_id"] == "Customer"
    assert column_map["user_session"] == "Visit"
    assert column_map["event_time"] == "When"
    assert event_map == {"click": "view", "add_to_basket": "cart", "order": "purchase"}


def test_missing_required_column_gives_clear_error(tmp_path):
    path = str(tmp_path / "bad.csv")
    with open(path, "w") as f:
        f.write("foo,bar\n1,2\n")
    with pytest.raises(ValueError, match="No column chosen"):
        mapping.resolve(path)


def test_pipeline_runs_on_user_file(tmp_path):
    path = str(tmp_path / "user.csv")
    write_user_file(path)
    out, reports = str(tmp_path / "out"), str(tmp_path / "reports")
    info = run_pipeline.run(path, out, reports, stop_spark=False, progress=lambda f, m: None)
    assert info["kpis"]["purchases"] > 0
    assert info["kpis"]["total_revenue"] > 0
    assert info["quality"]["issues"]["unreadable_time"] == 0
    assert os.path.exists(os.path.join(reports, "summary.md"))
    zip_bytes = export.results_zip(out, reports)
    assert len(zip_bytes) > 1000


def test_file_without_purchases_still_runs(tmp_path):
    path = str(tmp_path / "nopurchase.csv")
    write_user_file(path, purchases=False)
    # the app/CLI refuses this by default because no value means 'purchase'; allow it explicitly here
    column_map = mapping.suggest_mapping(list(mapping.read_preview(path).columns))
    event_map = {"click": "view", "add_to_basket": "cart"}
    out, reports = str(tmp_path / "out"), str(tmp_path / "reports")
    with pytest.raises(ValueError, match="purchase"):
        run_pipeline.run(path, out, reports, stop_spark=False, column_map=column_map, event_map=event_map,
                         progress=lambda f, m: None)


def test_unreadable_times_give_clear_error(tmp_path):
    path = str(tmp_path / "badtime.csv")
    with open(path, "w") as f:
        f.write("event_time,event_type,user_session,user_id,price\n")
        for i in range(20):
            f.write(f"not-a-date,view,s{i},u{i},10\n")
        f.write("not-a-date,purchase,s1,u1,10\n")
    out, reports = str(tmp_path / "out"), str(tmp_path / "reports")
    with pytest.raises(ValueError, match="No usable rows"):
        run_pipeline.run(path, out, reports, stop_spark=False, progress=lambda f, m: None)


def test_parquet_failure_does_not_stop_the_analysis(tmp_path, monkeypatch):
    """On Windows without winutils the Parquet export can fail. The rest of the results must still be produced."""
    path = str(tmp_path / "user.csv")
    write_user_file(path)

    def broken_save(clean, target):
        raise RuntimeError("simulated: winutils.exe not found\nsecond line")

    monkeypatch.setattr(run_pipeline, "save_parquet", broken_save)
    out, reports = str(tmp_path / "out"), str(tmp_path / "reports")
    info = run_pipeline.run(path, out, reports, skip_ml=True, stop_spark=False, progress=lambda f, m: None)
    assert info["warnings"] and "winutils" in info["warnings"][0]
    with open(os.path.join(reports, "summary.md"), encoding="utf-8") as f:
        assert "## Warnings" in f.read()
    assert info["kpis"]["purchases"] > 0


def test_non_ascii_text_in_data(tmp_path):
    """Brand and category names in other alphabets must not crash the report (a Windows code-page problem)."""
    path = str(tmp_path / "unicode.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["event_time", "event_type", "user_session", "user_id", "price", "brand", "category_code"])
        for i in range(60):
            kind = "purchase" if i % 3 == 0 else "view"
            brand = "\u0160koda" if i % 2 else "\u83ef\u70ba"
            writer.writerow([f"2021-02-0{1 + i % 8} 10:{i % 60:02d}:00", kind, f"s{i % 20}", f"u{i % 15}",
                             10 + i, brand, "\u00e9lectronique.t\u00e9l\u00e9phone"])
    out, reports = str(tmp_path / "out"), str(tmp_path / "reports")
    run_pipeline.run(path, out, reports, skip_ml=True, stop_spark=False, progress=lambda f, m: None)
    with open(os.path.join(reports, "summary.md"), encoding="utf-8") as f:
        text = f.read()
    assert "\u0160koda" in text and "\u83ef\u70ba" in text

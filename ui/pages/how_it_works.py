"""How it works: pipeline overview and the technical details of the current run."""
import pandas as pd
import streamlit as st

from ui import state, theme

DOT = """
digraph G {
  rankdir=LR; bgcolor="transparent"; pad=0.2; nodesep=0.35; ranksep=0.5;
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=12, fontcolor="white", color="#2B3566", fillcolor="#161E42", penwidth=1.4, margin="0.22,0.14"];
  edge [color="#5B6AA8", arrowsize=0.8, penwidth=1.4];
  csv [label="Your CSV", fillcolor="#7C5CFF", color="#7C5CFF"];
  map [label="Column mapping"];
  clean [label="Clean + features\\n(Spark DataFrame)"];
  analyse [label="Analysis\\n(groupBy, pivot, windows)"];
  rdd [label="RDD cross-check\\n(accumulator, broadcast)"];
  store [label="Parquet"];
  model [label="Models\\n(Spark MLlib + scikit-learn)"];
  out [label="Dashboard, report, ZIP", fillcolor="#00B7E6", color="#00B7E6"];
  csv -> map -> clean -> analyse -> out;
  clean -> rdd -> out;
  clean -> store;
  clean -> model -> out;
}
"""

STEPS = [
    ("1", "Map and clean", "Columns are detected and translated. Times are parsed, duplicates and unusable rows removed, "
                           "date and price features added."),
    ("2", "Analyse", "KPIs, revenue by category and brand, monthly trend with pivot, daily revenue with window "
                     "functions, funnel, shopping hours, RFM segments."),
    ("3", "Cross-check with RDDs", "Key numbers are recomputed with the low-level RDD API (mapPartitions, "
                                   "accumulator, reduceByKey, groupByKey, broadcast variable)."),
    ("4", "Store", "The cleaned data is saved as Parquet, partitioned by month."),
    ("5", "Predict", "Six models (Spark MLlib and scikit-learn) learn which cart sessions end in a purchase."),
    ("6", "Report", "Charts, tables, trained models and a written summary are packed into a ZIP."),
]


def render():
    theme.page_title("How it works", "The pipeline behind the dashboard, and the facts of this run.")
    with st.container(key="card-flow"):
        theme.card_title("Pipeline", "From raw file to decisions")
        st.graphviz_chart(DOT, width="stretch")

    cards = "".join(f'<div class="feature"><div class="big">{n}</div><div class="t">{t}</div><div class="d">{d}</div></div>'
                    for n, t, d in STEPS)
    theme.html(f'<div class="features">{cards}</div>')

    info = state.results()
    if info is None:
        st.info("Run an analysis or open the demo to see the details of a run here.")
        return

    theme.section("This run", "Data quality, column mapping and the RDD check for the current data.")
    q, issues = info["quality"], info["quality"]["issues"]
    theme.kpi_grid([
        {"label": "Rows read", "value": f"{q['rows_before']:,}", "tone": "violet", "icon": "≡"},
        {"label": "Rows used", "value": f"{q['rows_after']:,}", "tone": "green", "icon": "✓"},
        {"label": "Rows removed", "value": f"{q['rows_removed']:,}",
         "sub": f"{q['rows_removed'] / max(q['rows_before'], 1):.1%} of the file", "tone": "amber", "icon": "−"},
        {"label": "Run time", "value": f"{info.get('seconds', 0):,.0f} s", "tone": "cyan", "icon": "⏱"},
    ])
    left, right = st.columns(2)
    with left, st.container(key="card-issues"):
        theme.card_title("Rows that could not be used", "Counts can overlap")
        st.dataframe(pd.DataFrame({"Problem": ["Unreadable time", "Event type not mapped", "Missing session id",
                                               "Missing or invalid price"],
                                   "Rows": [issues["unreadable_time"], issues["unmapped_event_type"],
                                            issues["missing_session"], issues["missing_or_invalid_price"]]}),
                     hide_index=True, width="stretch")
    with right, st.container(key="card-columns"):
        theme.card_title("How your columns were used", "Standard field and the column in your file")
        st.dataframe(pd.DataFrame([{"Field": f, "Your column": c or "(not provided)"}
                                   for f, c in info["column_map"].items()]), hide_index=True, width="stretch")

    rdd = info.get("rdd")
    if rdd:
        k = info["kpis"]
        diff = rdd["revenue"] - k["total_revenue"]
        theme.section("RDD cross-check", "The same numbers computed a second way. They should agree.")
        with st.container(key="card-rdd"):
            st.dataframe(pd.DataFrame({"Metric": ["Purchases", "Revenue"],
                                       "DataFrame": [f"{k['purchases']:,}", f"{k['total_revenue']:,.2f}"],
                                       "RDD": [f"{rdd['purchases']:,}", f"{rdd['revenue']:,.2f}"],
                                       "Difference": [f"{rdd['purchases'] - k['purchases']:,}", f"{diff:,.2f}"]}),
                         hide_index=True, width="stretch")
            st.caption("A small difference is expected: the RDD parser keeps duplicate rows that the DataFrame cleaning "
                       f"removes. Rows the accumulator could not use: {rdd['bad_rows']:,}.")
            if rdd.get("common_paths"):
                st.markdown("**Most common short customer journeys (RDD):** " +
                            ", ".join(f"`{p}` ({c:,})" for p, c in rdd["common_paths"]))

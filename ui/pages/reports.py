"""Reports: download everything."""
import os

import streamlit as st

from src import export
from ui import state, theme


def render():
    info = state.require_results("Reports")
    theme.page_title("Reports", "Download the results and read the written summary.",
                     [("Demo data", "amber")] if info.get("demo") else [(state.source_label(info), "violet")])

    if info.get("demo"):
        st.info("This is the demo, so there is no ZIP with models. Run an analysis on your own data to download everything.")
    else:
        summary_path = os.path.join(info["reports_dir"], "summary.md")
        with st.container(key="card-downloads"):
            theme.card_title("Download", "Tables, charts, trained models, the report and metrics")
            left, right = st.columns(2)
            left.download_button("Download everything (ZIP)", type="primary", width="stretch",
                                 data=export.results_zip(info["output_dir"], info["reports_dir"]),
                                 file_name="clickpulse_results.zip", mime="application/zip")
            with open(summary_path, encoding="utf-8") as f:
                report_text = f.read()
            right.download_button("Download the report (Markdown)", data=report_text, file_name="summary.md",
                                  width="stretch")

    theme.section("Tables", "Each table as a CSV file.")
    names = list(info["tables"])
    columns = st.columns(4)
    for i, name in enumerate(names):
        columns[i % 4].download_button(name.replace("_", " ").capitalize(), data=info["tables"][name].to_csv(index=False),
                                       file_name=f"{name}.csv", mime="text/csv", width="stretch", key=f"dl_{name}")

    if not info.get("demo"):
        theme.section("Written report")
        with st.container(key="card-report"):
            st.markdown(report_text)

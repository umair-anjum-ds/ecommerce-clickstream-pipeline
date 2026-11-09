"""Shared state between pages (the results of the last analysis live in st.session_state)."""
import os
import shutil
import tempfile

import streamlit as st

from src import demo
from ui import nav


def results():
    return st.session_state.get("results")


def set_results(info):
    st.session_state["results"] = info


def source_label(info):
    return info.get("source") or os.path.basename(str(info.get("input", "your data")))


def new_workdir():
    """Each upload gets its own temporary folder, so runs never mix. The old one is deleted."""
    old = st.session_state.get("workdir")
    if old and os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)
    st.session_state["workdir"] = tempfile.mkdtemp(prefix="clickpulse_")
    return st.session_state["workdir"]


def open_demo():
    set_results(demo.load_demo())
    st.switch_page(nav.PAGES["dashboard"])


def require_results(page_name):
    """Return the results, or show a friendly empty state (and stop the page) when there are none."""
    from ui import theme
    info = results()
    if info is not None:
        return info
    theme.page_title(page_name, "Run an analysis first, or open the demo to explore.")
    theme.empty_state("Nothing to show yet",
                      "Upload your clickstream CSV on the Start page, or open the demo to see a complete example.")
    left, right, _ = st.columns([1, 1, 3])
    left.page_link(nav.PAGES["start"], label="Go to Start", icon=":material/rocket_launch:")
    if demo.demo_available() and right.button("Open the demo", type="primary"):
        open_demo()
    st.stop()


def compact(value):
    """12345 -> 12.3K, 2400000 -> 2.40M"""
    value = float(value)
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e4, "K")):
        if abs(value) >= limit:
            return f"{value / limit:,.2f}{suffix}" if suffix != "K" else f"{value / limit:,.1f}K"
    return f"{value:,.0f}" if abs(value) >= 100 else f"{value:,.2f}"

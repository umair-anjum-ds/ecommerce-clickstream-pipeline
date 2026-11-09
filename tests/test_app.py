"""The web app: every page renders without errors, the insights make sense, the demo loads."""
import os

import pytest
from streamlit.testing.v1 import AppTest

from src import demo, insights

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PATH = os.path.join(ROOT, "app.py")


def test_landing_page_starts():
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    assert not app.exception
    assert any("Explore the demo" in b.label for b in app.button)


@pytest.mark.parametrize("page", ["dashboard", "customers", "predict", "how_it_works", "reports"])
def test_every_page_renders_with_the_demo(page):
    code = f"""
import streamlit as st
from src import demo
from ui import theme
theme.inject_css()
st.session_state['results'] = demo.load_demo()
from ui.pages import {page}
{page}.render()
"""
    app = AppTest.from_string(code, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]


def test_pages_show_a_friendly_message_without_results():
    code = """
import streamlit as st
from ui import nav, state
nav.PAGES.update({"start": st.Page(lambda: None, title="Start"), "dashboard": st.Page(lambda: None, title="Dash")})
state.require_results("Dashboard")
"""
    app = AppTest.from_string(code, default_timeout=60).run()
    assert not app.exception


def test_demo_files_load():
    assert demo.demo_available()
    info = demo.load_demo()
    assert info["kpis"]["purchases"] > 0 and info["demo"] is True
    assert len(info["tables"]["revenue_by_category"]) > 0
    assert len(demo.demo_sessions()) > 100


def test_insights_are_written_from_the_numbers():
    found = insights.build_insights(demo.load_demo())
    assert 3 <= len(found) <= 12
    for item in found:
        assert item["tone"] in {"good", "warn", "info"} and item["title"] and item["text"]
    assert any("abandoned" in item["title"] for item in found)


def test_insights_survive_a_dataset_without_purchases():
    info = demo.load_demo()
    info["kpis"]["total_revenue"] = 0
    info["kpis"]["purchases"] = 0
    info["funnel"].update(sessions_with_cart=0, sessions_with_purchase=0, cart_abandonment_rate=0.0,
                          cart_to_purchase_rate=0.0)
    for name in ["revenue_by_category", "top_brands", "daily_revenue", "segment_summary", "weekday_revenue"]:
        info["tables"][name] = info["tables"][name].iloc[0:0]
    info["tables"]["hourly_activity"] = info["tables"]["hourly_activity"].assign(purchase=0)
    info["ml"] = {"skipped": "no purchases"}
    assert isinstance(insights.build_insights(info), list)         # must not raise


# ---------------------------------------------------------------- light and dark theme
def test_both_themes_define_the_same_colours():
    from ui import theme
    assert set(theme.PALETTES["light"]) == set(theme.PALETTES["dark"])


def test_css_flips_instantly_with_light_dark_colours():
    from ui import theme
    captured = {}
    import streamlit as st
    original = st.markdown
    st.markdown = lambda body, **kwargs: captured.setdefault("css", body)
    try:
        theme.inject_css("light")
    finally:
        st.markdown = original
    css = captured["css"]
    assert "light-dark(#F3F5FB, #0A0F1F)" in css          # adaptive background
    assert "--bg: #F3F5FB" in css                          # static fallback for the detected mode
    assert "__VARS__" not in css and "__ADAPTIVE__" not in css


def test_chart_colours_follow_the_theme():
    from ui import charts
    try:
        charts.set_mode("light")
        light = charts.pal()["ink"]
        charts.set_mode("dark")
        dark = charts.pal()["ink"]
        assert light != dark
        charts.set_mode("nonsense")                        # unknown values fall back to dark
        assert charts.pal()["ink"] == dark
    finally:
        charts.set_mode("dark")


@pytest.mark.parametrize("page", ["dashboard", "customers", "predict"])
def test_pages_render_in_light_mode(page):
    code = f"""
import streamlit as st
from src import demo
from ui import charts, theme
theme.inject_css("light")
charts.set_mode("light")
st.session_state['results'] = demo.load_demo()
from ui.pages import {page}
{page}.render()
"""
    app = AppTest.from_string(code, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]


# ---------------------------------------------------------------- mixed old/new files are explained, not a crash
def test_all_required_parts_exist():
    from ui import health
    assert health.missing_parts() == []


def test_app_explains_mixed_versions_instead_of_crashing(monkeypatch):
    from ui import health, theme
    monkeypatch.delattr(theme, "current_mode")            # simulate an old theme.py next to a new app.py
    assert health.missing_parts() == ["ui.theme.current_mode"]
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    assert not app.exception
    assert any("different versions" in e.value for e in app.error)

"""ClickPulse: web app for e-commerce clickstream analytics.

Run it with:   python run.py        (or: streamlit run app.py)
"""
import os

import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="ClickPulse", page_icon=":material/bolt:", layout="wide",
                   initial_sidebar_state="collapsed")

from ui import health  # noqa: E402

problems = health.missing_parts()
if problems:                                      # old and new files mixed: explain instead of crashing
    st.error(health.FIX)
    st.code("\n".join(problems))
    st.stop()

from ui import charts, nav, theme  # noqa: E402
from ui.pages import customers, dashboard, how_it_works, predict, reports, start  # noqa: E402

mode = theme.current_mode()                     # "light" or "dark", from the visitor's theme
theme.inject_css(mode)
theme.inject_theme_watcher()
charts.set_mode(mode)
logo = "logo_light.svg" if mode == "light" else "logo.svg"
st.logo(os.path.join(HERE, "ui", "assets", logo), size="large")

nav.PAGES.update({
    "start": st.Page(start.render, title="Start", icon=":material/rocket_launch:", url_path="start", default=True),
    "dashboard": st.Page(dashboard.render, title="Dashboard", icon=":material/dashboard:", url_path="dashboard"),
    "customers": st.Page(customers.render, title="Customers", icon=":material/groups:", url_path="customers"),
    "predict": st.Page(predict.render, title="Predict", icon=":material/psychology:", url_path="predict"),
    "how": st.Page(how_it_works.render, title="How it works", icon=":material/account_tree:", url_path="how-it-works"),
    "reports": st.Page(reports.render, title="Reports", icon=":material/download:", url_path="reports"),
})
st.navigation(list(nav.PAGES.values()), position="top").run()

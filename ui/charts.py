"""Interactive charts (Altair) in one consistent style that follows the light or dark theme."""
import altair as alt
import pandas as pd
import streamlit as st

TIER_ORDER = ["budget", "mid", "high", "premium"]
DAY_ORDER = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

_MODE = {"value": "dark"}

PALETTES = {
    "dark": {"accent": "#7C5CFF", "cyan": "#00D4FF", "green": "#2EE6A6", "amber": "#FFB020", "red": "#FF5C7C",
             "muted": "#9AA4C7", "grid": "#232C52", "ink": "#FFFFFF",
             "area_top": "rgba(0,212,255,0.0)", "area_bottom": "rgba(0,212,255,0.55)"},
    "light": {"accent": "#6D4AFF", "cyan": "#0891B2", "green": "#10B981", "amber": "#F59F00", "red": "#E8446D",
              "muted": "#5E678C", "grid": "#DDE2F0", "ink": "#151A33",
              "area_top": "rgba(8,145,178,0.0)", "area_bottom": "rgba(8,145,178,0.40)"},
}


def set_mode(mode):
    """Called once per run by app.py with 'light' or 'dark'."""
    _MODE["value"] = mode if mode in PALETTES else "dark"


def pal():
    return PALETTES[_MODE["value"]]


def palette_list():
    p = pal()
    return [p["accent"], p["cyan"], p["green"], p["amber"], p["red"], "#C084FC", "#38BDF8", "#F472B6"]


def segment_colors():
    p = pal()
    return {"Champions": p["green"], "Big new spenders": p["cyan"], "Regular": p["accent"], "At risk / lapsed": p["amber"]}


def _finish(chart, height=300):
    """Apply the shared look (transparent background, soft grid, readable text)."""
    p = pal()
    return (chart.properties(height=height, width="container")
            .configure(background="transparent")
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor=p["muted"], titleColor=p["muted"], gridColor=p["grid"], domainColor=p["grid"],
                            tickColor=p["grid"], labelFontSize=11, titleFontSize=12, titleFontWeight=600)
            .configure_legend(labelColor=p["muted"], titleColor=p["muted"], orient="bottom", symbolType="circle")
            .configure_title(color=p["ink"]))


def show(chart, height=300):
    st.altair_chart(_finish(chart, height), theme=None, width="stretch")


def _gradient(color_top, color_bottom):
    return alt.Gradient(gradient="linear", stops=[alt.GradientStop(color=color_top, offset=0),
                                                  alt.GradientStop(color=color_bottom, offset=1)],
                        x1=1, x2=1, y1=1, y2=0)


def category_bar(df, top=8):
    p = pal()
    data = df.head(top)
    return (alt.Chart(data).mark_bar(cornerRadiusEnd=6, height=22, color=p["accent"])
            .encode(y=alt.Y("main_category:N", sort="-x", title=None),
                    x=alt.X("revenue:Q", title="Revenue"),
                    tooltip=[alt.Tooltip("main_category:N", title="Category"), alt.Tooltip("revenue:Q", format=",.2f"),
                             alt.Tooltip("items_sold:Q", format=","), alt.Tooltip("buyers:Q", format=",")]))


def daily_line(df):
    p = pal()
    data = df.copy()
    data["event_date"] = pd.to_datetime(data["event_date"])
    base = alt.Chart(data).encode(x=alt.X("event_date:T", title=None))
    area = base.mark_area(opacity=0.35, line={"color": p["cyan"], "strokeWidth": 1.5},
                          color=_gradient(p["area_top"], p["area_bottom"])).encode(
        y=alt.Y("revenue:Q", title="Revenue"),
        tooltip=[alt.Tooltip("event_date:T", title="Day"), alt.Tooltip("revenue:Q", format=",.2f"),
                 alt.Tooltip("orders:Q", format=",")])
    average = base.mark_line(color=p["amber"], strokeWidth=2.5).encode(y="moving_avg_7d:Q")
    return area + average


def monthly_combo(df):
    p = pal()
    data = df.fillna(0)
    base = alt.Chart(data).encode(x=alt.X("year_month:N", title=None, axis=alt.Axis(labelAngle=0)))
    bars = base.mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color=p["accent"], size=34).encode(
        y=alt.Y("purchase:Q", title="Purchases"),
        tooltip=[alt.Tooltip("year_month:N", title="Month"), alt.Tooltip("purchase:Q", format=","),
                 alt.Tooltip("purchase_rate_pct:Q", title="Purchase rate %")])
    line = base.mark_line(color=p["green"], strokeWidth=3, point=alt.OverlayMarkDef(color=p["green"], size=70)).encode(
        y=alt.Y("purchase_rate_pct:Q", title="Purchase rate (% of views)"))
    return alt.layer(bars, line).resolve_scale(y="independent")


def funnel(f):
    p = pal()
    stages = [("Sessions with a view", f["sessions_with_view"]), ("Sessions with a cart", f["sessions_with_cart"]),
              ("Sessions with a purchase", f["sessions_with_purchase"])]
    rows, previous = [], None
    for label, value in stages:
        share = "" if previous in (None, 0) else f"{value / previous:.1%} of previous"
        rows.append({"stage": label, "sessions": value, "note": share})
        previous = value
    data = pd.DataFrame(rows)
    base = alt.Chart(data).encode(y=alt.Y("stage:N", sort=None, title=None))
    bars = base.mark_bar(cornerRadiusEnd=8, height=38).encode(
        x=alt.X("sessions:Q", title="Sessions"),
        color=alt.Color("stage:N", legend=None, scale=alt.Scale(domain=[r["stage"] for r in rows],
                                                                range=[p["cyan"], p["amber"], p["green"]])),
        tooltip=["stage:N", alt.Tooltip("sessions:Q", format=","), "note:N"])
    labels = base.mark_text(align="left", dx=8, color=p["ink"], fontWeight="bold").encode(
        x="sessions:Q", text=alt.Text("sessions:Q", format=","))
    return bars + labels


def hourly_bars(df):
    p = pal()
    data = df.fillna(0).copy()
    data["is_peak"] = data["purchase"] == data["purchase"].max()
    return (alt.Chart(data).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
            .encode(x=alt.X("hour:O", title="Hour of day (UTC)", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("purchase:Q", title="Purchases"),
                    color=alt.condition("datum.is_peak", alt.value(p["amber"]), alt.value(p["accent"])),
                    tooltip=[alt.Tooltip("hour:O", title="Hour"), alt.Tooltip("purchase:Q", format=","),
                             alt.Tooltip("view:Q", format=","),
                             alt.Tooltip("purchase_per_1000_views:Q", title="Purchases per 1,000 views")]))


def weekday_bars(df):
    p = pal()
    data = df.fillna(0).copy()
    data["is_peak"] = data["revenue"] == data["revenue"].max()
    return (alt.Chart(data).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(x=alt.X("day_name:N", sort=DAY_ORDER, title=None, axis=alt.Axis(labelAngle=0),
                            scale=alt.Scale(paddingInner=0.4, paddingOuter=0.2)),
                    y=alt.Y("revenue:Q", title="Revenue"),
                    color=alt.condition("datum.is_peak", alt.value(p["green"]), alt.value(p["cyan"])),
                    tooltip=[alt.Tooltip("day_name:N", title="Day"), alt.Tooltip("revenue:Q", format=",.2f"),
                             alt.Tooltip("events:Q", format=",")]))


def donut(df, category, value, order=None, colors=None):
    p = pal()
    data = df.copy()
    total = data[value].sum()
    data["share"] = data[value] / total if total else 0
    domain = order or list(data[category])
    colours = [colors.get(name, p["muted"]) for name in domain] if colors else palette_list()[:len(domain)]
    scale = alt.Scale(domain=domain, range=colours)
    arcs = (alt.Chart(data).mark_arc(innerRadius=62, outerRadius=105, cornerRadius=5, padAngle=0.02)
            .encode(theta=alt.Theta(f"{value}:Q"),
                    color=alt.Color(f"{category}:N", scale=scale, legend=alt.Legend(title=None)),
                    tooltip=[alt.Tooltip(f"{category}:N"), alt.Tooltip(f"{value}:Q", format=",.0f"),
                             alt.Tooltip("share:Q", format=".1%")]))
    centre = (alt.Chart(pd.DataFrame({"t": [f"{total:,.0f}"]}))
              .mark_text(color=p["ink"], fontSize=24, fontWeight="bold").encode(text="t:N"))
    return arcs + centre


def segment_bars(df, value, title):
    colors = segment_colors()
    data = df.sort_values(value, ascending=False)
    scale = alt.Scale(domain=list(colors), range=list(colors.values()))
    return (alt.Chart(data).mark_bar(cornerRadiusEnd=6, height=24)
            .encode(y=alt.Y("segment:N", sort="-x", title=None), x=alt.X(f"{value}:Q", title=title),
                    color=alt.Color("segment:N", scale=scale, legend=None),
                    tooltip=["segment:N", alt.Tooltip(f"{value}:Q", format=",.2f")]))


def importance_bars(df):
    p = pal()
    return (alt.Chart(df).mark_bar(cornerRadiusEnd=6, height=22, color=p["accent"])
            .encode(y=alt.Y("Feature:N", sort="-x", title=None), x=alt.X("Importance:Q", title="Importance"),
                    tooltip=["Feature:N", alt.Tooltip("Importance:Q", format=".3f")]))


def auc_chart(df):
    """Leaderboard: each bar runs from 0.5 (random guessing) to the model's AUC. The name is written inside the bar."""
    p = pal()
    data = df.copy()
    short = data["Framework"].map({"Spark MLlib": "Spark", "scikit-learn": "sklearn"}).fillna(data["Framework"])
    data["label"] = data["Algorithm"] + "  [" + short + "]"
    data["start"] = 0.5
    data["end"] = data["AUC"].clip(lower=0.5)
    order = data.sort_values("AUC", ascending=False)["label"].tolist()
    x_scale = alt.Scale(domain=[0.5, max(0.8, float(data["AUC"].max()) + 0.08)], nice=False)

    base = alt.Chart(data).encode(y=alt.Y("label:N", sort=order, axis=None))
    bars = base.mark_bar(cornerRadiusEnd=8, height=22).encode(
        x=alt.X("start:Q", scale=x_scale, title="Test AUC (0.5 = random guessing, 1.0 = perfect)"), x2="end:Q",
        color=alt.Color("Framework:N", scale=alt.Scale(domain=["Spark MLlib", "scikit-learn"],
                                                       range=[p["amber"], p["accent"]])),
        tooltip=["Algorithm:N", "Framework:N", alt.Tooltip("AUC:Q", format=".3f"), alt.Tooltip("Accuracy:Q", format=".3f")])
    names = base.mark_text(align="left", dx=10, fontSize=12, fontWeight="bold").encode(
        x=alt.X("start:Q", scale=x_scale), text="label:N",
        color=alt.condition(alt.datum.Framework == "Spark MLlib", alt.value("#1A1200"), alt.value("#FFFFFF")))
    scores = base.mark_text(align="left", dx=8, color=p["ink"], fontSize=12, fontWeight="bold").encode(
        x=alt.X("end:Q", scale=x_scale), text=alt.Text("AUC:Q", format=".3f"))
    return bars + names + scores

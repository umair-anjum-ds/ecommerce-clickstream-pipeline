"""Dashboard: headline numbers, automatic insights and interactive charts."""
import streamlit as st

from src import insights
from ui import charts, state, theme


def render():
    info = state.require_results("Dashboard")
    k, f, tables = info["kpis"], info["funnel"], info["tables"]

    pills = [("Demo data", "amber") if info.get("demo") else (state.source_label(info), "violet"),
             (f"{k['total_events']:,} events", "cyan")]
    theme.page_title("Dashboard", "Everything your clickstream says, at a glance.", pills)

    purchases = k["purchases"] or 0
    aov = k["total_revenue"] / purchases if purchases else 0
    conversion = f["sessions_with_purchase"] / f["sessions"] if f["sessions"] else 0
    theme.kpi_grid([
        {"label": "Revenue", "value": state.compact(k["total_revenue"]), "sub": f"median price {k['median_price']:,.2f}",
         "tone": "violet", "icon": "$"},
        {"label": "Purchases", "value": f"{purchases:,}", "sub": f"avg order {aov:,.2f}", "tone": "green", "icon": "✓"},
        {"label": "Customers", "value": f"{k['unique_users']:,}", "sub": f"{k['unique_sessions']:,} sessions",
         "tone": "cyan", "icon": "◎"},
        {"label": "Conversion", "value": f"{conversion:.1%}", "sub": "sessions that buy", "tone": "amber", "icon": "%"},
        {"label": "Cart abandonment", "value": f"{f['cart_abandonment_rate']:.1%}",
         "sub": f"{f['sessions_with_cart']:,} cart sessions", "tone": "red", "icon": "↯"},
    ])

    found = insights.build_insights(info)
    if found:
        theme.section("What stands out", "Findings written automatically from your numbers.")
        theme.insight_grid(found[:6])

    theme.section("Revenue", "Where the money comes from and how it moves over time.")
    left, right = st.columns([2, 3])
    with left, st.container(key="card-category"):
        theme.card_title("Revenue by category", "Top categories by purchase revenue")
        if len(tables["revenue_by_category"]):
            charts.show(charts.category_bar(tables["revenue_by_category"]), 330)
        else:
            st.caption("No purchases found.")
    with right, st.container(key="card-daily"):
        theme.card_title("Daily revenue", "Cyan: each day. Amber: 7-day moving average")
        if len(tables["daily_revenue"]):
            charts.show(charts.daily_line(tables["daily_revenue"]), 330)
        else:
            st.caption("No purchases found.")

    theme.section("Customer journey", "How visitors move from browsing to buying, and how that changes by month.")
    left, right = st.columns(2)
    with left, st.container(key="card-funnel"):
        theme.card_title("Session funnel", "Share of sessions that reach each stage")
        charts.show(charts.funnel(f), 300)
    with right, st.container(key="card-monthly"):
        theme.card_title("Monthly purchases and purchase rate", "Bars: purchases. Line: purchases per 100 views")
        charts.show(charts.monthly_combo(tables["monthly_trend"]), 300)

    theme.section("Timing", "When customers shop. Hours are in UTC.")
    left, mid, right = st.columns([3, 2, 2])
    with left, st.container(key="card-hours"):
        theme.card_title("Purchases by hour", "Highlighted bar is the peak hour")
        charts.show(charts.hourly_bars(tables["hourly_activity"]), 280)
    with mid, st.container(key="card-weekday"):
        theme.card_title("Revenue by weekday", "Highlighted bar is the best day")
        charts.show(charts.weekday_bars(tables["weekday_revenue"]), 280)
    with right, st.container(key="card-tier"):
        theme.card_title("Purchases by price tier", "budget < 20, mid < 100, high < 500")
        if len(tables["price_tier_purchases"]):
            charts.show(charts.donut(tables["price_tier_purchases"], "price_tier", "count", charts.TIER_ORDER), 280)

    theme.section("Brands", "Top brands by revenue.")
    brands = tables["top_brands"].head(10)
    if len(brands):
        top_value = float(brands["revenue"].max())
        st.dataframe(brands, hide_index=True, width="stretch", column_config={
            "brand": "Brand",
            "purchases": st.column_config.NumberColumn("Purchases", format="%d"),
            "revenue": st.column_config.ProgressColumn("Revenue", format="%.0f", min_value=0, max_value=top_value),
        })

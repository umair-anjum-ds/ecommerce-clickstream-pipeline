"""Customers: RFM segments."""
import streamlit as st

from ui import charts, state, theme

DESCRIPTIONS = {
    "Champions": "Bought recently, spend a lot and buy again. Reward and protect them.",
    "Big new spenders": "Recent and high spending, but not repeat buyers yet. Turn them into regulars.",
    "Regular": "Steady, lower-spending customers. Good targets for cross-selling.",
    "At risk / lapsed": "Have not bought for a while. A win-back offer can bring them back.",
}


def render():
    info = state.require_results("Customers")
    seg = info["tables"]["segment_summary"].copy()
    theme.page_title("Customers", "Who your buyers are, grouped by Recency, Frequency and Monetary value (RFM).",
                     [("Demo data", "amber")] if info.get("demo") else [(state.source_label(info), "violet")])
    if not len(seg):
        theme.empty_state("No buyers found", "RFM needs at least one purchase event. Check the event-type mapping.")
        return

    seg["value"] = seg["customers"] * seg["avg_spend"]
    seg["revenue_share"] = seg["value"] / seg["value"].sum()
    theme.kpi_grid([
        {"label": "Buyers", "value": f"{int(seg['customers'].sum()):,}", "sub": "customers with a purchase",
         "tone": "violet", "icon": "◎"},
        {"label": "Segments", "value": f"{len(seg)}", "sub": "RFM groups", "tone": "cyan", "icon": "#"},
        {"label": "Largest group", "value": seg.sort_values("customers").iloc[-1]["segment"],
         "sub": f"{int(seg['customers'].max()):,} customers", "tone": "amber", "icon": "▲"},
        {"label": "Most valuable", "value": seg.sort_values("value").iloc[-1]["segment"],
         "sub": f"{seg['revenue_share'].max():.0%} of buyer value", "tone": "green", "icon": "★"},
    ])

    left, right = st.columns(2)
    with left, st.container(key="card-seg-count"):
        theme.card_title("Customers per segment", "How many buyers fall into each group")
        charts.show(charts.donut(seg, "segment", "customers", colors=charts.segment_colors()), 300)
    with right, st.container(key="card-seg-value"):
        theme.card_title("Customer value per segment", "Share of total spend")
        value_table = seg.assign(value=seg["value"].round(0))
        charts.show(charts.donut(value_table, "segment", "value", colors=charts.segment_colors()), 300)

    left, right = st.columns(2)
    with left, st.container(key="card-seg-spend"):
        theme.card_title("Average spend", "Money per customer")
        charts.show(charts.segment_bars(seg, "avg_spend", "Average spend"), 240)
    with right, st.container(key="card-seg-recency"):
        theme.card_title("Days since last purchase", "Lower is better")
        charts.show(charts.segment_bars(seg, "avg_recency", "Average days"), 240)

    theme.section("What to do with each segment")
    for name in seg.sort_values("value", ascending=False)["segment"]:
        row = seg[seg["segment"] == name].iloc[0]
        st.markdown(f"**{name}** &nbsp; {int(row['customers']):,} customers, average spend {row['avg_spend']:,.2f}, "
                    f"{row['revenue_share']:.0%} of buyer value  \n"
                    f"<span style='color:#9AA4C7'>{DESCRIPTIONS.get(name, '')}</span>", unsafe_allow_html=True)

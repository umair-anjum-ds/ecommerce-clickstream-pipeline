"""Write a short Markdown report (reports/summary.md) that is committed to git by the automation."""
import datetime


def md_table(headers, rows):
    """Build a Markdown table from a list of header names and a list of row lists."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def build_summary(info):
    """`info` is the dictionary collected by run_pipeline.py. Returns the report text."""
    k, f, q = info["kpis"], info["funnel"], info["quality"]
    lines = [
        "# Pipeline summary",
        "",
        f"Generated: {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC  |  input: `{info['input']}`",
        "",
        "## Data quality",
        md_table(["Metric", "Value"], [
            ["Rows read", f"{q['rows_before']:,}"],
            ["Rows after cleaning", f"{q['rows_after']:,}"],
            ["Rows removed", f"{q['rows_removed']:,}"],
            ["Rows with unreadable time", f"{q['issues']['unreadable_time']:,}"],
            ["Rows with an unmapped event type", f"{q['issues']['unmapped_event_type']:,}"],
            ["Rows with missing session id", f"{q['issues']['missing_session']:,}"],
            ["Rows with missing or invalid price", f"{q['issues']['missing_or_invalid_price']:,}"],
        ]),
        "",
        "## How your columns were used",
        md_table(["Standard field", "Column in your file"],
                 [[field, column or "(not provided)"] for field, column in info["column_map"].items()]),
        "",
        md_table(["Event value in your file", "Treated as"], [[k, v] for k, v in info["event_map"].items()]),
        "",
        "## Key numbers",
        md_table(["Metric", "Value"], [
            ["Total events", f"{k['total_events']:,}"],
            ["Unique users", f"{k['unique_users']:,}"],
            ["Unique sessions", f"{k['unique_sessions']:,}"],
            ["Unique products", f"{k['unique_products']:,}"],
            ["Purchases", f"{k['purchases']:,}"],
            ["Total revenue", f"{k['total_revenue']:,.2f}"],
            ["Median price", f"{k['median_price']:,.2f}"],
        ]),
        "",
        "## Funnel",
        md_table(["Metric", "Value"], [
            ["Sessions", f"{f['sessions']:,}"],
            ["Sessions with a cart", f"{f['sessions_with_cart']:,}"],
            ["Sessions with a purchase", f"{f['sessions_with_purchase']:,}"],
            ["View to cart rate", f"{f['view_to_cart_rate']:.2%}"],
            ["Cart to purchase rate", f"{f['cart_to_purchase_rate']:.2%}"],
            ["Cart abandonment rate", f"{f['cart_abandonment_rate']:.2%}"],
        ]),
        "",
        "## Top categories by revenue",
        md_table(["Category", "Items sold", "Revenue"],
                 [[r.main_category, f"{r.items_sold:,}", f"{r.revenue:,.2f}"]
                  for r in info["tables"]["revenue_by_category"].head(5).itertuples()]),
        "",
        "## Top brands by revenue",
        md_table(["Brand", "Purchases", "Revenue"],
                 [[r.brand, f"{r.purchases:,}", f"{r.revenue:,.2f}"]
                  for r in info["tables"]["top_brands"].head(5).itertuples()]),
        "",
        "## Customer segments (RFM)",
        md_table(["Segment", "Customers", "Average spend"],
                 [[r.segment, f"{r.customers:,}", f"{r.avg_spend:,.2f}"]
                  for r in info["tables"]["segment_summary"].itertuples()]),
    ]

    rdd = info.get("rdd")
    if rdd:
        diff = abs(rdd["revenue"] - k["total_revenue"])
        lines += ["", "## RDD cross-check",
                  md_table(["Metric", "DataFrame", "RDD"], [
                      ["Purchases", f"{k['purchases']:,}", f"{rdd['purchases']:,}"],
                      ["Revenue", f"{k['total_revenue']:,.2f}", f"{rdd['revenue']:,.2f}"],
                  ]),
                  "", f"Revenue difference: {diff:,.2f} (the RDD parser does not remove duplicate rows). "
                      f"Malformed lines counted by the accumulator: {rdd['bad_rows']}."]

    ml = info.get("ml")
    if ml and "skipped" in ml:
        lines += ["", "## Machine learning", f"Skipped: {ml['skipped']}."]
    elif ml:
        lines += ["", "## Machine learning (will a cart session end in a purchase?)",
                  f"Cart sessions: {ml['cart_sessions']:,} | purchased share: {ml['purchased_share']:.1%} | "
                  f"best model: **{ml['best_model']}** ({ml['best_framework']}), AUC {ml['best_auc']:.3f} | "
                  f"saved model reloads correctly: {ml['reload_ok']}", "",
                  md_table(["Framework", "Algorithm", "AUC", "Accuracy"],
                           [[r.Framework, r.Algorithm, f"{r.AUC:.3f}", f"{r.Accuracy:.3f}"]
                            for r in ml["results"].itertuples()])]
    if info.get("warnings"):
        lines += ["", "## Warnings"] + [f"- {w}" for w in info["warnings"]]
    lines += ["", "## Charts", "![Dashboard](business_dashboard.png)", "![Segments](customer_segments.png)"]
    if ml and "skipped" not in ml:
        lines.append("![Models](model_comparison.png)")
    return "\n".join(lines) + "\n"

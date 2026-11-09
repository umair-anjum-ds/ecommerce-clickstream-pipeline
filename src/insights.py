"""Turn the numbers of a run into plain-English findings. Works for any dataset (nothing is hard-coded).

Each insight is a dict: {"tone": "good" | "warn" | "info", "title": short headline, "text": one or two sentences}.
"""
import pandas as pd


def _money(value):
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:,.2f}"


def _auc_label(auc):
    if auc >= 0.85:
        return "strong"
    if auc >= 0.7:
        return "good"
    if auc >= 0.6:
        return "moderate"
    return "weak"


def build_insights(info):
    """Return a list of insight dicts (at most about 8), most important first."""
    out = []
    k, f, tables = info["kpis"], info["funnel"], info["tables"]
    total_revenue = k.get("total_revenue") or 0

    # 1) revenue concentration
    cat = tables["revenue_by_category"]
    if total_revenue > 0 and len(cat):
        top = cat.iloc[0]
        share = top["revenue"] / total_revenue
        tone = "warn" if share >= 0.6 else "info"
        extra = " Revenue depends heavily on this one category." if share >= 0.6 else ""
        out.append({"tone": tone, "title": f"{top['main_category']} drives {share:.0%} of revenue",
                    "text": f"It earned {_money(top['revenue'])} from {int(top['items_sold']):,} items.{extra}"})

    # 2) the cart is where customers are lost
    if f["sessions_with_cart"] > 0:
        rate = f["cart_abandonment_rate"]
        tone = "warn" if rate >= 0.5 else "good"
        out.append({"tone": tone, "title": f"{rate:.0%} of carts are abandoned",
                    "text": f"Only {f['cart_to_purchase_rate']:.0%} of sessions with a cart end in a purchase. "
                            "Reminders or small incentives are the quickest win."})

    # 3) browsing barely reaches the cart
    if f["sessions_with_view"] > 0 and f["view_to_cart_rate"] < 0.15:
        out.append({"tone": "info",
                    "title": f"Only {f['view_to_cart_rate']:.1%} of browsing sessions reach the cart",
                    "text": "Most visitors look and leave. Better product pages and search can lift this."})

    # 4) growth: last 30 days against the 30 days before
    daily = tables["daily_revenue"]
    if len(daily) >= 60:
        d = daily.copy()
        d["event_date"] = pd.to_datetime(d["event_date"])
        d = d.sort_values("event_date")
        last_day = d["event_date"].max()
        recent = d[d["event_date"] > last_day - pd.Timedelta(days=30)]["revenue"].sum()
        before = d[(d["event_date"] <= last_day - pd.Timedelta(days=30))
                   & (d["event_date"] > last_day - pd.Timedelta(days=60))]["revenue"].sum()
        if before > 0:
            change = recent / before - 1
            tone = "good" if change >= 0 else "warn"
            word = "up" if change >= 0 else "down"
            out.append({"tone": tone, "title": f"Revenue is {word} {abs(change):.0%} in the last 30 days",
                        "text": f"{_money(recent)} against {_money(before)} in the 30 days before."})

    # 5) when customers buy
    hourly = tables["hourly_activity"]
    if len(hourly) and hourly["purchase"].fillna(0).sum() > 0:
        h = hourly.fillna(0)
        peak_hour = int(h.loc[h["purchase"].idxmax(), "hour"])
        text = f"Most purchases happen around {peak_hour:02d}:00 (UTC)."
        busy = h[h["view"] >= max(h["view"].sum() * 0.01, 1)]
        if len(busy):
            best = busy.loc[busy["purchase_per_1000_views"].idxmax()]
            text += (f" Conversion is best at {int(best['hour']):02d}:00 "
                     f"({best['purchase_per_1000_views']:.0f} purchases per 1,000 views).")
        out.append({"tone": "info", "title": f"Peak buying hour: {peak_hour:02d}:00", "text": text})

    # 6) best weekday
    wk = tables["weekday_revenue"]
    if len(wk) and wk["revenue"].fillna(0).sum() > 0:
        best, worst = wk.loc[wk["revenue"].idxmax()], wk.loc[wk["revenue"].idxmin()]
        out.append({"tone": "info", "title": f"{best['day_name']} is the strongest day",
                    "text": f"{_money(best['revenue'])} in revenue, against {_money(worst['revenue'])} "
                            f"on {worst['day_name']}."})

    # 7) customer value concentration
    seg = tables["segment_summary"]
    if len(seg) and total_revenue > 0:
        s = seg.copy()
        s["value"] = s["customers"] * s["avg_spend"]
        s["share"] = s["value"] / s["value"].sum()
        champs = s[s["segment"].isin(["Champions", "Big new spenders"])]
        if len(champs) and s["customers"].sum() > 0:
            cust_share = champs["customers"].sum() / s["customers"].sum()
            rev_share = champs["share"].sum()
            out.append({"tone": "good", "title": f"{cust_share:.0%} of buyers bring {rev_share:.0%} of revenue",
                        "text": "Champions and big new spenders are your most valuable customers. Protect them."})
        lapsed = s[s["segment"] == "At risk / lapsed"]
        if len(lapsed) and lapsed.iloc[0]["share"] >= 0.2:
            out.append({"tone": "warn", "title": f"{int(lapsed.iloc[0]['customers']):,} customers have gone quiet",
                        "text": f"They represent about {lapsed.iloc[0]['share']:.0%} of customer value. A win-back "
                                "campaign could recover part of it."})

    # 8) prediction quality
    ml = info.get("ml")
    if ml and "skipped" not in ml:
        out.append({"tone": "good" if ml["best_auc"] >= 0.7 else "info",
                    "title": f"{ml['best_model']} predicts purchases ({_auc_label(ml['best_auc'])})",
                    "text": f"AUC {ml['best_auc']:.2f} on {ml['cart_sessions']:,} cart sessions (0.5 is guessing, "
                            "1.0 is perfect). Use it to rank carts by purchase chance."})

    # 9) data quality
    q = info["quality"]
    if q["rows_before"] > 0:
        removed = q["rows_removed"] / q["rows_before"]
        if removed >= 0.05:
            out.append({"tone": "warn", "title": f"{removed:.0%} of rows were unusable",
                        "text": "Check the column mapping and the data export. Duplicates, missing prices "
                                "or unreadable times were removed."})
    return out

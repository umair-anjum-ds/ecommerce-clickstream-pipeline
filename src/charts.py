"""Step 6 of the pipeline: save the charts as PNG files."""
import os

import matplotlib

matplotlib.use("Agg")                      # draw to files, no window needed (works in CI)
import matplotlib.pyplot as plt  # noqa: E402


def _style():
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update({"figure.dpi": 110, "axes.titleweight": "bold", "axes.titlesize": 12,
                         "axes.spines.top": False, "axes.spines.right": False})


def save_business_dashboard(tables, funnel, out_dir):
    """2 x 3 grid of business charts. `tables` holds small pandas DataFrames."""
    _style()
    cat = tables["revenue_by_category"].head(8).sort_values("revenue")
    daily = tables["daily_revenue"]
    hourly = tables["hourly_activity"]
    monthly = tables["monthly_trend"]
    weekday = tables["weekday_revenue"]
    segments = tables["segment_summary"].sort_values("customers")

    fig, ax = plt.subplots(2, 3, figsize=(18, 10))

    ax[0, 0].barh(cat["main_category"], cat["revenue"], color="#1f4e79")
    ax[0, 0].set_title("Revenue by main category (top 8)")

    ax[0, 1].plot(daily["event_date"], daily["revenue"], color="#85c1e9", label="Daily revenue")
    ax[0, 1].plot(daily["event_date"], daily["moving_avg_7d"], color="#1f4e79", linewidth=2, label="7-day average")
    ax[0, 1].set_title("Daily purchase revenue")
    ax[0, 1].legend(frameon=False)
    ax[0, 1].tick_params(axis="x", rotation=30)

    ax[0, 2].bar(hourly["hour"], hourly["purchase"], color="#e67e22")
    ax[0, 2].set_title("Purchases by hour of day (UTC)")

    ax[1, 0].bar(monthly["year_month"], monthly["purchase"], color="#2e86c1")
    ax[1, 0].set_title("Purchases per month")
    ax[1, 0].tick_params(axis="x", rotation=45)

    ax[1, 1].bar(weekday["day_name"], weekday["revenue"], color="#27ae60")
    ax[1, 1].set_title("Revenue by weekday")

    ax[1, 2].bar(["View", "Cart", "Purchase"],
                 [funnel["sessions_with_view"], funnel["sessions_with_cart"], funnel["sessions_with_purchase"]],
                 color=["#2e86c1", "#f39c12", "#27ae60"])
    ax[1, 2].set_title("Session funnel")

    fig.suptitle("E-commerce Clickstream: Key Results", fontsize=15, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(out_dir, "business_dashboard.png")
    fig.savefig(path)
    plt.close(fig)

    # second small figure: customer segments
    fig, ax2 = plt.subplots(1, 2, figsize=(12, 4))
    ax2[0].barh(segments["segment"], segments["customers"], color="#27ae60")
    ax2[0].set_title("Customers per RFM segment")
    ax2[1].barh(segments["segment"], segments["avg_spend"], color="#f39c12")
    ax2[1].set_title("Average spend per RFM segment")
    plt.tight_layout()
    seg_path = os.path.join(out_dir, "customer_segments.png")
    fig.savefig(seg_path)
    plt.close(fig)
    return [path, seg_path]


def save_model_chart(results, out_dir):
    """Horizontal bar chart of test AUC for every model."""
    _style()
    data = results.sort_values("AUC")
    colors = data["Framework"].map({"Spark MLlib": "#e67e22", "scikit-learn": "#1f4e79"})
    labels = data["Algorithm"] + "  (" + data["Framework"] + ")"

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(labels, data["AUC"], color=colors)
    ax.axvline(0.5, color="grey", linestyle="--", linewidth=1)           # 0.5 = random guessing
    ax.set_xlim(0.4, max(0.8, data["AUC"].max() + 0.05))
    ax.set_xlabel("Test AUC (0.5 = random guessing)")
    ax.set_title("Model comparison: predicting purchase from a cart session", fontweight="bold")
    for bar, value in zip(bars, data["AUC"]):
        ax.text(value + 0.002, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", va="center", fontsize=9)
    plt.tight_layout()
    path = os.path.join(out_dir, "model_comparison.png")
    fig.savefig(path)
    plt.close(fig)
    return [path]

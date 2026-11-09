"""Step 3 of the pipeline: the business analysis. Every function takes the clean DataFrame."""
from pyspark.sql import Window
from pyspark.sql import functions as F


def kpis(clean):
    """Whole-table key numbers as a dictionary."""
    row = clean.agg(
        F.count("*").alias("total_events"),
        F.countDistinct("user_id").alias("unique_users"),
        F.countDistinct("user_session").alias("unique_sessions"),
        F.countDistinct("product_id").alias("unique_products"),
        F.round(F.sum("revenue"), 2).alias("total_revenue"),
        F.sum((F.col("event_type") == "purchase").cast("int")).alias("purchases"),
        F.round(F.avg("price"), 2).alias("avg_price"),
        F.expr("percentile_approx(price, 0.5)").alias("median_price"),
    ).first()
    return row.asDict()


def revenue_by_category(clean):
    """Purchases, revenue and buyers for every main category (best first)."""
    return (
        clean.filter("event_type = 'purchase'")
        .groupBy("main_category")
        .agg(
            F.count("*").alias("items_sold"),
            F.round(F.sum("price"), 2).alias("revenue"),
            F.round(F.avg("price"), 2).alias("avg_item_price"),
            F.countDistinct("user_id").alias("buyers"),
        )
        .orderBy(F.desc("revenue"))
    )


def top_brands(clean):
    """Revenue per brand (the 'unknown' brand is ignored)."""
    return (
        clean.filter("event_type = 'purchase' AND brand != 'unknown'")
        .groupBy("brand")
        .agg(F.count("*").alias("purchases"), F.round(F.sum("price"), 2).alias("revenue"))
        .orderBy(F.desc("revenue"))
    )


def monthly_trend(clean):
    """Events per month by type, with cart and purchase rates (pivot)."""
    return (
        clean.groupBy("year_month")
        .pivot("event_type", ["view", "cart", "purchase"])
        .count()
        .orderBy("year_month")
        .withColumn("cart_rate_pct", F.round(F.col("cart") / F.col("view") * 100, 2))
        .withColumn("purchase_rate_pct", F.round(F.col("purchase") / F.col("view") * 100, 2))
    )


def daily_revenue(clean):
    """Daily revenue with a running total and a 7-day moving average (window functions)."""
    daily = (
        clean.filter("event_type = 'purchase'")
        .groupBy("event_date")
        .agg(F.round(F.sum("price"), 2).alias("revenue"), F.count("*").alias("orders"))
    )
    all_days = Window.orderBy("event_date")
    running = all_days.rowsBetween(Window.unboundedPreceding, Window.currentRow)
    last_7_days = all_days.rowsBetween(-6, 0)
    return (
        daily
        .withColumn("cumulative_revenue", F.round(F.sum("revenue").over(running), 2))
        .withColumn("moving_avg_7d", F.round(F.avg("revenue").over(last_7_days), 2))
        .orderBy("event_date")
    )


def funnel(clean):
    """Session funnel: view -> cart -> purchase. Returns a dictionary of counts and rates."""
    sessions = clean.groupBy("user_session").agg(
        F.max((F.col("event_type") == "view").cast("int")).alias("viewed"),
        F.max((F.col("event_type") == "cart").cast("int")).alias("carted"),
        F.max((F.col("event_type") == "purchase").cast("int")).alias("purchased"),
    )
    row = sessions.agg(
        F.count("*").alias("sessions"),
        F.sum("viewed").alias("sessions_with_view"),
        F.sum("carted").alias("sessions_with_cart"),
        F.sum("purchased").alias("sessions_with_purchase"),
        F.sum(F.col("viewed") * F.col("carted")).alias("view_and_cart"),
        F.sum(F.col("carted") * F.col("purchased")).alias("cart_and_purchase"),
    ).first().asDict()
    view_to_cart = row["view_and_cart"] / row["sessions_with_view"] if row["sessions_with_view"] else 0.0
    cart_to_purchase = row["cart_and_purchase"] / row["sessions_with_cart"] if row["sessions_with_cart"] else 0.0
    row["view_to_cart_rate"] = view_to_cart
    row["cart_to_purchase_rate"] = cart_to_purchase
    row["cart_abandonment_rate"] = 1 - cart_to_purchase if row["sessions_with_cart"] else 0.0
    return row


def hourly_activity(clean):
    """Events per hour of the day by type (UTC)."""
    return (
        clean.groupBy("hour").pivot("event_type", ["view", "cart", "purchase"]).count()
        .withColumn("purchase_per_1000_views", F.round(F.col("purchase") / F.col("view") * 1000, 1))
        .orderBy("hour")
    )


def weekday_revenue(clean):
    """Events and revenue per weekday."""
    return (
        clean.groupBy("dow", "day_name")
        .agg(F.count("*").alias("events"), F.round(F.sum("revenue"), 2).alias("revenue"))
        .orderBy("dow")
    )


def price_tier_purchases(clean):
    """Number of purchases in each price tier."""
    return clean.filter("event_type = 'purchase'").groupBy("price_tier").count()


def rfm_segments(clean):
    """RFM customer table: Recency, Frequency, Monetary scores and a segment name per buyer."""
    buyers = clean.filter("event_type = 'purchase'")
    snapshot_date = buyers.agg(F.max("event_date")).first()[0]          # latest date acts as 'today'

    rfm = buyers.groupBy("user_id").agg(
        F.datediff(F.lit(snapshot_date), F.max("event_date")).alias("recency_days"),
        F.countDistinct("user_session").alias("frequency"),
        F.round(F.sum("price"), 2).alias("monetary"),
    )
    return (
        rfm
        .withColumn("r_score", F.ntile(4).over(Window.orderBy(F.desc("recency_days"))))
        .withColumn("m_score", F.ntile(4).over(Window.orderBy("monetary")))
        .withColumn("f_score", F.when(F.col("frequency") >= 3, 3).when(F.col("frequency") == 2, 2).otherwise(1))
        .withColumn(
            "segment",
            F.when((F.col("r_score") >= 3) & (F.col("m_score") >= 3) & (F.col("f_score") >= 2), "Champions")
            .when((F.col("r_score") >= 3) & (F.col("m_score") >= 3), "Big new spenders")
            .when(F.col("r_score") <= 2, "At risk / lapsed")
            .otherwise("Regular"),
        )
    )


def segment_summary(rfm):
    """One row per RFM segment: customers, average spend and average recency."""
    return (
        rfm.groupBy("segment")
        .agg(
            F.count("*").alias("customers"),
            F.round(F.avg("monetary"), 2).alias("avg_spend"),
            F.round(F.avg("recency_days"), 1).alias("avg_recency"),
        )
        .orderBy(F.desc("customers"))
    )

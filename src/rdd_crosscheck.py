"""Step 4 of the pipeline: recompute key numbers with the low-level RDD API.

This double-checks the DataFrame results and shows mapPartitions with an accumulator,
a broadcast variable, reduceByKey and groupByKey.
"""
from collections import namedtuple
from operator import add

from pyspark.sql import Row
from pyspark.sql import functions as F

Event = namedtuple("Event", ["event_time", "event_type", "product_id", "category_code",
                             "brand", "price", "user_id", "session"])


# ---- small named functions (easier to read than one-line lambdas) ----
def has_session(e):
    return e.session != ""


def is_purchase(e):
    return e.event_type == "purchase"


def is_known_brand(e):
    return e.brand != "unknown"


def event_type_and_one(e):
    return (e.event_type, 1)


def brand_and_price(e):
    return (e.brand, e.price)


def get_price(e):
    return e.price


def session_and_event(e):
    return (e.session, (e.event_time, e.event_type))


def event_types_in_time_order(items):
    """items = all (time, type) pairs of one session. Sort by time and keep only the types."""
    return [event_type for _, event_type in sorted(items)]


def path_text_and_one(pair):
    return (">".join(pair[1]), 1)


def is_short_path(pair):
    return pair[0].count(">") < 3


def minus_second_item(pair):
    return -pair[1]                                   # sort from largest to smallest


def make_parser(bad_rows):
    """Build the partition parser. `bad_rows` is an accumulator that counts rows that cannot be used."""
    def parse_partition(rows):
        for row in rows:
            try:
                if row.event_time is None or row.event_type is None or row.user_session is None:
                    raise ValueError("missing value")
                price = float(row.price)
                if price <= 0:
                    raise ValueError("invalid price")
                yield Event(row.event_time, row.event_type, row.product_id or "unknown",
                            row.category_code or "unknown", row.brand or "unknown", price,
                            row.user_id, row.user_session)
            except (ValueError, TypeError):
                bad_rows.add(1)
    return parse_partition


def run_rdd_crosscheck(spark, prepared_df):
    """Recompute key numbers with RDDs, starting from the standardised data. Returns a dictionary."""
    sc = spark.sparkContext
    bad_rows = sc.accumulator(0)

    # one text time per row (so journeys can be sorted by time), then drop to the RDD API
    as_text = prepared_df.select(
        F.date_format("event_ts", "yyyy-MM-dd HH:mm:ss").alias("event_time"),
        "event_type", "product_id", "category_code", "brand", "price", "user_id", "user_session")
    events = as_text.rdd.mapPartitions(make_parser(bad_rows)).filter(has_session)
    events.cache()

    events_count = events.count()
    events_per_type = dict(events.map(event_type_and_one).reduceByKey(add).collect())

    purchases = events.filter(is_purchase)
    purchase_count = purchases.count()
    revenue = purchases.map(get_price).sum() if purchase_count else 0.0

    brand_revenue = purchases.filter(is_known_brand).map(brand_and_price).reduceByKey(add)
    top_brands = brand_revenue.takeOrdered(5, key=minus_second_item)

    # customer journeys
    paths = events.map(session_and_event).groupByKey().mapValues(event_types_in_time_order)
    common_paths = (paths.map(path_text_and_one).filter(is_short_path)
                    .reduceByKey(add).takeOrdered(5, key=minus_second_item))

    # engagement score with a broadcast variable
    weights = sc.broadcast({"view": 1, "cart": 3, "purchase": 5})

    def user_and_points(e):
        return (e.user_id, weights.value[e.event_type])

    def pair_to_row(pair):
        return Row(user_id=pair[0], engagement_score=pair[1])

    user_score = events.map(user_and_points).reduceByKey(add)
    top_users = user_score.takeOrdered(5, key=minus_second_item)
    score_df = spark.createDataFrame(user_score.map(pair_to_row))
    scored_users = score_df.count()
    weights.unpersist()

    result = {
        "events": events_count,
        "bad_rows": bad_rows.value,
        "events_per_type": events_per_type,
        "purchases": purchase_count,
        "revenue": round(revenue, 2),
        "top_brands": top_brands,
        "common_paths": common_paths,
        "top_users": top_users,
        "scored_users": scored_users,
    }
    events.unpersist()
    return result

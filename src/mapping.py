"""Let the pipeline work on ANY user file: detect and validate which column means what.

The pipeline needs a few standard fields. A user's file may call them something else
(`timestamp` instead of `event_time`, `click` instead of `view`), so we detect the names,
let the user fix them in the app, and translate everything to the standard names.
"""
import re

import pandas as pd

# field name -> (is it required?, label shown to the user)
FIELDS = {
    "event_time": (True, "Event time (when it happened)"),
    "event_type": (True, "Event type (view / cart / purchase)"),
    "user_session": (True, "Session id"),
    "user_id": (True, "User / customer id"),
    "price": (True, "Price"),
    "product_id": (False, "Product id"),
    "category_code": (False, "Category"),
    "brand": (False, "Brand"),
}
REQUIRED = [name for name, (required, _) in FIELDS.items() if required]
EVENT_ROLES = ["view", "cart", "purchase"]

ALIASES = {
    "event_time": ["event_time", "timestamp", "time", "datetime", "date_time", "event_timestamp", "created_at", "date",
                   "when"],
    "event_type": ["event_type", "event", "action", "type", "event_name", "behavior", "behaviour"],
    "user_session": ["user_session", "session_id", "session", "sessionid", "visit_id", "visitid", "visit"],
    "user_id": ["user_id", "userid", "customer_id", "customerid", "visitor_id", "visitorid", "customer", "user"],
    "price": ["price", "unit_price", "amount", "value", "cost"],
    "product_id": ["product_id", "productid", "item_id", "itemid", "sku", "product"],
    "category_code": ["category_code", "category", "category_name", "product_category"],
    "brand": ["brand", "brand_name", "manufacturer"],
}

EVENT_KEYWORDS = {                       # checked in this order, first match wins
    "purchase": ["purchase", "buy", "bought", "order", "transaction", "sale"],
    "cart": ["cart", "basket"],
    "view": ["view", "click", "detail", "browse", "impression", "visit"],
}


def _normalise(name):
    return re.sub(r"[^a-z0-9_]", "", str(name).strip().lower().replace(" ", "_"))


def suggest_mapping(columns):
    """Guess {field: column name or None} from the file's column names."""
    by_normalised = {}
    for column in columns:
        by_normalised.setdefault(_normalise(column), column)
    used, result = set(), {}
    for field, aliases in ALIASES.items():
        result[field] = None
        for alias in aliases:
            column = by_normalised.get(alias)
            if column is not None and column not in used:
                result[field] = column
                used.add(column)
                break
    return result


def suggest_event_map(values):
    """Guess {value found in the file: 'view' | 'cart' | 'purchase'}. Unknown values are left out."""
    result = {}
    for value in values:
        text = str(value).strip().lower()
        for role, keywords in EVENT_KEYWORDS.items():
            if any(word in text for word in keywords):
                result[text] = role
                break
    return result


def validate_mapping(column_map, columns, event_map=None):
    """Return a list of problems (an empty list means everything is fine)."""
    problems = []
    for field in REQUIRED:
        chosen = column_map.get(field)
        if not chosen:
            problems.append(f"No column chosen for '{field}'.")
        elif chosen not in columns:
            problems.append(f"Column '{chosen}' (for '{field}') is not in the file.")
    chosen_columns = [c for c in column_map.values() if c]
    if len(chosen_columns) != len(set(chosen_columns)):
        problems.append("The same column is used for two different fields.")
    if event_map is not None and not any(role == "purchase" for role in event_map.values()):
        problems.append("No event value is marked as 'purchase', so revenue and the funnel cannot be calculated.")
    return problems


def detect_delimiter(path):
    """Look at the first line and pick the most common separator."""
    if str(path).endswith(".gz"):
        import gzip
        opener = gzip.open
    else:
        opener = open
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:
        first_line = f.readline()
    counts = {sep: first_line.count(sep) for sep in [",", ";", "\t", "|"]}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def read_preview(path, nrows=1000, delimiter=None):
    """Read the first rows as text with pandas (fast, no Spark needed)."""
    delimiter = delimiter or detect_delimiter(path)
    return pd.read_csv(path, nrows=nrows, dtype=str, sep=delimiter, encoding_errors="replace")


def distinct_values(path, column, delimiter=None, max_values=60):
    """Distinct values of one column (reads only that column, in chunks)."""
    delimiter = delimiter or detect_delimiter(path)
    found = set()
    for chunk in pd.read_csv(path, usecols=[column], dtype=str, sep=delimiter, chunksize=500_000,
                             encoding_errors="replace"):
        found.update(chunk[column].dropna().str.strip().str.lower().unique())
        if len(found) > max_values:
            break
    return sorted(found)[:max_values]


def resolve(path, column_map=None, event_map=None, delimiter=None):
    """Fill in anything the user did not give (auto-detect) and validate. Returns (columns, events, delimiter)."""
    delimiter = delimiter or detect_delimiter(path)
    columns = list(read_preview(path, nrows=5, delimiter=delimiter).columns)
    column_map = dict(column_map) if column_map else suggest_mapping(columns)
    if event_map is None:
        event_map = {}
        if column_map.get("event_type") in columns:
            event_map = suggest_event_map(distinct_values(path, column_map["event_type"], delimiter))
    problems = validate_mapping(column_map, columns, event_map)
    if problems:
        raise ValueError("Cannot run on this file:\n- " + "\n- ".join(problems) +
                         f"\nColumns found in the file: {columns}")
    return column_map, event_map, delimiter

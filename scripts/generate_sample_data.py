"""Create a small, fake events.csv with the same columns as the real dataset.

The real file is large and is not stored in git. The automated tests and the
GitHub Actions pipeline use this generator instead.

Usage:  python scripts/generate_sample_data.py --sessions 6000 --out data/events.csv
"""
import argparse
import csv
import datetime
import os
import random

CATEGORIES = [
    "computers.components.videocards", "electronics.smartphone", "appliances.kitchen.washer",
    "computers.notebook", "electronics.tablet", "appliances.environment.vacuum",
    "furniture.living_room.sofa", "apparel.shoes", "",
]
BRANDS = ["msi", "gigabyte", "palit", "samsung", "xiaomi", "lg", "asus", "sony", "", ""]


def generate(out_path, sessions=6000, seed=1):
    """Write a fake clickstream file and return the number of rows written."""
    random.seed(seed)
    products = []
    for i in range(300):
        products.append((1000 + i, random.choice(CATEGORIES), random.choice(BRANDS), round(random.uniform(5, 1200), 2)))
    users = list(range(1, max(sessions // 2, 10)))
    start = datetime.datetime(2020, 9, 24)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    rows = 0
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["event_time", "event_type", "product_id", "category_id", "category_code",
                         "brand", "price", "user_id", "user_session"])
        for s in range(sessions):
            user = random.choice(users)
            session = f"sess-{s}"
            t = start + datetime.timedelta(seconds=random.randint(0, 150 * 86400))
            for _ in range(random.randint(1, 12)):
                p = random.choice(products)
                t += datetime.timedelta(seconds=random.randint(5, 600))
                r = random.random()
                event_type = "view" if r < 0.85 else ("cart" if r < 0.95 else "purchase")
                writer.writerow([t.strftime("%Y-%m-%d %H:%M:%S") + " UTC", event_type, p[0], 2000 + p[0] % 50,
                                 p[1], p[2], p[3], user, session])
                rows += 1
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=6000)
    parser.add_argument("--out", default="data/events.csv")
    args = parser.parse_args()
    print(f"Wrote {generate(args.out, args.sessions):,} rows to {args.out}")

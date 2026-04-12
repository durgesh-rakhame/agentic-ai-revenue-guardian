"""
============================================================
PROJECT : Agentic AI Revenue Guardian
FILE    : 2_data_generator.py
PURPOSE : Generate 30 days of realistic (messy) sales data
          with 3 hidden anomaly events built in.
          Output: sales_data.csv, web_logs.csv
AUTHOR  : Durgesh Rakhame
============================================================

HOW TO RUN:
    pip install pandas numpy
    python 2_data_generator.py

WHAT IT GENERATES:
    - 30 days of hourly sales for 5 products
    - 3 planted anomaly events:
        Event 1 (Day 7 ):  90% sales drop due to 404 errors on product page
        Event 2 (Day 15):  80% sales drop due to payment gateway 500 errors
        Event 3 (Day 23):  70% sales drop due to server timeout errors
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
import random

# ── Reproducibility ─────────────────────────────────────
random.seed(42)
np.random.seed(42)

# ── Constants ────────────────────────────────────────────
START_DATE   = date(2024, 1, 1)
NUM_DAYS     = 30
BUSINESS_HOURS = list(range(9, 22))   # 9 AM to 9 PM (peak sales window)

# ── Product catalogue (mirrors dim_products table) ───────
PRODUCTS = [
    {"product_id": "P001", "product_name": "Wireless Earbuds",   "price": 1299.0},
    {"product_id": "P002", "product_name": "Laptop Stand",        "price": 899.0},
    {"product_id": "P003", "product_name": "USB-C Hub",           "price": 599.0},
    {"product_id": "P004", "product_name": "Mechanical Keyboard", "price": 2499.0},
    {"product_id": "P005", "product_name": "Webcam HD",           "price": 1799.0},
]

# ── Anomaly event definitions ────────────────────────────
# Each event = one day where sales drop + web errors spike
ANOMALY_EVENTS = {
    7:  {
        "error_type":    "404_NOT_FOUND",
        "affected_page": "/product/wireless-earbuds",
        "drop_factor":   0.10,    # Sales fall to 10% of normal (90% drop)
        "error_count":   random.randint(800, 1200),
        "description":   "Product page returning 404 — customers can't find the item"
    },
    15: {
        "error_type":    "500_PAYMENT_GATEWAY",
        "affected_page": "/checkout/payment",
        "drop_factor":   0.20,    # Sales fall to 20% of normal (80% drop)
        "error_count":   random.randint(600, 900),
        "description":   "Payment gateway returning 500 errors — customers can't complete purchase"
    },
    23: {
        "error_type":    "503_SERVER_TIMEOUT",
        "affected_page": "/api/cart",
        "drop_factor":   0.30,    # Sales fall to 30% of normal (70% drop)
        "error_count":   random.randint(400, 700),
        "description":   "Cart API timing out — customers losing items before checkout"
    },
}

# ─────────────────────────────────────────────────────────
# SECTION 1: Generate Sales Data
# ─────────────────────────────────────────────────────────

def generate_normal_units(product_price: float) -> int:
    """
    Generate a realistic number of units sold per hour.
    More expensive items sell fewer units — realistic market behavior.
    """
    if product_price < 700:
        base = random.randint(8, 25)
    elif product_price < 1500:
        base = random.randint(4, 15)
    else:
        base = random.randint(1, 8)

    # Add some natural noise (weekend peaks, random spikes)
    noise = np.random.normal(0, 1.5)
    return max(1, int(base + noise))


def generate_sales_data() -> pd.DataFrame:
    """
    Create 30 days × business hours × 5 products of sales records.
    Inject anomaly events on days 7, 15, and 23.
    """
    rows = []

    for day_num in range(NUM_DAYS):
        current_date = START_DATE + timedelta(days=day_num)
        is_anomaly_day = (day_num + 1) in ANOMALY_EVENTS  # day_num is 0-indexed
        anomaly = ANOMALY_EVENTS.get(day_num + 1, {})

        for hour in BUSINESS_HOURS:
            for product in PRODUCTS:

                # Generate base units sold
                units = generate_normal_units(product["price"])

                # Apply anomaly drop factor if today is an anomaly day
                if is_anomaly_day:
                    drop = anomaly["drop_factor"]
                    units = max(0, int(units * drop))

                # Add random discount (5–20% occasionally)
                discount = round(random.choice([0, 0, 0, 5, 10, 15, 20]), 2)
                price_after_discount = product["price"] * (1 - discount / 100)
                revenue = round(units * price_after_discount, 2)

                rows.append({
                    "product_id":   product["product_id"],
                    "product_name": product["product_name"],
                    "sale_date":    current_date.isoformat(),
                    "sale_hour":    hour,
                    "units_sold":   units,
                    "revenue":      revenue,
                    "discount_pct": discount,
                })

    df = pd.DataFrame(rows)
    print(f"[✓] Sales data generated: {len(df)} rows")
    return df


# ─────────────────────────────────────────────────────────
# SECTION 2: Generate Web Error Logs
# ─────────────────────────────────────────────────────────

def generate_web_logs() -> pd.DataFrame:
    """
    Create web server error log data.
    Normal days have low error counts (background noise).
    Anomaly days have massive error spikes correlated with sales drops.
    """
    rows = []
    servers = ["server-01", "server-02", "server-03"]

    for day_num in range(NUM_DAYS):
        current_date = START_DATE + timedelta(days=day_num)
        is_anomaly_day = (day_num + 1) in ANOMALY_EVENTS
        anomaly = ANOMALY_EVENTS.get(day_num + 1, {})

        for hour in range(24):  # Log all 24 hours (not just business hours)

            # ── Normal background errors (every site has some) ──
            rows.append({
                "log_date":      current_date.isoformat(),
                "log_hour":      hour,
                "error_type":    "404_NOT_FOUND",
                "error_count":   random.randint(2, 15),    # Low baseline noise
                "affected_page": "/misc/broken-links",
                "server_id":     random.choice(servers),
            })

            # ── Anomaly spike: inject huge errors during business hours ──
            if is_anomaly_day and hour in BUSINESS_HOURS:
                rows.append({
                    "log_date":      current_date.isoformat(),
                    "log_hour":      hour,
                    "error_type":    anomaly["error_type"],
                    "error_count":   anomaly["error_count"] + random.randint(-50, 50),
                    "affected_page": anomaly["affected_page"],
                    "server_id":     random.choice(servers),
                })

    df = pd.DataFrame(rows)
    print(f"[✓] Web logs generated: {len(df)} rows")
    return df


# ─────────────────────────────────────────────────────────
# MAIN: Run and save to CSV
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🚀 Agentic AI Revenue Guardian — Data Generator")
    print("=" * 50)

    sales_df = generate_sales_data()
    logs_df  = generate_web_logs()

    # Save to CSV
    sales_df.to_csv("sales_data.csv", index=False)
    logs_df.to_csv("web_logs.csv",   index=False)

    print("\n📁 Files saved:")
    print("   → sales_data.csv")
    print("   → web_logs.csv")

    # Quick sanity check — show anomaly vs normal revenue
    print("\n📊 Daily Revenue Summary (sample):")
    daily = sales_df.groupby("sale_date")["revenue"].sum().reset_index()
    daily.columns = ["date", "total_revenue"]
    print(daily.to_string(index=False))

    print("\n✅ Data generation complete. Run 3_anomaly_detection.py next.")

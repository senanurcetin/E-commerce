"""Generate deterministic synthetic raw data for the DuckDB demo/CI targets.

Writes seeds/raw_gz_*.csv with the same column names as the real raw tables
(including quirks such as `pdt_id`, `purchse_PRICE`, `logCost`, `camPGN_name`
and `shipping_fee_1`). The data deliberately contains edge cases that the
models and tests are expected to handle:

  * orders without a shipping record          -> operational margin must not be NULL
  * a sold product missing from the product table -> relationships warning
  * days with ad spend but no orders          -> must stay visible in the daily mart
  * several ad platforms/campaigns on one day -> campaign union + daily rollup

It also writes seeds/gwz_finance_*.csv, a small synthetic copy of the order-level Google Sheets
export (BigQuery dataset `fvt_gsheet`) used by the `source_system: fvt_gsheet` mode: one orders,
shipping and refund row per order plus one campaign row per day, with a zero-revenue order and an
order without a shipping row as edge cases.

Usage: python scripts/generate_seed_data.py
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "seeds"
START = date(2023, 1, 1)
DAYS = 90
N_PRODUCTS = 30
MISSING_PRODUCT_ID = 1099          # sold, but absent from raw_gz_product
NO_ORDER_DAYS = {date(2023, 2, 14), date(2023, 3, 5)}
NO_SHIP_EVERY = 37                 # every 37th order has no shipping row

ADS = {
    # seed table -> (paid_source, key prefix, campaigns, daily cost scale)
    "adwords": ("adwords", "adw", ["Brand", "Generic", "Shopping"], 60.0),
    "bing": ("bing", "bng", ["Brand", "Generic"], 25.0),
    "criterio": ("criteo", "cri", ["Retargeting", "Prospecting"], 40.0),
    "facebook": ("facebook", "fbk", ["Lookalike", "Retargeting", "Spring Promo"], 45.0),
}


def write(name, header, rows):
    path = SEED_DIR / f"raw_gz_{name}.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"{path.name}: {len(rows)} rows")


def main():
    rng = random.Random(42)
    SEED_DIR.mkdir(exist_ok=True)

    product_ids = [1000 + i for i in range(1, N_PRODUCTS + 1)]
    prices = {pid: round(rng.uniform(2.0, 40.0), 2) for pid in product_ids}
    prices[MISSING_PRODUCT_ID] = round(rng.uniform(5.0, 20.0), 2)  # used only for revenue
    write(
        "product",
        ["products_id", "purchse_PRICE"],
        [(pid, prices[pid]) for pid in product_ids],
    )

    sales, ship = [], []
    order_id = 100000
    for offset in range(DAYS):
        day = START + timedelta(days=offset)
        if day in NO_ORDER_DAYS:
            continue
        # mild weekly seasonality: more orders on weekends
        n_orders = rng.randint(9, 16) + (4 if day.weekday() >= 5 else 0)
        for _ in range(n_orders):
            order_id += 1
            n_lines = rng.randint(1, 4)
            pool = product_ids + ([MISSING_PRODUCT_ID] if order_id % 53 == 0 else [])
            products = rng.sample(pool, n_lines)
            if order_id % 53 == 0 and MISSING_PRODUCT_ID not in products:
                products[0] = MISSING_PRODUCT_ID
            order_revenue = 0.0
            for pid in products:
                qty = rng.randint(1, 5)
                revenue = round(qty * prices[pid] * rng.uniform(1.25, 1.7), 2)
                order_revenue += revenue
                sales.append((day.isoformat(), order_id, pid, revenue, qty))
            if order_id % NO_SHIP_EVERY == 0:
                continue  # edge case: no shipping record
            fee = round(rng.choice([0.0, 4.9, 5.9, 7.9]) if order_revenue < 80 else 0.0, 2)
            ship.append(
                (
                    order_id,
                    fee,
                    fee,
                    round(rng.uniform(1.0, 4.0), 2),   # logCost
                    round(rng.uniform(2.0, 6.5), 2),   # ship_cost
                )
            )
    write("sales", ["date_date", "orders_id", "pdt_id", "revenue", "quantity"], sales)
    write("ship", ["orders_id", "shipping_fee", "shipping_fee_1", "logCost", "ship_cost"], ship)

    for table, (source, prefix, campaigns, scale) in ADS.items():
        rows = []
        for offset in range(DAYS):
            day = START + timedelta(days=offset)
            for idx, campaign in enumerate(campaigns, start=1):
                impressions = int(rng.uniform(800, 6000) * scale / 40)
                clicks = int(impressions * rng.uniform(0.01, 0.06))
                cost = round(clicks * rng.uniform(0.06, 0.32), 2)
                rows.append(
                    (day.isoformat(), source, f"{prefix}_{idx:02d}",
                     f"{campaign}", cost, impressions, clicks)
                )
        write(
            table,
            ["date_date", "paid_source", "campaign_key", "camPGN_name", "ads_cost", "impression", "click"],
            rows,
        )


def generate_gsheet():
    rng = random.Random(2021)
    start, days, per_day = date(2021, 10, 1), 15, 60
    orders, shipping, refund, campaign = [], [], [], []
    order_id, line = 1002561, 0
    for offset in range(days):
        day = start + timedelta(days=offset)
        stamp = f"{day.isoformat()} 00:00:00UTC"
        for _ in range(per_day):
            order_id += 1
            line += 1
            turnover = 0.0 if line % 97 == 0 else round(rng.uniform(5, 150), 2)  # edge: free order
            purchase = round(turnover * rng.uniform(0.5, 0.9), 2) if turnover else round(rng.uniform(1, 30), 2)
            fee = rng.choice([0.0, 0.93, 3.43, 7.35])
            orders.append((line, fee, stamp, order_id, purchase, turnover))
            if line % 211 != 0:  # edge: order without a shipping row
                shipping.append((line, order_id, round(rng.uniform(2, 10), 2), day.isoformat(), rng.randint(2, 8)))
            refund.append((line, stamp, order_id, rng.randint(50, 500)))
        hour = rng.randint(6, 22)
        campaign.append((offset + 1, f"{day.isoformat()} {hour:02d}:00:00UTC", round(rng.uniform(3800, 5000), 2)))

    def write_gs(name, header, rows):
        path = SEED_DIR / f"gwz_finance_{name}.csv"
        with path.open("w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)
        print(f"{path.name}: {len(rows)} rows")

    write_gs("orders_orders", ["_line", "ship_fee", "datetime", "orders_id", "purchase_cost", "turnover"], orders)
    write_gs("shipping_shipping", ["_line", "orders_id", "log_cost", "date_date", "ship_cost"], shipping)
    write_gs("refund_sheet_1", ["_line", "datetime", "orders_id", "refund"], refund)
    write_gs("campaign", ["_row", "datetime", "cost"], campaign)


if __name__ == "__main__":
    main()
    generate_gsheet()

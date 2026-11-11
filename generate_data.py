"""Generate a fully synthetic, reproducible FrostBite transaction history."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

COUNTRIES = ["United Kingdom", "Germany", "France", "Italy", "Spain", "Poland"]
COUNTRY_P = [0.22, 0.19, 0.16, 0.16, 0.15, 0.12]
METHODS = ["Card", "Digital wallet", "Bank transfer", "BNPL"]
METHOD_P = [0.60, 0.25, 0.10, 0.05]
PRODUCTS = ["Game licenses", "In-game currency", "DLC", "Subscriptions"]
PRODUCT_P = [0.35, 0.30, 0.22, 0.13]

def generate_transactions(n=3000, seed=42, output=None):
    rng = np.random.default_rng(seed)
    # Six-month mature cohort: transactions end 90 days before the reporting date,
    # ensuring every generated chargeback (10-90 days later) is observable.
    report_date = pd.Timestamp.today().normalize()
    end = report_date - pd.Timedelta(days=90)
    start = end - pd.DateOffset(months=6)
    dates = pd.to_datetime(rng.integers(start.value // 10**9, end.value // 10**9, n), unit="s").normalize()
    countries = rng.choice(COUNTRIES, n, p=COUNTRY_P)
    methods = rng.choice(METHODS, n, p=METHOD_P)
    products = rng.choice(PRODUCTS, n, p=PRODUCT_P)
    first = rng.random(n) < 0.30
    account_age = np.where(first, rng.integers(0, 31, n), rng.integers(31, 1800, n))
    prior = np.where(first, 0, rng.integers(1, 80, n))
    amounts = np.clip(rng.lognormal(mean=3.65, sigma=0.95, size=n), 5, 250).round(2)

    # Base probability is calibrated to produce roughly 1.5-2.0% chargebacks.
    p = np.full(n, 0.006)
    p += first * 0.020
    p += (methods == "Card") * 0.009
    p += (methods == "Digital wallet") * 0.0015
    p += (amounts > 100) * 0.010
    p += (products == "In-game currency") * 0.008
    p += np.isin(countries, ["Italy", "Spain", "Poland"]) * 0.005
    p += (account_age < 14) * 0.008
    p = np.clip(p * 0.62, 0.001, 0.08)
    chargeback = rng.random(n) < p

    reasons = np.array([""] * n, dtype=object)
    reason_pool = ["Fraud / card not present", "Friendly fraud", "Product not received", "Processing error"]
    reasons[chargeback] = rng.choice(reason_pool, chargeback.sum(), p=[0.48, 0.30, 0.18, 0.04])
    cb_dates = np.array([None] * n, dtype=object)
    delays = rng.integers(10, 91, chargeback.sum())
    for ix, delay in zip(np.where(chargeback)[0], delays):
        cb_dates[ix] = (dates[ix] + pd.Timedelta(days=int(delay))).date().isoformat()

    df = pd.DataFrame({
        "transaction_id": [f"FB-{i+1:06d}" for i in range(n)],
        "customer_id": [f"CUST-{x:05d}" for x in rng.integers(1, int(n*0.72)+1, n)],
        "transaction_date": dates.date.astype(str),
        "country": countries,
        "payment_method": methods,
        "product_category": products,
        "amount_eur": amounts,
        "first_time_buyer": first,
        "account_age_days": account_age,
        "prior_transactions": prior,
        "chargeback": chargeback,
        "chargeback_date": cb_dates,
        "chargeback_reason": reasons,
    })
    if output:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/transactions.csv")
    args = parser.parse_args()
    data = generate_transactions(args.rows, args.seed, args.output)
    print(f"Created {len(data):,} synthetic transactions at {args.output}")
    print(f"Chargebacks: {int(data.chargeback.sum())} ({data.chargeback.mean():.2%})")

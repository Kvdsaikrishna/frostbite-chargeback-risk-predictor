# FrostBite Gaming — Chargeback Risk Predictor

A Streamlit-based chargeback analytics and explainable transaction-risk demo. It uses **synthetic data only** and includes both stretch goals: configurable risk weights and a financial impact simulator.

## Features

- Executive dashboard: chargeback KPIs, daily/weekly trends, payment method, product, country and country × product × method explorer.
- Date and country filters that update all dashboard views.
- Time-to-chargeback histogram (synthetic delays are 10–90 days).
- CSV upload and batch scoring (0–100), explanations and sortable/filterable results.
- Top-decile manual-review queue.
- Risk-weight tuning with score comparison and top-decile overlap.
- Threshold simulator estimating review volume, prevented disputes, review cost and net impact.
- Reproducible synthetic data generator and basic tests.

## Requirements

- Python 3.10+
- pip

## Run locally (Windows PowerShell)

```powershell
# 1. Unzip the project and open a terminal in the project folder
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install packages
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. (Optional) Regenerate the 3,000-row synthetic dataset
python scripts/generate_data.py --rows 3000 --seed 42 --output data/transactions.csv

# 4. Start the app
streamlit run app.py
```

Open the local URL printed by Streamlit (normally http://localhost:8501).

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_data.py --rows 3000 --seed 42 --output data/transactions.csv
streamlit run app.py
```

## CSV upload schema

Required columns:

| Column | Type / examples |
|---|---|
| `transaction_id` | string, unique ID |
| `country` | United Kingdom, Germany, France, Italy, Spain, Poland |
| `payment_method` | Card, Digital wallet, Bank transfer, BNPL |
| `product_category` | Game licenses, In-game currency, DLC, Subscriptions |
| `amount_eur` | numeric EUR amount |
| `first_time_buyer` | true/false, yes/no, 1/0 |
| `account_age_days` | integer |

Optional columns such as `customer_id`, `prior_transactions`, and `transaction_date` are retained in the scored output.

## Risk model

The transparent heuristic allocates a 0–100 score across six configurable dimensions: payment method, first-time buyer, amount above €100, country, product category and account age. Component priors are deliberately illustrative and documented in `risk_engine.py`; the weights are normalised to 100. The score is **not a calibrated probability** and should not be used as an automatic decline decision. The top 10% by score is separately marked for manual review.

The demo country/product priors encode synthetic patterns, not real-world assertions about countries or product categories. A production model should be trained and calibrated using matured labels, temporal validation, reason-code review, monitoring, privacy controls and fairness checks.

## Synthetic data

`data/transactions.csv` contains 3,000 generated transactions across six European countries, four payment methods and four product categories. The generator uses a fixed seed for reproducibility and adds chargeback delays of 10–90 days. It creates a mature six-month transaction cohort (the transaction window ends 90 days before generation date) so the outcome labels have time to occur. No real customer or payment data is included.

Regenerate:
```bash
python scripts/generate_data.py --rows 3000 --seed 42
```

## Tests

```bash
pytest -q
```

## Deploy publicly

### Streamlit Community Cloud (recommended for this demo)
1. Push this repository to a **public GitHub repository**.
2. Visit https://share.streamlit.io/ and sign in with GitHub.
3. Choose the repository, branch `main`, and main file path `app.py`.
4. Deploy. Streamlit installs packages from `requirements.txt`.
5. Confirm the app opens in an incognito/private browser and test the upload flow.

Keep `data/transactions.csv` committed because the app uses it as its demo dataset. Do not commit real customer data, secrets, or credentials.

## Demo walkthrough (2–4 minutes)

See `DEMO_SCRIPT.md` for a timed walkthrough. Screenshots can be captured from the running app and stored under `screenshots/`.

## Project writeup

See `PROJECT_WRITEUP.md` for the 5–10 sentence methodology and findings summary.

## Limitations / production considerations

- The dataset is synthetic and the scoring priors are illustrative, so the displayed rates and patterns are demo findings only.
- The simulator is a scenario estimate, not a causal estimate or guarantee of avoided losses.
- This prototype does not connect to a payment gateway, issuer, card network or live fraud feed.
- Production rollout needs authenticated access, role-based permissions, audit logs, secure storage, PCI/privacy review, model validation, drift monitoring and a documented manual-review process.

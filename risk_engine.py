"""Explainable, configurable chargeback risk scoring for synthetic/demo transactions."""
from __future__ import annotations
import pandas as pd

DEFAULT_WEIGHTS = {
    "payment_method": 20.0,
    "first_time_buyer": 20.0,
    "high_amount": 15.0,
    "country": 15.0,
    "product_category": 15.0,
    "account_age": 15.0,
}
DEFAULT_THRESHOLDS = {"medium": 31, "high": 61}

# These are illustrative priors for the demo, not claims about real countries or issuers.
COUNTRY_RISK = {"Italy": 1.0, "Spain": 0.8, "Poland": 0.7, "France": 0.45,
                "Germany": 0.35, "United Kingdom": 0.3}
PRODUCT_RISK = {"In-game currency": 1.0, "DLC": 0.65,
                "Game licenses": 0.4, "Subscriptions": 0.25}
PAYMENT_RISK = {"Card": 1.0, "Digital wallet": 0.35,
                "Bank transfer": 0.05, "BNPL": 0.15}

def _normalise_weights(weights):
    merged = DEFAULT_WEIGHTS.copy()
    if weights:
        merged.update({k: max(0.0, float(v)) for k, v in weights.items() if k in merged})
    total = sum(merged.values())
    if total <= 0:
        return DEFAULT_WEIGHTS.copy()
    return {k: v / total * 100.0 for k, v in merged.items()}

def score_transactions(transactions: pd.DataFrame, weights=None) -> pd.DataFrame:
    """Return a copy with 0-100 score, risk band and human-readable reasons."""
    df = transactions.copy()
    w = _normalise_weights(weights)
    components = {
        "payment_method": df.get("payment_method", pd.Series("", index=df.index)).map(PAYMENT_RISK).fillna(0.35),
        "first_time_buyer": df.get("first_time_buyer", pd.Series(False, index=df.index)).astype(str).str.lower().isin(["true", "1", "yes", "y"]).astype(float),
        "high_amount": (pd.to_numeric(df.get("amount_eur", pd.Series(0, index=df.index)), errors="coerce").fillna(0) > 100).astype(float),
        "country": df.get("country", pd.Series("", index=df.index)).map(COUNTRY_RISK).fillna(0.3),
        "product_category": df.get("product_category", pd.Series("", index=df.index)).map(PRODUCT_RISK).fillna(0.3),
        "account_age": (1 - (pd.to_numeric(df.get("account_age_days", pd.Series(365, index=df.index)), errors="coerce").fillna(365).clip(0, 365) / 365)).clip(0, 1),
    }
    # Payment method, country and category priors are scaled by their factor weights.
    score = sum(components[k] * w[k] for k in components).clip(0, 100)
    reasons = []
    labels = {
        "payment_method": "card payment",
        "first_time_buyer": "first-time buyer",
        "high_amount": "transaction above €100",
        "country": "country with elevated demo risk prior",
        "product_category": "higher-risk product category",
        "account_age": "new customer account",
    }
    for idx in df.index:
        row_reasons = []
        for key, vals in components.items():
            val = float(vals.loc[idx])
            if val >= 0.65 and w[key] >= 3:
                row_reasons.append(labels[key])
        if not row_reasons:
            row_reasons.append("no major configured risk indicators")
        reasons.append(" + ".join(row_reasons))
    df["risk_score"] = score.round(1)
    df["risk_reasons"] = reasons
    df["risk_band"] = pd.cut(df["risk_score"], bins=[-0.01, 30, 60, 100],
                             labels=["Low", "Medium", "High"], include_lowest=True).astype(str)
    return df

def top_decile_ids(scored: pd.DataFrame):
    """IDs in the top 10% by score; deterministic and always at least one for non-empty input."""
    if scored.empty:
        return set()
    n = max(1, int(-(-len(scored) // 10)))
    ordered = scored.sort_values(["risk_score"], ascending=False)
    return set(ordered.head(n).get("transaction_id", ordered.head(n).index).astype(str))

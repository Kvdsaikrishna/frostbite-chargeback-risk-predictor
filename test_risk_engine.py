import pandas as pd
from risk_engine import score_transactions, top_decile_ids

def test_scores_are_bounded_and_explainable():
    df = pd.DataFrame([{
        "transaction_id":"A", "payment_method":"Card", "first_time_buyer":True,
        "amount_eur":180, "country":"Italy", "product_category":"In-game currency",
        "account_age_days":1
    }])
    result = score_transactions(df)
    assert 0 <= result.loc[0,"risk_score"] <= 100
    assert "first-time buyer" in result.loc[0,"risk_reasons"]
    assert result.loc[0,"risk_band"] == "High"

def test_top_decile():
    df = pd.DataFrame({"transaction_id":[f"T{i}" for i in range(100)],
                       "risk_score":range(100)})
    assert len(top_decile_ids(df)) == 10

from pathlib import Path
import io
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from risk_engine import DEFAULT_WEIGHTS, score_transactions, top_decile_ids

st.set_page_config(page_title="FrostBite | Chargeback Intelligence", page_icon="🧊",
                   layout="wide", initial_sidebar_state="expanded")

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "transactions.csv"

st.markdown("""
<style>
.stApp {background: #0b1220; color: #e8eef8;}
[data-testid="stSidebar"] {background: #111c30;}
[data-testid="stMetric"] {background: linear-gradient(135deg,#17243a,#101a2b); padding: 16px; border:1px solid #263a58; border-radius:14px;}
.block-container {padding-top: 1.5rem; max-width: 1500px;}
h1,h2,h3 {color:#f4f7fb;}
div[data-testid="stDataFrame"] {border:1px solid #263a58; border-radius:10px;}
.small-muted {color:#93a4bd;font-size:0.85rem;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_demo_data():
    return pd.read_csv(DATA_PATH)

def clean_upload(df):
    required = ["transaction_id","country","payment_method","product_category","amount_eur",
                "first_time_buyer","account_age_days"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    df = df.copy()
    df["amount_eur"] = pd.to_numeric(df["amount_eur"], errors="coerce")
    df["account_age_days"] = pd.to_numeric(df["account_age_days"], errors="coerce").fillna(365)
    if df["amount_eur"].isna().any() or (df["amount_eur"] < 0).any():
        raise ValueError("amount_eur must contain valid non-negative numbers.")
    return df

def chargeback_rate(df):
    if df.empty: return 0.0
    return pd.to_numeric(df["chargeback"], errors="coerce").fillna(0).astype(bool).mean()

st.sidebar.title("🧊 FrostBite")
st.sidebar.caption("CHARGEBACK INTELLIGENCE")
page = st.sidebar.radio("Workspace", ["Executive dashboard", "Transaction risk scoring",
                                       "Risk model tuning", "Financial impact simulator"])
st.sidebar.divider()
st.sidebar.caption("DEMO ENVIRONMENT")
st.sidebar.success("Synthetic data only")
st.sidebar.caption("3,000 synthetic transactions · 6-month mature cohort")

try:
    raw = load_demo_data()
except Exception as e:
    st.error(f"Could not load demo data: {e}")
    st.stop()

raw["transaction_date"] = pd.to_datetime(raw["transaction_date"], errors="coerce")
raw["chargeback"] = raw["chargeback"].astype(str).str.lower().isin(["true","1","yes"])
if "chargeback_date" in raw:
    raw["chargeback_date_parsed"] = pd.to_datetime(raw["chargeback_date"], errors="coerce")
raw["time_to_chargeback_days"] = (raw["chargeback_date_parsed"] - raw["transaction_date"]).dt.days

if "weights" not in st.session_state:
    st.session_state.weights = DEFAULT_WEIGHTS.copy()
scored_all = score_transactions(raw, st.session_state.weights)

if page == "Executive dashboard":
    st.title("Chargeback overview")
    st.markdown('<p class="small-muted">Historical monitoring across FrostBite’s synthetic European transaction cohort.</p>', unsafe_allow_html=True)
    min_date = raw.transaction_date.min().date()
    max_date = raw.transaction_date.max().date()
    with st.sidebar:
        st.subheader("Dashboard filters")
        date_range = st.date_input("Transaction date range", value=(min_date, max_date),
                                   min_value=min_date, max_value=max_date)
        countries = st.multiselect("Countries", sorted(raw.country.unique()), default=sorted(raw.country.unique()))
        granularity = st.radio("Trend aggregation", ["Daily", "Weekly"], horizontal=True)
    filtered = raw[raw.country.isin(countries)].copy()
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        filtered = filtered[filtered.transaction_date.dt.date.between(date_range[0], date_range[1])]
    cb_count = int(filtered.chargeback.sum())
    rate = chargeback_rate(filtered)
    total_value = filtered.amount_eur.sum()
    prior_rate = chargeback_rate(raw)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Transactions", f"{len(filtered):,}")
    c2.metric("Chargeback rate", f"{rate:.2%}", f"{(rate-prior_rate)*100:+.2f} pp vs full cohort")
    c3.metric("Chargebacks", f"{cb_count:,}")
    c4.metric("Gross transaction value", f"€{total_value:,.0f}")
    st.divider()
    left,right = st.columns([1.55,1])
    with left:
        st.subheader("Chargeback rate over time")
        if not filtered.empty:
            freq = "D" if granularity == "Daily" else "W-MON"
            trend = filtered.set_index("transaction_date").resample(freq).agg(
                transactions=("transaction_id","count"), chargebacks=("chargeback","sum"))
            trend["chargeback_rate"] = trend.chargebacks / trend.transactions.replace(0,np.nan)
            trend = trend.reset_index()
            fig = px.line(trend, x="transaction_date", y="chargeback_rate", markers=True,
                          labels={"transaction_date":"Transaction date","chargeback_rate":"Chargeback rate"})
            fig.update_traces(line_color="#63d6c5", marker_color="#63d6c5")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", yaxis_tickformat=".1%")
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Payment method mix & rate")
        method = filtered.groupby("payment_method").agg(
            transactions=("transaction_id","count"), chargebacks=("chargeback","sum")).reset_index()
        method["rate"] = method.chargebacks / method.transactions
        fig = px.bar(method, x="payment_method", y="rate", color="rate",
                     color_continuous_scale=["#3a8f88","#f0b35a","#ed6b73"],
                     labels={"rate":"Chargeback rate","payment_method":"Payment method"})
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", yaxis_tickformat=".1%", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    left,right = st.columns(2)
    with left:
        st.subheader("Product category exposure")
        prod = filtered.groupby("product_category").agg(
            transactions=("transaction_id","count"), chargebacks=("chargeback","sum")).reset_index()
        prod["chargeback_rate"] = prod.chargebacks / prod.transactions
        fig = px.bar(prod.sort_values("chargeback_rate"), x="chargeback_rate", y="product_category",
                     orientation="h", text=prod.sort_values("chargeback_rate").chargeback_rate.map(lambda x:f"{x:.2%}"),
                     labels={"chargeback_rate":"Chargeback rate","product_category":"Product"})
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", xaxis_tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Country risk comparison")
        country = filtered.groupby("country").agg(
            transactions=("transaction_id","count"), chargebacks=("chargeback","sum")).reset_index()
        country["chargeback_rate"] = country.chargebacks / country.transactions
        fig = px.bar(country.sort_values("chargeback_rate"), x="country", y="chargeback_rate",
                     color="chargeback_rate", color_continuous_scale=["#3a8f88","#ed6b73"],
                     labels={"chargeback_rate":"Chargeback rate","country":"Country"})
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", yaxis_tickformat=".1%", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    st.subheader("Time from transaction to chargeback")
    delays = filtered.loc[filtered.chargeback, "time_to_chargeback_days"].dropna()
    if len(delays):
        fig = px.histogram(delays, nbins=16, labels={"value":"Days to chargeback","count":"Chargebacks"})
        fig.update_traces(marker_color="#a78bfa")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Median delay: {delays.median():.0f} days · range: {delays.min():.0f}–{delays.max():.0f} days")
    else:
        st.info("No chargebacks in the selected filters.")
    st.subheader("Country × product × payment method explorer")
    pivot = filtered.groupby(["country","product_category","payment_method"]).agg(
        transactions=("transaction_id","count"), chargebacks=("chargeback","sum")).reset_index()
    pivot["chargeback_rate"] = pivot.chargebacks / pivot.transactions
    st.dataframe(pivot.sort_values("chargeback_rate",ascending=False).style.format({"chargeback_rate":"{:.2%}"}),
                 use_container_width=True, hide_index=True)

elif page == "Transaction risk scoring":
    st.title("Transaction risk scoring")
    st.markdown('<p class="small-muted">Score a new batch before processing. Upload a CSV or use the sample transactions.</p>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload transaction CSV", type=["csv"])
    if uploaded:
        try:
            batch = clean_upload(pd.read_csv(uploaded))
            st.success(f"Loaded {len(batch):,} transactions from upload.")
        except Exception as e:
            st.error(str(e)); batch = pd.DataFrame()
    else:
        st.info("No file uploaded — demo mode scores 250 held-out synthetic transactions.")
        batch = raw.tail(250).drop(columns=["chargeback_date_parsed","time_to_chargeback_days"], errors="ignore").copy()
        batch = batch.drop(columns=["chargeback","chargeback_date","chargeback_reason"], errors="ignore")
    if not batch.empty:
        scored = score_transactions(batch, st.session_state.weights)
        top_ids = top_decile_ids(scored)
        scored["manual_review"] = scored.transaction_id.astype(str).isin(top_ids)
        a,b,c = st.columns(3)
        a.metric("Scored transactions", f"{len(scored):,}")
        b.metric("Manual review queue", f"{len(top_ids):,}")
        c.metric("Average risk score", f"{scored.risk_score.mean():.1f}/100")
        min_score,max_score = st.slider("Filter risk score",0,100,(0,100))
        bands = st.multiselect("Risk bands",["High","Medium","Low"],default=["High","Medium","Low"])
        view = scored[scored.risk_score.between(min_score,max_score) & scored.risk_band.isin(bands)]
        view = view.sort_values("risk_score",ascending=False)
        st.dataframe(view[["transaction_id","country","payment_method","product_category","amount_eur",
                           "first_time_buyer","account_age_days","risk_score","risk_band","manual_review","risk_reasons"]],
                     use_container_width=True, hide_index=True,
                     column_config={"risk_score":st.column_config.ProgressColumn("Risk score",min_value=0,max_value=100,format="%.1f"),
                                    "manual_review":st.column_config.CheckboxColumn("Manual review")})
        st.download_button("Download scored transactions",scored.to_csv(index=False).encode(),
                           "frostbite_scored_transactions.csv","text/csv")
        st.subheader("Highest-priority transactions")
        st.dataframe(scored.sort_values("risk_score",ascending=False).head(10)[
            ["transaction_id","risk_score","risk_band","risk_reasons"]],use_container_width=True,hide_index=True)

elif page == "Risk model tuning":
    st.title("Risk model tuning")
    st.write("Adjust relative factor importance. Weights are normalised to 100 points automatically.")
    st.caption("The factor sliders change the model's relative contribution; they are not calibrated probabilities.")
    labels = {"payment_method":"Payment method","first_time_buyer":"First-time buyer",
              "high_amount":"Amount above €100","country":"Country","product_category":"Product category",
              "account_age":"Account age"}
    cols = st.columns(2)
    new_weights = {}
    for i,(key,label) in enumerate(labels.items()):
        with cols[i%2]:
            new_weights[key] = st.slider(label,0,40,int(st.session_state.weights.get(key,DEFAULT_WEIGHTS[key])),1)
    if st.button("Apply weights",type="primary"):
        st.session_state.weights = new_weights
        st.success("Weights applied. Scores on the scoring page will update.")
    if st.button("Reset default weights"):
        st.session_state.weights = DEFAULT_WEIGHTS.copy()
        st.rerun()
    before = score_transactions(raw, DEFAULT_WEIGHTS)
    after = score_transactions(raw, st.session_state.weights)
    compare = pd.DataFrame({"transaction_id":raw.transaction_id,
                            "default_score":before.risk_score,"tuned_score":after.risk_score})
    compare["score_change"] = compare.tuned_score - compare.default_score
    st.subheader("Impact on historical prioritisation")
    x,y,z = st.columns(3)
    x.metric("Mean score change",f"{compare.score_change.mean():+.1f}")
    y.metric("Transactions moved by >10 points",f"{(compare.score_change.abs()>10).sum():,}")
    z.metric("Top-decile overlap",f"{len(top_decile_ids(before)&top_decile_ids(after))/max(1,len(top_decile_ids(before))):.0%}")
    fig = px.scatter(compare.sample(min(800,len(compare)),random_state=4),x="default_score",y="tuned_score",
                     opacity=.5,labels={"default_score":"Default score","tuned_score":"Tuned score"})
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig,use_container_width=True)

elif page == "Financial impact simulator":
    st.title("Financial impact simulator")
    st.write("Estimate the operational trade-off of reviewing transactions above a selected risk score.")
    a,b,c = st.columns(3)
    threshold = a.slider("Review threshold",0,100,60)
    monthly_volume = b.number_input("Transactions per month",min_value=1000,max_value=1000000,value=50000,step=1000)
    analyst_hourly = c.number_input("Analyst cost (€/hour)",min_value=5.0,max_value=150.0,value=30.0,step=1.0)
    d,e = st.columns(2)
    review_minutes = d.slider("Review time per transaction (minutes)",1,30,4)
    prevention = e.slider("Preventable share of flagged chargebacks (%)",0,100,65)
    historical = score_transactions(raw,st.session_state.weights)
    flagged = historical[historical.risk_score >= threshold]
    review_rate = len(flagged)/max(1,len(historical))
    flagged_cb_rate = chargeback_rate(flagged)
    monthly_reviews = monthly_volume * review_rate
    estimated_flagged_cb = monthly_reviews * flagged_cb_rate
    prevented = estimated_flagged_cb * prevention/100
    avg_ticket = flagged.amount_eur.mean() if not flagged.empty else raw.amount_eur.mean()
    # €25 combines an illustrative €20 dispute fee and average principal at risk.
    benefit = prevented * (avg_ticket + 20)
    cost = monthly_reviews * review_minutes/60 * analyst_hourly
    net = benefit-cost
    x,y,z,w = st.columns(4)
    x.metric("Monthly review volume",f"{monthly_reviews:,.0f}",f"{review_rate:.1%} of transactions")
    y.metric("Estimated chargebacks prevented",f"{prevented:,.1f}")
    z.metric("Estimated gross benefit",f"€{benefit:,.0f}")
    w.metric("Estimated net impact",f"€{net:,.0f}",delta=f"Review cost €{cost:,.0f}")
    st.caption(f"Historical flagged-group chargeback rate: {flagged_cb_rate:.2%}. Average flagged ticket: €{avg_ticket:,.2f}.")
    st.warning("Illustrative scenario only: historical association is not causal proof. Prevention rate, dispute fees, and ticket value are assumptions; validate with controlled pilots before operational use.")
    thresholds = []
    for t in range(20,91,5):
        group=historical[historical.risk_score>=t]
        rr=len(group)/len(historical)
        rev=monthly_volume*rr
        prevented_t=rev*chargeback_rate(group)*prevention/100
        benefit_t=prevented_t*((group.amount_eur.mean() if len(group) else raw.amount_eur.mean())+20)
        cost_t=rev*review_minutes/60*analyst_hourly
        thresholds.append({"Threshold":t,"Review rate":rr,"Reviews/month":rev,"Estimated net €/month":benefit_t-cost_t})
    sim=pd.DataFrame(thresholds)
    fig=px.line(sim,x="Threshold",y="Estimated net €/month",markers=True)
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
    st.subheader("Net impact by threshold")
    st.plotly_chart(fig,use_container_width=True)
    st.dataframe(sim.style.format({"Review rate":"{:.1%}","Reviews/month":"{:,.0f}","Estimated net €/month":"€{:,.0f}"}),
                 use_container_width=True,hide_index=True)

st.sidebar.divider()
st.sidebar.caption("Risk scores are decision-support indicators, not fraud verdicts. Validate on real, consented, appropriately governed data before production use.")

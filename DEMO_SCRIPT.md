# Demo video script (2–4 minutes)

**0:00–0:20 — Intro**
- Open the public Streamlit app.
- Explain that this is a synthetic-data prototype for chargeback monitoring and pre-transaction triage.

**0:20–1:10 — Dashboard**
- Point out transaction count, chargeback rate, dispute count and gross value.
- Change the date range and country filter.
- Switch daily/weekly trend.
- Compare payment method, product category and country.
- Show the time-to-chargeback histogram and the country × product × payment method table.

**1:10–2:00 — Risk scoring**
- Open Transaction risk scoring.
- Explain the required CSV schema and upload a batch (or show demo batch).
- Sort/filter scores, show top-decile manual review flag and open the risk reasons.
- Download the scored CSV.

**2:00–2:35 — Stretch goal: tuning**
- Open Risk model tuning.
- Increase first-time-buyer or payment-method weight and apply.
- Show that prioritisation and top-decile overlap change.

**2:35–3:15 — Stretch goal: simulator**
- Open Financial impact simulator.
- Change threshold, monthly volume and analyst assumptions.
- Explain estimated reviews, potential prevention, costs and net impact.
- Call out that this is an illustrative scenario, not a guarantee.

**3:15–3:30 — Close**
- Mention that all data is synthetic and that production use requires validation, governance and integration.

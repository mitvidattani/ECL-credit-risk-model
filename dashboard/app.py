"""
ECL Portfolio Dashboard
========================

A small Streamlit app that puts notebooks 03 and 04 in front of a live,
interactive interface instead of a static notebook.

It does two things:
1. Shows the portfolio-level ECL results from notebook 03
   (data/processed/ecl_results.csv), with a live "stress multiplier"
   slider that recomputes stressed ECL on the fly.
2. Shows the Indian NBFC benchmark comparison from notebook 04, as
   static context underneath.

Run it with:
    streamlit run dashboard/app.py
"""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.patches import Patch
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "ecl_results.csv"

st.set_page_config(page_title="ECL Portfolio Dashboard", layout="wide")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


df = load_data()


# ---------------------------------------------------------------------------
# ECL logic — re-implemented here so the dashboard doesn't depend on
# re-running any notebook. This mirrors notebook 03's (corrected) staging
# and ECL formulas exactly:
#   - Stage 3 (known historical default, credit_risk == 0): PD is treated
#     as 100% since the default has already happened — ECL = LGD * EAD.
#   - Stage 2 (pd >= 0.50, not Stage 3): lifetime ECL = PD * LGD * EAD.
#   - Stage 1 (pd < 0.50, not Stage 3): 12-month ECL, prorating PD by
#     min(1, 12/duration).
# ---------------------------------------------------------------------------
def compute_staged_ecl(data: pd.DataFrame, pd_col: str) -> tuple[pd.Series, pd.Series]:
    """Returns (stage, ecl) Series computed from the given PD column."""
    pd_values = data[pd_col]

    is_stage3 = data["credit_risk"] == 0
    is_stage2 = (~is_stage3) & (pd_values >= 0.50)
    is_stage1 = (~is_stage3) & (~is_stage2)

    stage = pd.Series("Stage 1", index=data.index)
    stage[is_stage2] = "Stage 2"
    stage[is_stage3] = "Stage 3"

    ecl = pd.Series(0.0, index=data.index)
    ecl[is_stage3] = data.loc[is_stage3, "LGD"] * data.loc[is_stage3, "EAD"]
    ecl[is_stage2] = pd_values[is_stage2] * data.loc[is_stage2, "LGD"] * data.loc[is_stage2, "EAD"]

    pd_12m = pd_values[is_stage1] * (12 / data.loc[is_stage1, "duration"]).clip(upper=1.0)
    ecl[is_stage1] = pd_12m * data.loc[is_stage1, "LGD"] * data.loc[is_stage1, "EAD"]

    return stage, ecl


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Expected Credit Loss (ECL) Portfolio Dashboard")
st.write(
    "This dashboard summarizes the Probability of Default (PD), Loss Given "
    "Default (LGD), Exposure at Default (EAD), and resulting Expected "
    "Credit Loss (ECL) for a 1,000-applicant portfolio, built on the South "
    "German Credit dataset with IFRS 9 staging applied — full methodology "
    "and caveats are documented in `notebooks/02_pd_model.ipynb` and "
    "`notebooks/03_ecl_calculation.ipynb`. LGD and EAD are illustrative "
    "assumptions, not fitted values — see those notebooks' Limitations "
    "sections before treating any number here as a real loss forecast."
)

st.divider()

# ---------------------------------------------------------------------------
# KPI cards (base case, as saved by notebook 03)
# ---------------------------------------------------------------------------
total_base_ecl = df["ecl"].sum()
total_ead = df["EAD"].sum()
ecl_pct = total_base_ecl / total_ead * 100
stage_counts = df["stage"].value_counts().reindex(["Stage 1", "Stage 2", "Stage 3"]).fillna(0).astype(int)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total base-case ECL", f"{total_base_ecl:,.0f} DM")
kpi2.metric("Total EAD", f"{total_ead:,.0f} DM")
kpi3.metric("ECL % of portfolio", f"{ecl_pct:.1f}%")
kpi4.metric("Applicants by stage", f"{len(df):,}")
kpi4.caption(f"Stage 1: {stage_counts['Stage 1']} | Stage 2: {stage_counts['Stage 2']} | Stage 3: {stage_counts['Stage 3']}")

st.divider()

# ---------------------------------------------------------------------------
# Interactive stress scenario
# ---------------------------------------------------------------------------
st.header("Stress scenario")
st.write(
    "Move the slider to see how total portfolio ECL responds to a stress "
    "shock applied to every applicant's PD (capped at 100%). This is the "
    "same mechanism as notebook 03's scenario analysis, just made "
    "interactive — an illustrative shock, not a calibrated macroeconomic "
    "scenario."
)

stress_multiplier = st.slider(
    "Stress multiplier (applied to every applicant's PD)",
    min_value=0.5, max_value=3.0, value=1.5, step=0.1,
)

df["pd_stressed_live"] = (df["pd_estimate"] * stress_multiplier).clip(upper=1.0)
_, ecl_stressed_live = compute_staged_ecl(df, "pd_stressed_live")
total_stressed_ecl = ecl_stressed_live.sum()
pct_change = (total_stressed_ecl - total_base_ecl) / total_base_ecl * 100

col1, col2 = st.columns(2)
col1.metric(
    f"Stressed ECL at {stress_multiplier:.1f}x",
    f"{total_stressed_ecl:,.0f} DM",
    delta=f"{pct_change:+.1f}% vs. base",
)
col2.metric("Base-case ECL (for reference)", f"{total_base_ecl:,.0f} DM")

fig1, ax1 = plt.subplots(figsize=(6, 4))
bars = ax1.bar(
    ["Base case", f"Stressed ({stress_multiplier:.1f}x)"],
    [total_base_ecl, total_stressed_ecl],
    color=["#2a78d6", "#e34948"],
)
ax1.set_ylabel("Total portfolio ECL (DM)")
ax1.set_title("Base vs. stressed total ECL")
for bar in bars:
    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
              f"{bar.get_height():,.0f}", ha="center", va="bottom")
st.pyplot(fig1)

st.divider()

# ---------------------------------------------------------------------------
# Static section: Indian NBFC benchmark context (from notebook 04)
# ---------------------------------------------------------------------------
st.header("Indian NBFC benchmark context")
st.caption(
    "Reproduced from notebooks/04_india_benchmark.ipynb, for context only — "
    "NOT a direct comparison. The South German Credit figures come from a "
    "1990s-era German research dataset with defaults deliberately "
    "oversampled for modeling purposes; the Indian figures are real, "
    "current industry numbers from a different country, era, and "
    "underwriting environment."
)

benchmark_table = pd.DataFrame([
    {"group": "This project", "metric": "South German Credit dataset — observed default rate",
     "value": "30.0%", "source": "UCI ML Repository / Grömping (2019) dataset documentation"},
    {"group": "This project", "metric": "Our PD model — base-case ECL rate",
     "value": "31.4% of portfolio EAD", "source": "This project, notebook 03"},
    {"group": "Indian NBFC sector", "metric": "NBFC sector-wide GNPA (Mar 2025)",
     "value": "~2.9%–4.2% (range across RBI publications)", "source": "RBI, Trend and Progress of Banking in India, 2025"},
    {"group": "Indian NBFC sector", "metric": "NBFC-MFI subsegment GNPA (Mar 2025)",
     "value": "~4.1%", "source": "RBI, Trend and Progress of Banking in India, 2025"},
    {"group": "Peer HFCs", "metric": "Bajaj Housing Finance GNPA (Dec 2025)",
     "value": "0.27%", "source": "Bajaj Housing Finance company disclosures"},
    {"group": "Peer HFCs", "metric": "PNB Housing Finance GNPA, FY22 vs. current",
     "value": "8.1% (FY22) improved to ~1.5% (current)", "source": "PNB Housing Finance company disclosures"},
    {"group": "Godrej Capital Group", "metric": "Credit rating",
     "value": "CRISIL AA+/Stable, ICRA AA+/Stable (2025)", "source": "CRISIL / ICRA rating rationale reports, 2025"},
    {"group": "Godrej Capital Group", "metric": "Numeric GNPA / NPA",
     "value": "Not publicly disclosed", "source": "CRISIL / ICRA rating rationale reports, 2025"},
])

st.dataframe(benchmark_table, hide_index=True, use_container_width=True)

COLOR_OUR_PROJECT = "#2a78d6"
COLOR_INDIAN_NBFC = "#1baf7a"
COLOR_PEER_HFC = "#eb6834"

bars_spec = [
    ("Bajaj Housing Finance GNPA (Dec 2025)", 0.27, 0.27, COLOR_PEER_HFC, None),
    ("PNB Housing Finance GNPA (current)", 1.5, 1.5, COLOR_PEER_HFC, None),
    ("PNB Housing Finance GNPA (FY22, pre-improvement)", 8.1, 8.1, COLOR_PEER_HFC, "//"),
    ("NBFC-MFI subsegment GNPA (Mar 2025)", 4.1, 4.1, COLOR_INDIAN_NBFC, None),
    ("Indian NBFC sector GNPA (Mar 2025, range)", 2.9, 4.2, COLOR_INDIAN_NBFC, None),
    ("South German Credit dataset default rate", 30.0, 30.0, COLOR_OUR_PROJECT, None),
    ("Our PD model base-case ECL rate", 31.4, 31.4, COLOR_OUR_PROJECT, None),
]

fig2, ax2 = plt.subplots(figsize=(9, 5.5))
y_pos = range(len(bars_spec))
for y, (label, low, high, color, hatch) in zip(y_pos, bars_spec):
    width = high - low
    if width == 0:
        ax2.barh(y, low, color=color, hatch=hatch, edgecolor="white")
        ax2.text(low + 0.5, y, f"{low:g}%", va="center", fontsize=9)
    else:
        ax2.barh(y, width, left=low, color=color, edgecolor="white")
        ax2.text(high + 0.5, y, f"{low:g}%–{high:g}%", va="center", fontsize=9)

ax2.set_yticks(list(y_pos))
ax2.set_yticklabels([b[0] for b in bars_spec])
ax2.invert_yaxis()
ax2.set_xlim(0, 36)
ax2.set_xlabel("Rate (%)")
ax2.set_title("Scale comparison — context only, not a direct equivalence")
legend_elements = [
    Patch(facecolor=COLOR_PEER_HFC, label="Peer HFCs (India)"),
    Patch(facecolor=COLOR_INDIAN_NBFC, label="Indian NBFC sector (RBI)"),
    Patch(facecolor=COLOR_OUR_PROJECT, label="This project (German dataset)"),
]
ax2.legend(handles=legend_elements, loc="upper right")
plt.tight_layout()
st.pyplot(fig2)

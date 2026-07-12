"""
ECL Portfolio Dashboard
========================

A Streamlit app that puts notebooks 03 and 04 in front of a live,
interactive, product-styled interface instead of a static notebook.

Layout:
- Sidebar (dark panel): project summary + key caveats.
- Tab "Overview": KPI cards + IFRS 9 stage composition donut.
- Tab "Stress Scenario": live slider that recomputes stressed ECL.
- Tab "India Benchmark": the Indian NBFC/HFC context from notebook 04.

Charts are built with Plotly (not matplotlib) for interactive hover
tooltips and a more polished look — see the design notes inline below
for the exact, version-verified Streamlit selectors used to hide default
UI chrome.

Run it with:
    streamlit run dashboard/app.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "ecl_results.csv"

st.set_page_config(page_title="ECL Portfolio Dashboard", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# Design system — fixed values, reused everywhere below so a color never
# gets typed twice with a slightly different hex by accident.
# ---------------------------------------------------------------------------
COLOR_PRIMARY = "#2A78D6"          # brand/neutral accent
COLOR_TEXT_PRIMARY = "#111827"
COLOR_TEXT_SECONDARY = "#6B7280"

# Semantic risk colors — reserved for the 3 IFRS 9 stages ONLY, used
# consistently across every card, chart, and badge that represents a stage.
STAGE_COLORS = {"Stage 1": "#16A34A", "Stage 2": "#D97706", "Stage 3": "#DC2626"}
STAGE_LABELS = {"Stage 1": "Stage 1 — Performing", "Stage 2": "Stage 2 — Watch", "Stage 3": "Stage 3 — Impaired"}

# Neutral grays for the India benchmark chart, which compares three groups
# that are NOT stage/risk signals — deliberately kept out of the green/
# amber/red family so that trio stays uniquely meaningful to IFRS 9 staging.
COLOR_GROUP_PROJECT = COLOR_PRIMARY  # "this project" bars
COLOR_GROUP_SECTOR = "#6B7280"       # Indian NBFC sector (RBI)
COLOR_GROUP_PEER = "#9CA3AF"         # Peer HFCs

FONT_STACK = "'Inter', -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"


def fmt_dm(x: float) -> str:
    return f"{x:,.0f} DM"


def fmt_pct(x: float, decimals: int = 1) -> str:
    return f"{x:.{decimals}f}%"


# ---------------------------------------------------------------------------
# Custom CSS.
#
# Every selector below was verified against the ACTUAL compiled frontend
# bundle of the installed Streamlit version (1.59.1) — not copied from an
# older tutorial — by grepping
# .../site-packages/streamlit/static/static/js/index.*.js for its literal
# data-testid strings. Two things this verification specifically caught:
#
#   1. There is no more standalone "Made with Streamlit" footer element in
#      this version — that text now lives INSIDE the hamburger menu's
#      dropdown panel. Hiding the hamburger button (stMainMenu) removes
#      access to it entirely, so no separate footer selector is needed.
#   2. The sidebar's "re-expand" arrow (stExpandSidebarButton, shown when
#      the sidebar is collapsed) lives INSIDE the same toolbar container
#      (stToolbar) as the Deploy button and hamburger menu. Hiding the
#      whole toolbar — as many older guides suggest — would silently break
#      the ability to reopen a collapsed sidebar. We hide stMainMenu and
#      stAppDeployButton individually instead, and never touch stToolbar,
#      stExpandSidebarButton, or stSidebarCollapseButton.
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [data-testid="stApp"], [data-testid="stMain"], [data-testid="stSidebar"] {{
        font-family: {FONT_STACK} !important;
    }}

    /* Main content background + width */
    [data-testid="stMain"] {{
        background-color: #F7F8FA;
    }}
    [data-testid="stMainBlockContainer"] {{
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }}

    /* Hide Deploy button + hamburger menu only — see note above for why
       we deliberately do NOT hide stToolbar as a whole. */
    [data-testid="stMainMenu"] {{ display: none !important; }}
    [data-testid="stAppDeployButton"] {{ display: none !important; }}

    /* ---- Sidebar: dark panel, every text role given an explicit light
       color rather than inheriting the light theme's dark text ---- */
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
        background-color: #0F1B2D;
    }}
    [data-testid="stSidebarContent"] h1,
    [data-testid="stSidebarContent"] h2,
    [data-testid="stSidebarContent"] h3,
    [data-testid="stSidebarContent"] h4 {{
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebarContent"] p,
    [data-testid="stSidebarContent"] li,
    [data-testid="stSidebarContent"] span,
    [data-testid="stSidebarContent"] strong,
    [data-testid="stSidebarContent"] em {{
        color: #E8ECF1 !important;
    }}
    [data-testid="stSidebarContent"] small {{
        color: #9FB0C3 !important;
    }}
    [data-testid="stSidebarContent"] hr {{
        border-color: rgba(255, 255, 255, 0.14) !important;
    }}
    /* The collapse-arrow icon (inside the sidebar) must stay visible
       against the new navy background — left fully functional, just
       recolored so it isn't dark-on-dark. */
    [data-testid="stSidebarCollapseButton"] svg {{
        fill: #E8ECF1 !important;
    }}

    /* ---- Header banner ---- */
    .dashboard-header {{
        padding-bottom: 1rem;
        margin-bottom: 1.25rem;
        border-bottom: 3px solid {COLOR_PRIMARY};
    }}
    .dashboard-header h1 {{
        font-size: 2.05rem;
        font-weight: 800;
        margin: 0 0 0.35rem 0;
        color: {COLOR_TEXT_PRIMARY};
    }}
    .dashboard-header p {{
        font-size: 1.05rem;
        color: {COLOR_TEXT_SECONDARY};
        margin: 0;
    }}

    /* ---- Meta row: data-as-of stamp + status badge ---- */
    .meta-row {{
        display: flex;
        align-items: center;
        gap: 0.9rem;
        flex-wrap: wrap;
        margin-bottom: 2rem;
    }}
    .data-stamp {{
        font-size: 0.85rem;
        color: {COLOR_TEXT_SECONDARY};
    }}
    .status-badge {{
        display: inline-block;
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FBBF24;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 0.3rem 0.75rem;
        border-radius: 999px;
    }}

    /* ---- KPI / stage cards ---- */
    .kpi-card {{
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-left: 4px solid {COLOR_PRIMARY};
        border-radius: 10px;
        padding: 1.25rem 1.25rem 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        margin-bottom: 0.5rem;
        height: 100%;
    }}
    .kpi-label {{
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: {COLOR_TEXT_SECONDARY};
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
    }}
    .kpi-value {{
        font-size: 2.1rem;
        font-weight: 700;
        color: {COLOR_TEXT_PRIMARY};
        font-variant-numeric: tabular-nums;
        line-height: 1.15;
    }}
    .kpi-sub {{
        font-size: 0.8rem;
        color: {COLOR_TEXT_SECONDARY};
        margin-top: 0.4rem;
    }}
    .kpi-delta {{
        font-size: 0.85rem;
        font-weight: 700;
        margin-top: 0.5rem;
    }}
    .stage-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }}

    /* ---- Section spacing ---- */
    h2, h3 {{ margin-top: 0.25rem !important; color: {COLOR_TEXT_PRIMARY}; }}
    .section-block {{ margin-bottom: 2rem; }}
    div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] {{
        margin-bottom: 0.25rem;
    }}

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab-list"] {{ gap: 1.75rem; margin-bottom: 1.5rem; }}
    .stTabs [data-baseweb="tab"] {{ font-weight: 600; }}

    /* ---- Footer ---- */
    .dashboard-footer {{
        margin-top: 2.5rem;
        padding-top: 1rem;
        border-top: 1px solid #E5E7EB;
        color: #9CA3AF;
        font-size: 0.82rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Shared Plotly layout — every chart in this dashboard calls this so they
# share one visual system (same font, same gridline treatment, same
# background) instead of looking like output from different tools.
# ---------------------------------------------------------------------------
def apply_chart_style(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        font=dict(family=FONT_STACK, size=12, color=COLOR_TEXT_PRIMARY),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(t=50, b=40, l=60, r=30),
        height=height,
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


df = load_data()


# ---------------------------------------------------------------------------
# ECL logic — re-implemented here so the dashboard doesn't depend on
# re-running any notebook. Mirrors notebook 03's (corrected) staging and
# ECL formulas exactly:
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


def kpi_card_html(label: str, value: str, accent: str = COLOR_PRIMARY, sub: str | None = None, dot: bool = False) -> str:
    dot_html = f'<span class="stage-dot" style="background:{accent};"></span>' if dot else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card" style="border-left-color:{accent};">
        <div class="kpi-label">{dot_html}{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """


# ---------------------------------------------------------------------------
# Sidebar — dark panel with project summary + caveats.
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ECL Credit Risk Model")
    st.write(
        "An interactive view of a full PD → LGD/EAD → IFRS 9 staging → ECL "
        "pipeline, built on the South German Credit dataset and benchmarked "
        "against Indian NBFC industry context."
    )

    st.markdown("### Key caveats")
    st.markdown(
        "- LGD and EAD are **illustrative assumptions**, not fitted from "
        "real recovery/amortization data\n"
        "- IFRS 9 staging is a **simplified PD-threshold proxy**, not a "
        "genuine origination-vs-current comparison\n"
        "- Indian NBFC figures are shown for **context only** — not a "
        "direct equivalence to this dataset's numbers"
    )

    st.markdown("### Data & code")
    st.caption(
        "Reproduces `notebooks/01-04`. Full methodology, formulas, and "
        "citations are documented there."
    )

# ---------------------------------------------------------------------------
# Header banner + meta row (data-as-of stamp + status badge)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="dashboard-header">
        <h1>Expected Credit Loss (ECL) Portfolio Dashboard</h1>
        <p>PD &times; LGD &times; EAD, IFRS&nbsp;9 staged, and stress-tested — benchmarked against Indian NBFC industry context.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="meta-row">
        <span class="data-stamp">Data as of: South German Credit dataset, {len(df):,} applicants</span>
        <span class="status-badge">Illustrative model — see limitations</span>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_overview, tab_stress, tab_india = st.tabs(["Overview", "Stress Scenario", "India Benchmark"])

# ---------------------------------------------------------------------------
# Tab 1: Overview
# ---------------------------------------------------------------------------
with tab_overview:
    st.write(
        "This dashboard summarizes the Probability of Default (PD), Loss "
        "Given Default (LGD), Exposure at Default (EAD), and resulting "
        "Expected Credit Loss (ECL) for a 1,000-applicant portfolio, with "
        "IFRS 9 staging applied — full methodology and caveats are "
        "documented in `notebooks/02_pd_model.ipynb` and "
        "`notebooks/03_ecl_calculation.ipynb`."
    )

    total_base_ecl = df["ecl"].sum()
    total_ead = df["EAD"].sum()
    ecl_pct = total_base_ecl / total_ead * 100

    kpi1, kpi2, kpi3, kpi4 = st.columns(4, gap="large")
    kpi1.markdown(kpi_card_html("Total base-case ECL", fmt_dm(total_base_ecl)), unsafe_allow_html=True)
    kpi2.markdown(kpi_card_html("Total EAD", fmt_dm(total_ead)), unsafe_allow_html=True)
    kpi3.markdown(kpi_card_html("ECL % of portfolio", fmt_pct(ecl_pct)), unsafe_allow_html=True)
    kpi4.markdown(kpi_card_html("Total applicants", f"{len(df):,}"), unsafe_allow_html=True)

    st.caption("DM = Deutsche Mark, the South German Credit dataset's original currency.")

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    st.subheader("Portfolio composition by IFRS 9 stage")
    st.write(
        "Stage distribution is normally the first thing a risk committee "
        "looks at — it shows how much of the portfolio is performing "
        "(Stage 1), showing elevated risk (Stage 2), or already "
        "credit-impaired (Stage 3), weighted by loan amount."
    )

    stage_amounts = df.groupby("stage")["EAD"].sum().reindex(["Stage 1", "Stage 2", "Stage 3"]).fillna(0)
    stage_counts = df["stage"].value_counts().reindex(["Stage 1", "Stage 2", "Stage 3"]).fillna(0).astype(int)
    stage_pct = stage_amounts / stage_amounts.sum() * 100

    col_donut, col_cards = st.columns([3, 2], gap="large")

    with col_donut:
        fig_donut = go.Figure(data=[go.Pie(
            labels=[STAGE_LABELS[s] for s in stage_amounts.index],
            values=stage_amounts.values,
            hole=0.62,
            sort=False,
            marker=dict(colors=[STAGE_COLORS[s] for s in stage_amounts.index], line=dict(color="#FFFFFF", width=2)),
            textinfo="percent",
            textfont=dict(size=13, color="#FFFFFF", family=FONT_STACK),
            hovertemplate="%{label}<br>%{value:,.0f} DM (%{percent})<extra></extra>",
        )])
        fig_donut.update_layout(
            font=dict(family=FONT_STACK, size=12, color=COLOR_TEXT_PRIMARY),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            margin=dict(t=20, b=20, l=20, r=20),
            height=360,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
            annotations=[dict(
                text=f"{len(df):,}<br>applicants",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=15, family=FONT_STACK, color=COLOR_TEXT_PRIMARY),
            )],
        )
        st.plotly_chart(fig_donut, width="stretch", theme=None)

    with col_cards:
        for stage in ["Stage 1", "Stage 2", "Stage 3"]:
            st.markdown(
                kpi_card_html(
                    STAGE_LABELS[stage],
                    f"{stage_counts[stage]:,}",
                    accent=STAGE_COLORS[stage],
                    sub=f"{fmt_pct(stage_pct[stage])} of portfolio EAD",
                    dot=True,
                ),
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tab 2: Interactive stress scenario
# ---------------------------------------------------------------------------
with tab_stress:
    st.write(
        "Move the slider to see how total portfolio ECL responds to a "
        "stress shock applied to every applicant's PD (capped at 100%). "
        "This is the same mechanism as notebook 03's scenario analysis, "
        "just made interactive — an illustrative shock, not a calibrated "
        "macroeconomic scenario."
    )

    stress_multiplier = st.slider(
        "Stress multiplier (applied to every applicant's PD)",
        min_value=0.5, max_value=3.0, value=1.5, step=0.1,
    )

    total_base_ecl = df["ecl"].sum()
    df["pd_stressed_live"] = (df["pd_estimate"] * stress_multiplier).clip(upper=1.0)
    _, ecl_stressed_live = compute_staged_ecl(df, "pd_stressed_live")
    total_stressed_ecl = ecl_stressed_live.sum()
    pct_change = (total_stressed_ecl - total_base_ecl) / total_base_ecl * 100

    col1, col2 = st.columns(2, gap="large")
    delta_arrow = "▲" if pct_change >= 0 else "▼"
    delta_color = STAGE_COLORS["Stage 3"] if pct_change >= 0 else STAGE_COLORS["Stage 1"]
    delta_html = f'<div class="kpi-delta" style="color:{delta_color};">{delta_arrow} {abs(pct_change):.1f}% vs. base</div>'
    col1.markdown(
        f"""
        <div class="kpi-card" style="border-left-color:{STAGE_COLORS['Stage 3']};">
            <div class="kpi-label">Stressed ECL at {stress_multiplier:.1f}x</div>
            <div class="kpi-value">{fmt_dm(total_stressed_ecl)}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    col2.markdown(kpi_card_html("Base-case ECL (for reference)", fmt_dm(total_base_ecl)), unsafe_allow_html=True)

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    y_max = max(total_base_ecl, total_stressed_ecl) * 1.18
    fig_stress = go.Figure(data=[go.Bar(
        x=["Base case", f"Stressed ({stress_multiplier:.1f}x)"],
        y=[total_base_ecl, total_stressed_ecl],
        marker_color=[COLOR_PRIMARY, STAGE_COLORS["Stage 3"]],
        text=[fmt_dm(total_base_ecl), fmt_dm(total_stressed_ecl)],
        textposition="outside",
        textfont=dict(size=13, family=FONT_STACK),
        hovertemplate="%{x}<br>%{y:,.0f} DM<extra></extra>",
        width=0.5,
    )])
    fig_stress.update_layout(
        title=dict(text="Base vs. stressed total ECL", font=dict(size=16, family=FONT_STACK, color=COLOR_TEXT_PRIMARY)),
        yaxis=dict(
            title="Total portfolio ECL (DM)",
            showgrid=True, gridcolor="#E5E7EB", zeroline=False,
            tickformat=",.0f", range=[0, y_max],
        ),
        xaxis=dict(showgrid=False),
    )
    apply_chart_style(fig_stress, height=440)
    st.plotly_chart(fig_stress, width="stretch", theme=None)

# ---------------------------------------------------------------------------
# Tab 3: Indian NBFC benchmark context (from notebook 04)
# ---------------------------------------------------------------------------
with tab_india:
    st.caption(
        "Reproduced from notebooks/04_india_benchmark.ipynb, for context "
        "only — NOT a direct comparison. The South German Credit figures "
        "come from a 1990s-era German research dataset with defaults "
        "deliberately oversampled for modeling purposes; the Indian "
        "figures are real, current industry numbers from a different "
        "country, era, and underwriting environment."
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

    st.dataframe(benchmark_table, hide_index=True, width="stretch")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Grouped so color encodes "which category this bar belongs to" once
    # per group (fixed order), not per individual bar.
    groups = {
        "Peer HFCs (India)": {
            "color": COLOR_GROUP_PEER,
            "bars": [
                ("Bajaj Housing Finance GNPA (Dec 2025)", 0.27, 0.27, ""),
                ("PNB Housing Finance GNPA (current)", 1.5, 1.5, ""),
                ("PNB Housing Finance GNPA (FY22, pre-improvement)", 8.1, 8.1, "/"),
            ],
        },
        "Indian NBFC sector (RBI)": {
            "color": COLOR_GROUP_SECTOR,
            "bars": [
                ("NBFC-MFI subsegment GNPA (Mar 2025)", 4.1, 4.1, ""),
                ("Indian NBFC sector GNPA (Mar 2025, range)", 2.9, 4.2, ""),
            ],
        },
        "This project (German dataset)": {
            "color": COLOR_GROUP_PROJECT,
            "bars": [
                ("South German Credit dataset default rate", 30.0, 30.0, ""),
                ("Our PD model base-case ECL rate", 31.4, 31.4, ""),
            ],
        },
    }

    category_order = [label for spec in groups.values() for label, *_ in spec["bars"]]

    fig_bench = go.Figure()
    for group_name, spec in groups.items():
        labels = [b[0] for b in spec["bars"]]
        lows = [b[1] for b in spec["bars"]]
        highs = [b[2] for b in spec["bars"]]
        widths = [h - l for l, h in zip(lows, highs)]
        patterns = [(b[3] or "") for b in spec["bars"]]
        bar_text = [f"{l:g}%" if l == h else f"{l:g}%–{h:g}%" for l, h in zip(lows, highs)]

        fig_bench.add_trace(go.Bar(
            y=labels, x=widths, base=lows, orientation="h",
            name=group_name,
            marker=dict(
                color=spec["color"],
                pattern=dict(shape=patterns, fgcolor="#FFFFFF", size=6),
            ),
            text=bar_text,
            textposition="outside",
            textfont=dict(size=11, family=FONT_STACK),
            hovertemplate="%{y}<br>%{text}<extra>" + group_name + "</extra>",
        ))

    fig_bench.update_layout(
        yaxis=dict(
            categoryorder="array", categoryarray=category_order[::-1],
            showgrid=True, gridcolor="#E5E7EB",
        ),
        xaxis=dict(title="Rate (%)", showgrid=False, range=[0, 36], tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=60, b=40, l=320, r=60),
    )
    apply_chart_style(fig_bench, height=460)
    fig_bench.update_layout(showlegend=True, title=dict(
        text="Scale comparison — context only, not a direct equivalence",
        font=dict(size=16, family=FONT_STACK, color=COLOR_TEXT_PRIMARY),
    ))
    st.plotly_chart(fig_bench, width="stretch", theme=None)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="dashboard-footer">
    Sources: UCI/Grömping (2019), RBI Trend and Progress of Banking in India (2025),
    CRISIL/ICRA rating rationale reports (2025), company disclosures — see
    <code>notebooks/</code> for full citations.
    </div>
    """,
    unsafe_allow_html=True,
)

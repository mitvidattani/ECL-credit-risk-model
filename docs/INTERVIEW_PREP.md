# Interview Prep Cheat-Sheet — ECL Credit Risk Model

*Last-minute review only. For full detail see the notebooks and README.*

## 1. The 30-second pitch

I built an end-to-end credit risk pipeline — data cleaning, a Probability
of Default model, and a full IFRS 9 Expected Credit Loss calculation with
stress testing — on the corrected South German Credit dataset, then
benchmarked the output against real Indian NBFC industry data and built a
live interactive dashboard, specifically to demonstrate the kind of
analytics work relevant to an NBFC role at Godrej Capital. The single
most impressive outcome: the PD model's screening decisions cut expected
business cost by **55.8%** versus approving every applicant, using the
real Statlog cost matrix — and the whole pipeline, including a
methodology bug I caught and fixed myself (Stage 3 PD treatment), is
fully reproducible end-to-end with zero notebook errors.

## 2. The 2-minute walkthrough

1. **Problem statement**: banks need to estimate Expected Credit Loss
   (ECL = PD × LGD × EAD) to size loan-loss provisions under IFRS 9 — I
   wanted to demonstrate that full pipeline, not just a PD classifier.
2. **Dataset choice**: I used the Grömping (2019) **corrected** South
   German Credit dataset, not the original flawed UCI version — the
   original had a known miscoding in `credit_history` that made "paid
   back duly" look riskier than it should. I also specifically avoided
   the common Kaggle upload of this dataset, which doesn't even have a
   usable target column.
3. **PD model**: trained Logistic Regression (`class_weight='balanced'`)
   against XGBoost on 1,000 applicants, evaluated with ROC-AUC, confusion
   matrices, and — critically — the real Statlog/UCI business cost matrix
   (misclassifying a bad credit as good costs 5 units, rejecting a good
   applicant costs 1 unit), not just accuracy.
4. **LGD/EAD**: since this dataset has no real recovery or amortization
   data, I built LGD from a collateral/savings score (30%-75% range) and
   used original loan amount as EAD — both explicitly labeled as
   illustrative assumptions, not fitted values, everywhere they appear.
5. **IFRS 9 staging**: applied a simplified 3-stage rule — known
   historical defaults are Stage 3, high predicted PD is Stage 2,
   everything else is Stage 1 — since this single-snapshot dataset can't
   support genuine origination-vs-current PD comparison.
6. **ECL calculation**: Stage 1 gets a prorated 12-month ECL, Stage 2/3
   get lifetime ECL — and Stage 3 specifically uses PD = 100%, since
   those are *known* defaults, not model predictions.
7. **Stress scenario**: multiplied every applicant's PD by 1.5x (capped
   at 100%) as an illustrative shock and recomputed staging and ECL from
   scratch, including which applicants migrate between stages.
8. **India/Godrej benchmarking**: put the model's output next to real RBI
   NBFC sector data, peer housing finance companies, and Godrej Capital
   Group's own disclosed rating profile — explicit that the scales aren't
   comparable, and why.
9. **Dashboard**: a Streamlit app with live KPI cards, an IFRS 9 stage
   donut, an interactive stress-multiplier slider, and the India
   benchmark view — a delivered product, not just static notebooks.

## 3. Numbers to have cold

| Metric | Value |
|---|---|
| PD model ROC-AUC (Logistic Regression) | **0.80** (vs. 0.76 for XGBoost) |
| Business cost reduction vs. "approve everyone" baseline | **55.8%** (450 → 199 cost units) |
| Base-case total portfolio ECL | **1,028,795 DM** — **31.4%** of portfolio EAD |
| Stressed-case total ECL (1.5x PD shock) | **1,239,301 DM** — **+20.5%** vs. base |
| Stage 3 share of total ECL vs. share of loan amount | **63.2%** of ECL vs. only **36.1%** of loan amount |
| Indian NBFC sector GNPA (RBI, Mar 2025) | **~2.9%–4.2%** (range across RBI publications) |
| Peer HFC GNPA | Bajaj Housing Finance **0.27%**; PNB Housing Finance **~1.5%** (current) |
| Godrej Capital Group credit rating | **CRISIL AA+/Stable, ICRA AA+/Stable** (2025) |

## 4. "Tell me about a challenge" — STAR stories

**a) The Stage 3 methodology bug**
*Situation*: my first ECL calculation applied the PD model's predicted
probability uniformly across all three IFRS 9 stages, including Stage 3.
*Task*: on review, I recognized Stage 3 loans are defined as *known
historical defaults* (`credit_risk == 0`) — the default has already
happened, so treating their loss probability as anything less than
certain understates the loss whenever the model happened to score a
known defaulter as lower-risk. *Action*: I corrected the formula so
Stage 3 uses PD = 100% (ECL = LGD × EAD directly), re-ran the full
notebook, and re-verified every downstream number. *Result*: total
portfolio ECL rose from 831,484 DM to **1,028,795 DM** — a real,
material correction. This demonstrates methodological rigor: catching a
conceptual mismatch between what a number *means* and how it was being
calculated, not just fixing a crash.

**b) The Plotly chart crash**
*Situation*: the India benchmark chart in my dashboard was crashing on
every load. *Task*: rather than guess-and-check, I traced it to the
exact root cause — Plotly's `marker.pattern.shape` property only accepts
a fixed enum of values (`''`, `/`, `\`, `x`, etc.), and `''` (empty
string) means "no pattern" — but my code was passing `None` as that
sentinel, which isn't a valid enum value. *Action*: replaced every `None`
with `""` and added a defensive `(value or "")` coercion so it can't
silently recur. *Result*: the chart rendered correctly, verified via a
clean server log and a standalone reproduction of the exact failing
code path. This demonstrates systematic debugging: reading the actual
library contract instead of trial-and-error patching.

**c) The silent HTML-as-code-block bug**
*Situation*: a custom-styled benchmark table rendered as a Streamlit code
block (with a copy-to-clipboard button) instead of an actual HTML table
— with zero server-side errors or exceptions anywhere. *Task*: find the
cause despite there being no stack trace to follow. *Action*: I inspected
the exact string being passed to `st.markdown()` and traced it to
CommonMark's rule that any line indented 4+ spaces is parsed as an
indented code block — a rule that takes precedence over HTML-block
recognition. My HTML string was indented to match the surrounding Python
code for readability, which was silently enough to trip that rule.
*Result*: stripped per-line indentation before returning the string, and
confirmed the fix at the string level since the bug produced no server
error to grep for. This demonstrates attention to detail: verifying
actual output, not just the absence of errors — a "no crash" result
doesn't mean "correct."

## 5. Hard questions I should expect

**"Why is your ECL rate 31% when real Indian NBFCs run under 5% GNPA?"**
Because the South German Credit dataset deliberately oversamples bad
credit for research purposes (30% defaults, per the dataset's own
documentation) — it's a research sample built for modeling convenience,
not a real bank's book. Real Indian lenders benefit from credit bureau
checks, collateral, and decades of underwriting refinement that this
1990s research dataset simply doesn't reflect.

**"Why did Logistic Regression beat XGBoost?"**
With only 1,000 rows and mostly monotonic relationships between features
and default risk — which I confirmed in the EDA — a tree ensemble has
less room to safely learn complex interactions without overfitting. On a
small, clean dataset like this, a well-specified linear model can
legitimately outperform a more flexible model.

**"What's the single biggest limitation of this project?"**
LGD and EAD are illustrative assumptions, not fitted values — this
dataset has no real recovery or amortization data, so I built LGD from a
collateral/savings score and used original loan amount as EAD. Everything
downstream (ECL, staging, stress results) inherits that assumption, which
is why I labeled it prominently rather than let it look empirically
derived.

**"If you had 3 more months and real data, what would you do
differently?"**
I'd fit LGD from actual historical recovery/workout data segmented by
collateral type, compute EAD from real amortization schedules instead of
original loan amount, replace the PD-threshold staging proxy with genuine
origination-vs-current PD tracking, and calibrate the stress scenario
against an actual macroeconomic model instead of a flat 1.5x multiplier.

**"Why does Godrej Capital specifically matter to this project?"**
CRISIL and ICRA's own 2025 rating rationale for Godrej Capital Group
notes the business has "reported comfortable asset quality since
inception, yet to be tested through economic cycles, given the limited
seasoning in relation to the loan tenure." A young, unseasoned lender
without years of its own loss history is exactly the situation where a
reproducible, scenario-based ECL framework — built before that history
exists — adds real value, rather than after a downturn has already
happened.

## 6. One closing line

Godrej Capital's own rating agencies say its book is strong today but
untested through a full cycle — this project is a working demonstration
that I can build the scenario-based risk infrastructure a young lender
needs *before* that test arrives, not after.

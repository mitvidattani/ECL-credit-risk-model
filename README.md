# ECL Credit Risk Model

A credit risk / Expected Credit Loss (ECL) modeling project built on the
**South German Credit dataset** (Grömping 2019 corrected version of the
classic UCI "German Credit" data), benchmarked against real Indian NBFC
industry context — built for a job application to **Godrej Capital**.

## Project goal

Build a full credit risk pipeline — data cleaning, EDA, a Probability of
Default (PD) model, and an Expected Credit Loss (ECL) calculation
(ECL = PD × LGD × EAD) with IFRS 9 staging and scenario stress-testing —
the kind of framework used under accounting standards like IFRS 9 / CECL
to size loan-loss provisions. Since this is a Western research dataset
but the target role is at an Indian NBFC, the project closes with a
notebook that puts the model's output in real Indian industry context and
is explicit about what does and doesn't transfer.

## Dataset

- **Source**: South German Credit dataset, Grömping (2019) corrected
  version of the original UCI German Credit dataset.
- **Rows**: 1,000 loan applicants.
- **Columns**: 21 (20 features + 1 target), originally coded with German
  variable names and numeric-coded categories.
- **Target**: `credit_risk` — `1` = good credit (loan repaid as agreed),
  `0` = bad credit (defaulted). The dataset is imbalanced: 700 good / 300
  bad — deliberately oversampled for research purposes, not representative
  of any real bank's book (see notebook 04 for why this matters).

## Project structure

```
ecl-credit-risk-model/
├── data/
│   ├── raw/                     # original, untouched data
│   │   └── german_credit_data.csv
│   └── processed/                # cleaned data + model outputs
│       ├── credit_clean.csv
│       └── ecl_results.csv       # full portfolio: PD, LGD, EAD, stage, ECL
├── models/
│   └── pd_model.pkl              # trained PD model (joblib)
├── notebooks/
│   ├── 01_eda.ipynb               # exploratory data analysis
│   ├── 02_pd_model.ipynb          # Probability of Default model
│   ├── 03_ecl_calculation.ipynb   # LGD, EAD, IFRS 9 staging, ECL, stress test
│   └── 04_india_benchmark.ipynb   # Indian NBFC/HFC industry context
├── dashboard/
│   └── app.py                    # interactive Streamlit ECL dashboard
├── src/
│   └── data_prep.py              # loads, cleans, renames columns, saves processed data
├── reports/
│   └── figures/                  # saved plots/exhibits
├── README.md
└── requirements.txt
```

## How to reproduce

```bash
pip install -r requirements.txt
python src/data_prep.py              # builds data/processed/credit_clean.csv
jupyter notebook notebooks/          # run 01 -> 02 -> 03 -> 04 in order
```

## How to run the dashboard

```bash
streamlit run dashboard/app.py
```

Opens an interactive view of the ECL results — KPI cards, IFRS 9 stage
composition, a live stress-scenario slider, and the India benchmark
comparison. Reads `data/processed/ecl_results.csv`, so run notebooks
01-03 first if that file doesn't exist yet.

## Status

- [x] Project scaffolding
- [x] Data cleaning / column renaming (`src/data_prep.py`)
- [x] Exploratory data analysis (`notebooks/01_eda.ipynb`)
- [x] Probability-of-default modeling (`notebooks/02_pd_model.ipynb`)
- [x] ECL calculation: LGD, EAD, IFRS 9 staging, stress scenario (`notebooks/03_ecl_calculation.ipynb`)
- [x] Indian NBFC industry benchmarking (`notebooks/04_india_benchmark.ipynb`)
- [x] Interactive dashboard (`dashboard/app.py`)

## Key findings

- **Indian NBFC context**: our model's base-case ECL rate (31.4% of
  portfolio EAD) sits far above real Indian NBFC sector GNPA (~2.9%-4.2%,
  RBI) and peer HFC GNPA (0.27%-1.5%) — expected, since this dataset's
  defaults are deliberately oversampled for research, not representative
  of a real loan book. Godrej Capital Group's own book is young/unseasoned
  per CRISIL/ICRA (2025) — no numeric GNPA disclosed yet — which is
  exactly the kind of situation this project's stress-testing methodology
  is built for (see `notebooks/04_india_benchmark.ipynb`).

## Key caveats (see notebooks for full detail)

- LGD and EAD in this project are **illustrative assumptions**, not
  fitted from real recovery/amortization data (this dataset doesn't
  contain either).
- IFRS 9 staging here is a **simplified PD-threshold proxy**, not a
  genuine origination-vs-current risk comparison.
- The dataset's 30% default rate and the model's 31.4% ECL rate are
  **not comparable** to real Indian lending benchmarks (sub-1% to
  low-single-digit GNPA) — see `notebooks/04_india_benchmark.ipynb` for
  why, and for what the modeling *methodology* still offers a young,
  not-yet-cycle-tested lender.

# ECL Credit Risk Model

A credit risk / Expected Credit Loss (ECL) modeling project built on the
**South German Credit dataset** (Grömping 2019 corrected version of the
classic UCI "German Credit" data).

## Project goal

Build a credit risk model that predicts the probability that a borrower
defaults ("bad" credit), as a step toward estimating **Expected Credit
Loss (ECL)** — the kind of model used under accounting standards like
IFRS 9 / CECL to size loan-loss provisions. This repo currently covers
**data preparation and exploratory data analysis (EDA)**. Modeling
(probability-of-default, ECL components, etc.) is a later step.

## Dataset

- **Source**: South German Credit dataset, Grömping (2019) corrected
  version of the original UCI German Credit dataset.
- **Rows**: 1,000 loan applicants.
- **Columns**: 21 (20 features + 1 target), originally coded with German
  variable names and numeric-coded categories.
- **Target**: `credit_risk` — `1` = good credit (loan repaid as agreed),
  `0` = bad credit (defaulted). The dataset is imbalanced: 700 good / 300
  bad.

## Project structure

```
ecl-credit-risk-model/
├── data/
│   ├── raw/                  # original, untouched data
│   │   └── german_credit_data.csv
│   └── processed/            # cleaned data ready for analysis/modeling
│       └── credit_clean.csv
├── notebooks/
│   └── 01_eda.ipynb          # exploratory data analysis
├── src/
│   └── data_prep.py          # loads, cleans, renames columns, saves processed data
├── reports/
│   └── figures/              # saved plots/exhibits
├── README.md
└── requirements.txt
```

## How to reproduce

```bash
pip install -r requirements.txt
python src/data_prep.py        # builds data/processed/credit_clean.csv
jupyter notebook notebooks/01_eda.ipynb
```

## Status

- [x] Project scaffolding
- [x] Data cleaning / column renaming (`src/data_prep.py`)
- [x] Exploratory data analysis (`notebooks/01_eda.ipynb`)
- [ ] Feature engineering
- [ ] Probability-of-default modeling
- [ ] ECL calculation (PD × LGD × EAD)

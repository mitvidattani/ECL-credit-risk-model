"""
data_prep.py
============

This script is the FIRST step of the credit risk / ECL modeling pipeline.
All it does is:

    1. Load the raw South German Credit dataset (German column names,
       numeric-coded categories).
    2. Rename the 21 German columns to clear English names.
    3. Check the data is actually clean (no missing values, no duplicate
       rows) and print what it finds.
    4. Save the renamed, checked data to data/processed/credit_clean.csv.
    5. Print a summary: shape, target class balance, and a data
       dictionary.

No modeling happens here — this is purely "get the data into a trustworthy,
readable shape" (a step data scientists usually call "data prep" or
"data cleaning").

Run it from the project root with:

    python src/data_prep.py
"""

# pandas is the standard Python library for working with tabular data
# (think: a programmable spreadsheet). We conventionally import it as `pd`.
import pandas as pd

# pathlib.Path gives us an OS-independent way to build file paths (so this
# script works the same on Windows, Mac, or Linux) instead of hand-writing
# strings like "data/raw/german_credit_data.csv".
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. File locations
# ---------------------------------------------------------------------------
# __file__ is "this script's own path". .resolve() turns it into a full,
# absolute path. .parent walks up one directory level. Since this file lives
# in `src/`, going up one level (.parent) from `src/data_prep.py` lands us
# at the project root `ecl-credit-risk-model/`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_PATH = PROJECT_ROOT / "data" / "raw" / "german_credit_data.csv"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "credit_clean.csv"


# ---------------------------------------------------------------------------
# 2. Column rename mapping: German column name -> English column name
# ---------------------------------------------------------------------------
# This is a Python dictionary: {"old_name": "new_name", ...}.
# The German names come straight from the original South German Credit
# dataset codebook (Grömping 2019). We map each one to a clear English name
# so the rest of the project (and anyone reading it) doesn't need to know
# German banking terminology.
COLUMN_MAP = {
    "laufkont": "status",                   # checking account status
    "laufzeit": "duration",                 # loan duration, in months
    "moral": "credit_history",              # credit history
    "verw": "purpose",                      # purpose of the loan
    "hoehe": "amount",                      # credit amount, in Deutsche Mark (DM)
    "sparkont": "savings",                  # savings account/bonds status
    "beszeit": "employment_duration",       # length of current employment
    "rate": "installment_rate",             # installment rate (% of disposable income)
    "famges": "personal_status_sex",        # personal status combined with sex
    "buerge": "other_debtors",              # other debtors / guarantors
    "wohnzeit": "present_residence",        # years at present residence
    "verm": "property",                     # property/assets owned
    "alter": "age",                         # age, in years
    "weitkred": "other_installment_plans",  # other installment plans (e.g. at other banks/stores)
    "wohn": "housing",                      # housing situation (rent/own/free)
    "bishkred": "number_credits",           # number of existing credits at this bank
    "beruf": "job",                         # job / employment type
    "pers": "people_liable",                # number of people financially dependent on applicant
    "telef": "telephone",                   # whether applicant has a registered telephone
    "gastarb": "foreign_worker",            # whether applicant is a foreign worker
    "kredit": "credit_risk",                # TARGET: 1 = good credit, 0 = bad credit
}

# A short, human-readable description for each ENGLISH column name. We reuse
# this later to print a "data dictionary" -- a simple reference table that
# says what every column means. This is standard practice in any real data
# project: assume the next person (including future-you) has no idea what
# `laufkont` or `status` means without it.
COLUMN_DESCRIPTIONS = {
    "status": "Status of existing checking account (numeric-coded category)",
    "duration": "Duration of the credit in months",
    "credit_history": "Credit history (numeric-coded category)",
    "purpose": "Purpose of the credit (numeric-coded category)",
    "amount": "Credit amount, in Deutsche Mark (DM)",
    "savings": "Savings account/bonds status (numeric-coded category)",
    "employment_duration": "Present employment duration (numeric-coded category)",
    "installment_rate": "Installment rate, in % of disposable income (numeric-coded category)",
    "personal_status_sex": "Personal status combined with sex (numeric-coded category)",
    "other_debtors": "Other debtors / guarantors (numeric-coded category)",
    "present_residence": "Years at present residence (numeric-coded category)",
    "property": "Property/assets owned (numeric-coded category)",
    "age": "Age of applicant, in years",
    "other_installment_plans": "Other installment plans, e.g. other banks/stores (numeric-coded category)",
    "housing": "Housing situation: rent / own / for free (numeric-coded category)",
    "number_credits": "Number of existing credits at this bank",
    "job": "Job / employment type (numeric-coded category)",
    "people_liable": "Number of people financially dependent on the applicant",
    "telephone": "Whether applicant has a registered telephone (numeric-coded category)",
    "foreign_worker": "Whether applicant is classified as a foreign worker (numeric-coded category)",
    "credit_risk": "TARGET: 1 = good credit (repaid as agreed), 0 = bad credit (defaulted)",
}


def load_raw_data(path: Path) -> pd.DataFrame:
    """Load the raw CSV into a pandas DataFrame.

    A DataFrame is pandas' core object: think of it as an in-memory
    spreadsheet with rows and named columns.
    """
    # pd.read_csv() reads a CSV file straight into a DataFrame.
    df = pd.read_csv(path)
    print(f"Loaded raw data from: {path}")
    print(f"  Raw shape: {df.shape[0]} rows x {df.shape[1]} columns\n")
    return df


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename the German columns to English using COLUMN_MAP.

    .rename(columns=...) takes a dictionary and swaps any column name that
    matches a key for its corresponding value. Columns not mentioned in the
    dictionary are left unchanged (none should be left over here, since
    COLUMN_MAP covers all 21 original columns).
    """
    df = df.rename(columns=COLUMN_MAP)

    # Sanity check: make sure every column we expected to rename actually
    # exists in the renamed DataFrame. This protects us from silently
    # mismatched column names if the source CSV ever changes.
    missing = set(COLUMN_MAP.values()) - set(df.columns)
    if missing:
        raise ValueError(f"Expected columns missing after rename: {missing}")

    print("Renamed columns from German -> English:")
    print(f"  {list(df.columns)}\n")
    return df


def check_data_quality(df: pd.DataFrame) -> None:
    """Check for missing values and duplicate rows, and print what we find.

    We're told this dataset *should* be clean, but in real projects you
    never just trust that -- you verify. This function doesn't change the
    data, it only inspects and reports.
    """
    # --- Missing values ---
    # df.isnull() returns a same-shaped DataFrame of True/False (True where
    # a value is missing). .sum() adds those up per column, giving a count
    # of missing values per column.
    null_counts = df.isnull().sum()
    total_nulls = null_counts.sum()

    print("Null value check:")
    if total_nulls == 0:
        print("  No missing values found in any column. Good.\n")
    else:
        # Only show columns that actually have at least one null.
        print("  Missing values found:")
        print(null_counts[null_counts > 0].to_string())
        print()

    # --- Duplicate rows ---
    # df.duplicated() flags rows that are exact copies of an earlier row.
    # .sum() counts how many rows are flagged as duplicates.
    n_duplicates = df.duplicated().sum()

    print("Duplicate row check:")
    if n_duplicates == 0:
        print("  No duplicate rows found.\n")
    else:
        print(f"  Found {n_duplicates} duplicate rows. These will be kept as-is "
              f"unless you decide to drop them -- with only numeric-coded "
              f"categorical columns, identical rows can legitimately "
              f"represent different, unrelated applicants.\n")


def save_processed_data(df: pd.DataFrame, path: Path) -> None:
    """Save the cleaned DataFrame to data/processed/credit_clean.csv.

    index=False tells pandas not to write out its internal row-number index
    as an extra column -- we only want the real data columns in the CSV.
    """
    # Make sure the destination folder exists before writing to it.
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Saved cleaned data to: {path}\n")


def print_summary(df: pd.DataFrame) -> None:
    """Print a final summary: shape, target balance, and data dictionary."""

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # --- Shape ---
    print(f"\nFinal shape: {df.shape[0]} rows x {df.shape[1]} columns")

    # --- Target distribution ---
    # .value_counts() counts how many times each unique value appears in a
    # column. normalize=True converts those counts into proportions (0-1)
    # instead of raw counts, which we then multiply by 100 for a percentage.
    target_counts = df["credit_risk"].value_counts()
    target_pct = df["credit_risk"].value_counts(normalize=True) * 100

    print("\nTarget distribution (credit_risk: 1 = good, 0 = bad):")
    for label, name in [(1, "Good credit"), (0, "Bad credit")]:
        count = target_counts.get(label, 0)
        pct = target_pct.get(label, 0)
        print(f"  {name} ({label}): {count} rows ({pct:.1f}%)")

    # --- Data dictionary ---
    # Build a small DataFrame purely for nicely printing column name,
    # dtype (data type pandas inferred, e.g. int64), and our description.
    dictionary = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(df[col].dtype) for col in df.columns],
        "description": [COLUMN_DESCRIPTIONS.get(col, "") for col in df.columns],
    })

    print("\nData dictionary:")
    # to_string(index=False) prints the DataFrame as a table without the
    # row-number index on the left, which is cleaner for a reference table.
    print(dictionary.to_string(index=False))
    print()


def main():
    """Run the full data prep pipeline, step by step."""
    df = load_raw_data(RAW_PATH)
    df = rename_columns(df)
    check_data_quality(df)
    save_processed_data(df, PROCESSED_PATH)
    print_summary(df)


# This "if __name__ == '__main__'" guard means the code inside only runs
# when you execute this file directly (e.g. `python src/data_prep.py`),
# not when some other script does `import data_prep` to reuse its
# functions. It's the standard Python pattern for a "runnable script that's
# also importable".
if __name__ == "__main__":
    main()

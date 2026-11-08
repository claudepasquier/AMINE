#!/usr/bin/env python3
"""Regenerate ``benchmarks/methods.xlsx`` from the baseline table plus new data.

The historical comparison table lives in
``old_code/active_module_detection/methods.xlsx`` (sheet ``list of tools``).
This script:

1. loads that baseline (or the current ``benchmarks/methods.xlsx``);
2. merges any additional tool rows found in ``benchmarks/competitors/tools_extra.csv``
   (or a file passed with ``--extra``);
3. de-duplicates rows by tool ``name`` (new rows win);
4. writes the result back to ``benchmarks/methods.xlsx``.

The extra CSV must use the same columns as the baseline:

    name, year, reference, principle, langage, type, note,
    link to the executable, link to the article

Usage::

    python benchmarks/update_methods_table.py
    python benchmarks/update_methods_table.py --extra new_tools.csv
"""

from __future__ import annotations

import argparse
import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
BASELINE = REPO_ROOT / "old_code" / "active_module_detection" / "methods.xlsx"
OUTPUT = HERE / "methods.xlsx"
DEFAULT_EXTRA = HERE / "competitors" / "tools_extra.csv"
SHEET_NAME = "list of tools"

COLUMNS = [
    "name",
    "year",
    "reference",
    "principle",
    "langage",
    "type",
    "note",
    "link to the executable",
    "link to the article",
]


def load_baseline() -> pd.DataFrame:
    """Load the baseline table, preferring the current output if it exists."""
    source = OUTPUT if OUTPUT.is_file() else BASELINE
    if not source.is_file():
        raise FileNotFoundError(
            f"no baseline table found (looked for {OUTPUT} and {BASELINE})"
        )
    df = pd.read_excel(source, sheet_name=SHEET_NAME)
    return df


def load_extra(path: pathlib.Path) -> pd.DataFrame:
    """Load additional rows from a CSV file, if it exists."""
    if not path.is_file():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"extra file {path} is missing columns: {missing}")
    return df[COLUMNS]


def merge(baseline: pd.DataFrame, extra: pd.DataFrame) -> pd.DataFrame:
    """Merge baseline and extra rows, de-duplicating by tool name."""
    combined = pd.concat([baseline, extra], ignore_index=True)
    # New rows (from ``extra``) win: keep the last occurrence of each name.
    combined = combined.drop_duplicates(subset=["name"], keep="last")
    combined = combined.sort_values(by=["year", "name"], na_position="last")
    return combined.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extra",
        type=pathlib.Path,
        default=DEFAULT_EXTRA,
        help="CSV file with additional tool rows",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=OUTPUT,
        help="path of the generated xlsx file",
    )
    args = parser.parse_args()

    baseline = load_baseline()
    extra = load_extra(args.extra)
    table = merge(baseline, extra)

    with pd.ExcelWriter(args.output) as writer:
        table.to_excel(writer, sheet_name=SHEET_NAME, index=False)

    print(
        f"wrote {len(table)} tools to {args.output} "
        f"({len(extra)} new/updated rows from {args.extra})"
    )


if __name__ == "__main__":
    main()

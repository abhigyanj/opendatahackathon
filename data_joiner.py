#!/usr/bin/env python3
# coding: utf-8
import os
import sys
import csv
import io
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import chardet
import pandas as pd

"""
Interactive merger for Japanese public facilities CSV files.
Changes:
- Removed 'description' field.
- Added optional automatic pre-selection of columns based on header names
    (e.g., 'URL' -> url, '名前' -> name).
"""

try:
        import chardet
except ImportError:
        chardet = None

try:
        import pandas
except ImportError:
        print("Please install pandas first: pip install pandas")
        sys.exit(1)

# Target fields (description removed)
TARGET_FIELDS = ["name", "address", "url", "latitude", "longitude"]

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = Path(__file__).parent / "public_facilities_merged.csv"

# Heuristic patterns for auto-detection (case-insensitive)
FIELD_PATTERNS: Dict[str, List[str]] = {
        "name": [r"^名称$"],
        "address": [r"^住所$"],
        "url": [r"^URL$"],
        "latitude": [r"^緯度$"],
        "longitude": [r"^経度$"],
}


def detect_encoding(file_path: Path, sample_size: int = 200000) -> str:
        common = ["utf-8-sig", "utf-8", "cp932", "shift_jis", "euc_jp"]
        if chardet:
                with open(file_path, "rb") as f:
                        raw = f.read(sample_size)
                result = chardet.detect(raw)
                enc = (result.get("encoding") or "").lower()
                if enc:
                        return enc
        for enc in common:
                try:
                        with open(file_path, "r", encoding=enc) as f:
                                f.readline()
                        return enc
                except Exception:
                        continue
        return "utf-8"


def load_dataframe(file_path: Path) -> Tuple[pd.DataFrame, str]:
        enc = detect_encoding(file_path)
        try:
                df = pd.read_csv(
                        file_path,
                        encoding=enc,
                        dtype=str,
                        encoding_errors="replace",
                        on_bad_lines="skip"
                )
                return df, enc
        except TypeError:
                with open(file_path, "rb") as f:
                        raw = f.read()
                text = raw.decode(enc, errors="replace")
                df = pd.read_csv(io.StringIO(text), dtype=str)
                return df, enc


def show_sample(df: pd.DataFrame, max_rows: int = 5) -> None:
        rows = min(len(df), max_rows)
        print(f"Showing first {rows} rows:")
        cols = list(df.columns)
        print("Column indices:")
        for idx, col in enumerate(cols):
                print(f"  [{idx}] {col}")
        print("-" * 60)
        for r in range(rows):
                print(f"Row {r}:")
                for idx, col in enumerate(cols):
                        val = df.iloc[r, idx]
                        if isinstance(val, str):
                                val = val.replace("\n", " ")[:80]
                        print(f"  ({idx}) {col}: {val}")
                print("-" * 60)


def guess_column_indices(df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Return suggestions mapping field -> index list string like '2' or '3+4',
        or None if no guess.
        """
        suggestions: Dict[str, Optional[str]] = {}
        cols = list(df.columns)
        for field, patterns in FIELD_PATTERNS.items():
                matched_indices: List[int] = []
                for i, col in enumerate(cols):
                        norm = str(col).strip().lower()
                        for pat in patterns:
                                if re.fullmatch(pat, norm, flags=re.IGNORECASE):
                                        matched_indices.append(i)
                                        break
                if matched_indices:
                        suggestions[field] = "+".join(str(i) for i in matched_indices)
                else:
                        suggestions[field] = None
        return suggestions


def prompt_column_mapping(
        df: pd.DataFrame,
        file_path: Path,
        suggestions: Optional[Dict[str, Optional[str]]] = None
) -> Dict[str, Optional[str]]:
        print(f"\nMapping columns for file: {file_path.name}")
        print("Enter the column index for each target field.")
        print("You can enter:")
        print("  - a single index (e.g., 2)")
        print("  - multiple indices joined by '+' to concatenate (e.g., 0+3)")
        print("  - leave blank to skip (unless a default is shown; Enter accepts default)")
        print("  - 'skipfile' to skip the entire file\n")

        mapping: Dict[str, Optional[str]] = {}
        columns = list(df.columns)

        for field in TARGET_FIELDS:
                default_spec = suggestions.get(field) if suggestions else None
                while True:
                        suffix = f" [default: {default_spec}]" if default_spec else ""
                        user_in = input(f"{field} column index(es){suffix}: ").strip()
                        if user_in.lower() == "skipfile":
                                return {"_skipfile": "1"}
                        if user_in == "":
                                if default_spec:
                                        # Use default indices
                                        parts = default_spec.split("+")
                                        selected_cols = [columns[int(p)] for p in parts]
                                        mapping[field] = "|".join(selected_cols)
                                else:
                                        mapping[field] = None
                                break
                        if re.fullmatch(r"[0-9]+(\+[0-9]+)*", user_in):
                                parts = user_in.split("+")
                                valid = True
                                for p in parts:
                                        if int(p) < 0 or int(p) >= len(columns):
                                                print("Index out of range. Try again.")
                                                valid = False
                                                break
                                if not valid:
                                        continue
                                selected_cols = [columns[int(p)] for p in parts]
                                mapping[field] = "|".join(selected_cols)
                                break
                        else:
                                print("Invalid format. Use indices like: 3 or 0+2. Try again.")
        return mapping


def extract_value(row: pd.Series, spec: Optional[str]) -> Optional[str]:
        if spec is None:
                return None
        col_list = spec.split("|")
        vals = []
        for c in col_list:
                if c in row and pd.notna(row[c]):
                        vals.append(str(row[c]).strip())
        if not vals:
                return None
        return " ".join(vals).strip()


def to_float(val: Optional[str]) -> Optional[float]:
        if val is None:
                return None
        v = val.strip()
        if v == "":
                return None
        v = v.replace("．", ".")
        m = re.search(r"-?\d+(?:\.\d+)?", v)
        if not m:
                return None
        try:
                return float(m.group())
        except ValueError:
                return None


def process_file(df: pd.DataFrame, file_path: Path, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
        rows = []
        for _, row in df.iterrows():
                record = {
                        "name": extract_value(row, mapping.get("name")),
                        "address": extract_value(row, mapping.get("address")),
                        "url": extract_value(row, mapping.get("url")),
                        "latitude": None,
                        "longitude": None,
                        "source_file": file_path.name
                }
                lat_raw = extract_value(row, mapping.get("latitude"))
                lon_raw = extract_value(row, mapping.get("longitude"))
                if lat_raw and lon_raw is None:
                        if "," in lat_raw:
                                parts = [p.strip() for p in lat_raw.split(",")]
                        elif " " in lat_raw:
                                parts = [p.strip() for p in lat_raw.split()]
                        else:
                                parts = [lat_raw]
                        if len(parts) >= 2:
                                record["latitude"] = to_float(parts[0])
                                record["longitude"] = to_float(parts[1])
                else:
                        record["latitude"] = to_float(lat_raw)
                        record["longitude"] = to_float(lon_raw)
                rows.append(record)
        out_df = pd.DataFrame(rows)
        for col in ["name", "address", "url"]:
                if col in out_df:
                        out_df[col] = out_df[col].fillna("").str.strip()
                        out_df.loc[out_df[col] == "", col] = None
        return out_df


def main():
        print("Public Facilities CSV Joiner (Interactive)")
        print(f"Scanning directory: {DATA_DIR}")
        if not DATA_DIR.exists():
                print("Data directory not found.")
                return

        auto_choice = input("Enable automatic column pre-selection? (Y/n): ").strip().lower()
        use_auto = (auto_choice == "" or auto_choice == "y")

        csv_files = sorted([p for p in DATA_DIR.glob("*.csv") if p.is_file()])
        if not csv_files:
                print("No CSV files found.")
                return

        merged_frames: List[pd.DataFrame] = []

        for f in csv_files:
                print("\n" + "=" * 80)
                print(f"File: {f.name}")
                try:
                        df, enc = load_dataframe(f)
                except Exception as e:
                        print(f"Failed to read {f.name}: {e}")
                        continue
                print(f"Detected / chosen encoding: {enc}")
                print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
                show_sample(df)

                suggestions = guess_column_indices(df) if use_auto else None
                if suggestions and any(v for v in suggestions.values()):
                        print("Auto-detected suggestions:")
                        for k, v in suggestions.items():
                                if v:
                                        print(f"  {k}: indices {v}")
                mapping = prompt_column_mapping(df, f, suggestions=suggestions)
                if "_skipfile" in mapping:
                        print(f"Skipping file {f.name}")
                        continue

                subset_df = process_file(df, f, mapping)
                print(f"Added {len(subset_df)} rows from {f.name}")
                merged_frames.append(subset_df)

                cont = input("Continue to next file? (Y/n): ").strip().lower()
                if cont == "n":
                        break

        if not merged_frames:
                print("No data collected. Exiting.")
                return

        final_df = pd.concat(merged_frames, ignore_index=True)
        cols_order = ["name", "address", "url", "latitude", "longitude", "source_file"]
        final_df = final_df[cols_order]

        final_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
        print(f"\nMerged file written to: {OUTPUT_FILE}")
        print(f"Total rows: {len(final_df)}")


if __name__ == "__main__":
        try:
                main()
        except KeyboardInterrupt:
                print("\nInterrupted by user.")
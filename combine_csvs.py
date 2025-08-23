import pandas as pd
import glob

# Find all CSV files in the current directory
def find_csv_files():
    return glob.glob("*.csv")

# Try to read a CSV file with utf-8, fallback to cp932
def read_csv_auto(file):
    try:
        return pd.read_csv(file, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(file, encoding="cp932")

def main():
    csv_files = find_csv_files()
    if not csv_files:
        print("No CSV files found.")
        return
    dfs = []
    for file in csv_files:
        print(f"Reading {file} ...")
        df = read_csv_auto(file)
        df['source_file'] = file  # Track source
        dfs.append(df)
    combined = pd.concat(dfs, ignore_index=True, sort=True)
    combined.to_csv("all_data_combined.csv", index=False)
    print(f"Combined {len(csv_files)} files. Output: all_data_combined.csv")
    print(combined.info())
    print(combined.head())

if __name__ == "__main__":
    main()

# opendatahackathon

## CSV Data Combination

This project includes a script to combine all CSV files in the folder, even if their headers differ. The combined data will be saved as `all_data_combined.csv`.

### How to use

1. Install requirements:
	```sh
	pip install -r requirements.txt
	```
2. Run the script:
	```sh
	python combine_csvs.py
	```
3. The output file `all_data_combined.csv` will contain all rows from all CSVs, with columns aligned by name.

### Requirements

- Python 3.7+
- pandas

---
For the main web app, see `main.py` and `template.html`.
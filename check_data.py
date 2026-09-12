import csv
import glob
import os

for file in glob.glob("data/output/*.csv"):
    with open(file, encoding="utf-8") as f:
        rows = list(csv.reader(f))

    print(os.path.basename(file), "->", len(rows) - 1, "rows")
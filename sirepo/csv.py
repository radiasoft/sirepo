import csv
import pandas


def open_csv(path):
    with open(str(path)) as f:
        for r in csv.reader(f):
            yield r

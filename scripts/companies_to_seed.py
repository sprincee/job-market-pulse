"""Regenerate transform/seeds/companies.csv from config/companies.yaml, the list the
Lambda uses. Run after changing that list; a dbt test fails if they drift.

    .venv\\Scripts\\python.exe scripts\\companies_to_seed.py
"""
import csv, pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

companies = yaml.safe_load((ROOT / "config/companies.yaml").read_text())
with open(ROOT / "transform/seeds/companies.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["company_token", "company_name", "ats"])
    for c in sorted(companies, key=lambda c: c["token"]):
        w.writerow([c["token"], c["name"], c["ats"]])

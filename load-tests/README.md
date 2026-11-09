# Load / Performance Testing (Locust)

Load tests run **only against the web application's backend API**, started
locally on the CI runner (SQLite DB) — never a third-party system.

## Layout
- `locustfile.py` — the load profile (weighted analyst read-mix + health traffic), grouped request names.
- `config.py` — env-driven config (`LOAD_BASE_URL`, users, spawn rate, run time, seeded creds).
- `thresholds.py` — CI-friendly per-endpoint p95 / error-rate ceilings + global gate.
- `test_cases/generate_catalog.py` — generates the 350+ case catalog (`load_test_cases.json/csv` + `test-cases/load_test_cases.xlsx`).
- `reports/generate_report.py` — reads the **real** Locust CSV, evaluates each case, writes `load_report.xlsx/json` + `summary.md`, and **fails the job on a genuine threshold breach**.

## Run locally
```bash
pip install -r requirements.txt
# start the backend first (from ../backend):  uvicorn app.main:app --port 8000
python test_cases/generate_catalog.py
locust -f locustfile.py --headless -u 25 -r 5 -t 90s \
       --host http://127.0.0.1:8000 --csv reports/load --only-summary
python reports/generate_report.py --stats reports/load_stats.csv
```

Status is derived from measured statistics only; endpoints that were not
exercised are reported as **SKIPPED**, never silently passed.

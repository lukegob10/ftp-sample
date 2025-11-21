# FTP Engine Workspace

Project layout for FTP engine planning, configs, and sample data.

- docs/: planning and design docs (`project-plan.md`, `ftp-engine-ftp-plan.md`, `bank-assets-liabilities.md`, `segmentation-mapping.md`).
- config/: analyst-editable inputs.
  - curves/: daily FTP curve snapshots (e.g., `ois-curve-2025-11-20.csv`).
  - segments/: segmentation mapping for FTP (e.g., `segmentation-mapping.csv` with `ticket_strategy` = match_funded|ladder).
- data/balance_sheet/: generated sample assets/liabilities CSVs.
- data/results/: FTP outputs.
- scripts/: utilities (e.g., `generate_balance_sheet.py`, `run_ftp_engine.py`).

Regenerate sample balance sheet (writes to `data/balance_sheet/`):
```
python3 scripts/generate_balance_sheet.py
```

Run FTP engine (uses today's date, OIS curve for that as_of_date, excludes equity):
```
python3 scripts/run_ftp_engine.py
```
Outputs FTP tickets to `data/results/ftp_results.csv` using 30/360 day count and the OIS curve for the run date. `ticket_strategy` in the segmentation file drives behavior: `match_funded` creates one ticket per instrument_id; `ladder` aggregates by segment (instrument IDs dropped) before laddering tickets. `side` column tags assets vs liabilities for reporting.

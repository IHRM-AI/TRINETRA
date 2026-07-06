# PRAHARI Data Acquisition

Four public datasets power the segment model zoo. Total disk budget: ~10 GB (we have ~21 GB free — do NOT download raw Amex, it's ~50 GB).

## Credentials needed first (user actions)

1. **Kaggle API token**: kaggle.com → Account → Settings → "Create New Token" → save as `~/.kaggle/kaggle.json`, then `chmod 600 ~/.kaggle/kaggle.json`.
   Also accept rules in the browser for each competition below (required before API download works).
2. **Freddie Mac**: free signup at https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset — then download the **Sample Dataset** (50k loans/year, ~a few hundred MB) manually into `prahari/data/raw/freddie/`.

## Downloads (after credentials)

```bash
cd "/Users/macbook/projects/IDBI HACKTHON/prahari/data/raw"
KAGGLE="../../../.venv/bin/kaggle"

# Segment 1 — Mortgage: Freddie Mac sample (MANUAL browser download, see above)

# Segment 2 — Behavioral/cards: Amex (parquet mirror, NOT the 50GB raw)
$KAGGLE datasets download -d raddar/amex-data-integer-dtypes-parquet-format -p amex/ --unzip

# Segment 3 — Retail unsecured: Home Credit (~2.5 GB)
$KAGGLE competitions download -c home-credit-default-risk -p homecredit/ && unzip -q homecredit/*.zip -d homecredit/

# Segment 4 — Indian vehicle loans: L&T/LTFS
$KAGGLE datasets download -d mamtadhaker/lt-vehicle-loan-default-prediction -p ltfs/ --unzip
```

## Label discipline (the whole game)

- **Freddie Mac**: build observation-point snapshots; label = D90+/default event within the NEXT 12 months of performance history after the observation point. No future information in features. Out-of-time split: train on observation vintages ≤ T, validate on > T.
- **Amex**: labels are "default within 18 months after last statement" — use as-is, note the horizon difference honestly on the benchmark slide.
- **Home Credit / LTFS**: application-time PD (no panel) — position as origination-risk segments, not EWS segments.
- Published baselines to beat/match (cite on S11): Freddie ~0.90 AUC (academic benchmarks), Amex LB ~0.80 (competition metric), Home Credit ~0.80 AUC.

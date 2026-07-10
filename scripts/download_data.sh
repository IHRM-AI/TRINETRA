#!/usr/bin/env bash
set -euo pipefail

# Public datasets for the segment model zoo. Requires a configured Kaggle API token
# (~/.kaggle/kaggle.json) and acceptance of each competition's rules in the browser.
# Datasets are never committed; see .gitignore.

RAW_DIR="$(cd "$(dirname "$0")/.." && pwd)/data/raw"
mkdir -p "$RAW_DIR"

# Indian segment: L&T vehicle-loan default
kaggle datasets download -d mamtadhaker/lt-vehicle-loan-default-prediction \
  -p "$RAW_DIR/ltfs" --unzip

# Retail unsecured: Home Credit Default Risk
kaggle competitions download -c home-credit-default-risk -p "$RAW_DIR/homecredit"
unzip -qo "$RAW_DIR/homecredit"/*.zip -d "$RAW_DIR/homecredit"

echo "Datasets downloaded to $RAW_DIR"

# US mortgage: Freddie Mac Single-Family / CRT loan-level sample (manual download,
# free account at freddiemac.com/research) -> place the zip in data/raw/freddie/.

# TRINETRA — MSME Early-Warning Risk Engine

**IDBI Innovate 2026 · Track 4 (Default Prediction Model)**

An ML + GenAI **augmentation layer** on the bank's existing rule-based Early-Warning System (EWS). It turns today's ~1-in-5 useful 12-month flags into a **calibrated, explainable probability of default** — every flag translated into RBI EWS-trigger language, every account one click from a human-approved credit memo.

> Augmentation, never replacement. TRINETRA ingests the existing ~80-trigger EWS as features and shared vocabulary — it extends it, never bypasses it.

## What it does
1. **Predicts** each borrower's probability of default over the next 12 months.
2. **Explains** every prediction in RBI EWS trigger language (SHAP to trigger taxonomy to SMA-0/1/2 staging).
3. **Acts** — drafts a one-page GenAI credit memo for officer approval (human-in-loop); moves accounts to the SMA watchlist / RFA queue.

## Architecture
| Layer | Technique |
|---|---|
| PD model zoo (per segment) | LightGBM / XGBoost on 12-month-ahead default labels |
| Behavioural trajectory | GRU / temporal model on statement sequences |
| Unified PD scale | Isotonic / Platt calibration |
| PD term structure | Discrete-time survival model (ECL / Ind AS 109-aligned) |
| Interpretation | SHAP to RBI EWS trigger taxonomy to SMA staging |
| News signal | Firecrawl (acquisition) + self-hosted Gemma-4 (extraction) |
| Document to data | OCR service (multi-language, handwritten) |
| GenAI credit memo | Self-hosted Gemma-4 via vLLM (on-prem, DPDP-compliant) |
| Serving | FastAPI to React cockpit |
| Governance | Champion-challenger, PSI drift, model cards, immutable audit log |

## Project layout
```
src/trinetra/
  config.py            environment-driven settings
  data/ltfs.py         dataset loading and parsing
  features/ltfs.py     feature construction
  models/gbm.py        LightGBM segment model with isotonic calibration
  eval/metrics.py      AUC, Gini, KS, Brier
  pipelines/           training entrypoints
```

## Quickstart
```bash
pip install -e ".[dev]"
cp .env.example .env          # fill in self-hosted endpoints when the GPU is running
bash scripts/download_data.sh # requires a Kaggle API token
make train                    # trains the L&T vehicle-finance segment
make test
```

## Current baseline
L&T vehicle-finance segment, out-of-time validation (~47k accounts): **AUC 0.65, Gini 0.30, KS 0.22**, calibrated. This is the CIBIL-style Indian segment; additional public segments (Home Credit, Amex, SBA, Freddie Mac) plug into the same interface. Every model retrains on the bank's own book in the sandbox.

## Datasets
Public datasets only; licences restrict redistribution, so the repository ships download scripts, not data (see `scripts/download_data.sh` and `.gitignore`).

## Configuration
All secrets and service endpoints live in `.env` (git-ignored). See `.env.example` for the self-hosted Gemma-4 (vLLM), OCR, and Firecrawl variables. With no endpoints set, the GenAI layer is disabled and the quantitative pipeline runs standalone.

## Compliance
On-prem LLM, no PII egress, DPDP-compliant, deployable beside core banking with zero customer-facing exposure. Every external-rail mock is labelled as a mock.

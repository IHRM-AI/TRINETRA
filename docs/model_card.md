# Model Card — TRINETRA MSME Early-Warning PD Engine

Version 0.1.0. This card documents the probability-of-default (PD) models that
power TRINETRA and the interpretation layer built on top of them. It follows the
model-card structure banks use for model-risk governance and is deliberately
explicit about limitations.

## Overview

- **Name.** TRINETRA MSME Early-Warning Risk Engine.
- **Owner.** Team IHRM (IDBI Innovate 2026, Track 4 — Default Prediction Model).
- **Model type.** One gradient-boosted decision-tree classifier (LightGBM) per
  loan segment, each followed by an isotonic-regression probability calibrator
  fitted on a dedicated held-out set.
- **Output.** A calibrated 12-month probability of default per borrower, mapped
  to a static PD-band grade and watch tier and accompanied by SHAP-derived
  reason codes expressed in RBI Early-Warning-System (EWS) trigger language.
- **Status.** Prototype for evaluation on public proxy data. Not in production
  use and not fitted on any IDBI Bank data.

## Intended use

- **Purpose.** Decision *support* for credit monitoring and early-warning. The
  engine augments the bank's existing rule-based EWS by turning its triggers
  into a calibrated, ranked, explainable PD, so officers can prioritise the
  monitored book and act earlier.
- **Human in the loop.** Every actionable output — watchlist placement, RFA
  review, credit memo — is drafted for and requires human officer approval. The
  generated credit memo carries an explicit "Awaiting officer approval" status.
- **Augmentation, never replacement.** The engine ingests the existing EWS
  triggers as features and shared vocabulary. It extends the EWS; it does not
  bypass or override it, and it does not make automated credit decisions.
- **Users.** Credit-monitoring officers and risk analysts inside the bank.

## Out-of-scope uses

- Automated approve/decline or limit decisions without human review.
- Consumer-facing scoring, adverse-action adjudication, or any customer-facing
  exposure.
- Regulatory capital calculation, IFRS 9 / ECL provisioning, or Basel PD
  estimation — the models are not validated or calibrated for those purposes.
- Any use on populations, products, or geographies unlike the training data
  without re-training and re-validation on the bank's own book.
- Treating the monthly PD term structure as a fitted survival model (see
  Limitations).

## Model architecture

| Layer | Technique |
|---|---|
| PD model (per segment) | LightGBM on 12-month-ahead binary default labels |
| Probability calibration | Isotonic regression on a held-out calibration split |
| PD term structure | Heuristic Gaussian-hazard allocator (not a fitted hazard model) |
| Interpretation | SHAP margin contributions mapped to an RBI EWS trigger taxonomy, then to static PD-band watch tiers |
| GenAI credit memo | Self-hosted Gemma via vLLM (optional, gated on `.env`) |

Booster hyperparameters are fixed and seeded for reproducibility
(`src/trinetra/models/gbm.py`). The calibrator is fitted only on data used for
neither training nor early stopping, so isotonic calibration does not leak into
reported metrics.

## Datasets, splits, and metrics

All datasets are public proxies used because loan-level default data with a
12-month label is not otherwise obtainable for a prototype. The bank's own book
would replace them in a sandbox. Metrics below are measured on a held-out test
block the model never saw during training, early stopping, or calibration, and
are reproduced in `artifacts/zoo_benchmark.json`.

| Segment | Dataset | Split | n (test) | Default rate | AUC | Gini | KS | Brier |
|---|---|---|---|---|---|---|---|---|
| India vehicle finance | L&T / LTFS | out-of-time (DisbursalDate) | 46,631 | 0.259 | 0.642 | 0.283 | 0.207 | 0.184 |
| Retail unsecured | Home Credit | random (no vintage field) | 61,502 | 0.081 | 0.746 | 0.493 | 0.366 | 0.068 |
| US mortgage | Freddie Mac (CRT loan-level) | out-of-time (origination date) | 383,644 | 0.020 | 0.750 | 0.499 | 0.376 | 0.015 |

Notes on the splits:

- **LTFS** and **Freddie** use genuine out-of-time evaluation — the model trains
  on earlier vintages and is tested on later ones, the honest setting for a
  forward-looking early-warning model. The LTFS AUC of 0.64 is modest and
  reflects a thin, noisy public feature set on an out-of-time split; it is
  reported as-is rather than inflated by a random split.
- **Home Credit** carries only relative `DAYS_*` fields and no absolute
  origination date, so it uses a fixed-seed stratified random split. Its 0.75
  AUC is therefore *not* out-of-time and is not directly comparable to the other
  two; a true out-of-time evaluation is pending vintage-stamped data.

### Metric definitions

- **AUC** — area under the ROC curve; rank-ordering power (`sklearn`).
- **Gini** — `2 * AUC - 1`.
- **KS** — maximum gap between the cumulative default and non-default
  distributions across the score.
- **Brier** — mean squared error between calibrated PD and outcome; lower is
  better and rewards good calibration, not just ranking.

## Calibration

Raw booster margins are mapped to probabilities by isotonic regression fitted on
a dedicated calibration split, with out-of-range inputs clipped. Calibration
quality is summarised by the Brier score above. Isotonic calibration is
monotone and non-parametric, so it preserves the booster's rank ordering (AUC,
Gini, KS are unchanged) while improving probability reliability.

## Limitations

- **Public-data proxies.** Models are trained on public datasets, not IDBI Bank
  data. Reported metrics describe those datasets and do not transfer to the
  bank's portfolio without re-training and re-validation.
- **Synthetic demo portfolio.** The cockpit's book of accounts is illustrative:
  company names, sectors, regions, and exposures are demo data. Only the PD is
  model-derived (scored on the public LTFS dataset). The API marks this book
  with `synthetic: true` and the cockpit shows a standing banner.
- **Heuristic PD term structure.** The monthly PD curve is a hand-set
  Gaussian-hazard allocation of the 12-month PD, *not* a fitted discrete-time
  hazard/survival model. The available datasets carry a single binary 12-month
  label with no time-to-event field, so a hazard model cannot be estimated from
  them. A fitted survival model is roadmap work.
- **Modest LTFS discrimination.** Out-of-time AUC of 0.64 on LTFS indicates
  limited separation on that thin public feature set; the engine adds value as a
  ranking and triage aid, not as a precise standalone predictor.
- **Static watch tiers.** Watch tiers derive from static PD bands, not from
  days-past-due SMA-0/1/2 staging. True DPD staging is roadmap work.
- **No live external rails.** News/adverse-media (Firecrawl), OCR, and the GenAI
  memo (Gemma via vLLM) are optional HTTP clients gated on `.env` endpoints.
  With no endpoints configured the GenAI layer is disabled and the quantitative
  pipeline runs standalone.
- **Segment coverage.** Only the three segments above are implemented. Other
  products would need their own trained segment.

## Fairness and monitoring stance

- **Fairness.** No protected-attribute fairness testing has been performed on
  the public proxy data. Before any deployment on the bank's book, the model
  must be assessed for disparate impact across protected classes under the
  applicable regulatory framework, and reason codes reviewed for proxy bias.
- **Monitoring (roadmap, not yet implemented).** Production use would require
  PSI/CSI drift monitoring on features and scores, champion-challenger
  evaluation, periodic recalibration, back-testing of realised defaults against
  predicted PD, and an immutable audit log of scores and overrides. These are
  tracked in the README roadmap and are not part of this prototype.

## Ethical and compliance considerations

- On-premises LLM with no PII egress; designed to be DPDP-compliant and
  deployable beside core banking with zero customer-facing exposure.
- Human-in-the-loop by design: the engine informs officers, it does not decide.
- All secrets and service endpoints live in `.env` (git-ignored); see
  `SECURITY.md`.

## References

- Benchmark artefacts: `artifacts/zoo_benchmark.json`, `artifacts/ltfs_metrics.json`.
- Model implementation: `src/trinetra/models/gbm.py`.
- Interpretation layer: `src/trinetra/interpret/`.
- PD term structure: `src/trinetra/survival/term_structure.py`.
- Metrics: `src/trinetra/eval/metrics.py`.

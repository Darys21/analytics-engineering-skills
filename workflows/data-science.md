# Workflow: data-science

## Purpose
Decide whether ML is justified, then produce a validated, interpretable, monitored predictive or prescriptive model. Always start from simpler analytical baselines and escalate complexity only when value is demonstrated.

## When to use
- Explicit forecasting, classification, regression, clustering, ranking, anomaly detection, or optimization requirement.
- Descriptive / diagnostic analysis (`statistics` workflow) cannot answer the question with sufficient accuracy or automation.
- A business decision depends on a predicted quantity and the cost of wrong predictions is quantifiable.

Do **NOT** use:
- If descriptive analysis, simple heuristics, or threshold-based rules suffice.
- Before a baseline non-ML solution exists.
- Without labeled ground truth or a way to measure model performance after deployment.
- For the first pass at a "why did X happen" question — use `business-analysis` + `statistics`.

## Inputs
- Business objective: what decision the prediction/insight will support, cost of errors.
- Historical dataset: features, label (if supervised), timeframe, grain, known gaps.
- Baseline: non-ML baseline already implemented (required) and its performance.
- Stakeholder for the model output: persona, latency/freshness SLA, interpretability needs.
- Deployment target: batch vs. online, environment, constraints (memory, latency, cost).

## Preconditions
- A non-ML baseline exists (simple heuristic, last-period carry, rule-based) and its metrics are recorded.
- The business value of improved accuracy (or automation) exceeds the cost of building and operating the model.
- Label / ground-truth collection is ongoing, not a one-time extract.

## Procedure
1. **Confirm problem framing.**
   - Supervised vs. unsupervised vs. time-series. Classification vs. regression vs. ranking.
   - Metrics: pick primary metric (business-aligned) and guardrail metrics. Examples: precision@k, recall, F1, AUC, Brier, RMSE, MAE, MAPE, WAPE, calibration error, fairness score, latency.
   - Decision threshold and cost trade-offs: false positive vs. false negative costs.
2. **Baseline first.**
   - Simple baseline: last-value, seasonal naive, moving average, rule-based, logistic regression or shallow decision tree.
   - Record baseline metrics and store baseline predictions for comparison.
3. **Data preparation and leakage prevention.**
   - Explicit temporal split: train/val/test by time (time-series) or by cohort. No random splits for time-dependent problems.
   - Feature engineering: no use of future information. No aggregate features computed across the whole dataset before splitting.
   - Handle missing values with documented strategy, consistent across train/serve.
   - Categorical encoding, scaling, normalization — fit only on train, apply to val/test.
4. **Model training progression (start simple, increase complexity only if it moves the primary metric).**
   - Linear / GLM baseline → shallow tree (RF / GBDT with few trees) → deeper GBDT / NN only if justified.
   - Cross-validation: stratified, grouped, or time-series CV depending on problem.
   - Hyperparameter search: only after the model family is justified; keep search bounded.
5. **Validation & calibration.**
   - Hold-out test set, never used for any training or hyperparameter tuning.
   - Report primary + guardrail metrics on test. Compare to baseline.
   - Calibration: reliability diagrams, Platt/Isotonic for classifiers; residual analysis for regressors.
   - Slices: performance on key segments (regions, cohorts, old vs. new users, rare classes). Degradation on a critical slice often blocks deployment even if overall is better.
6. **Interpretability.**
   - Feature importance (global). Permutation importance preferred over in-model when possible.
   - Local explanations (SHAP/LIME, or simpler model-specific) for a sample of predictions including high-error cases.
   - Document known failure modes, edge cases, conditions under which model will misbehave.
7. **Robustness.**
   - Sensitivity to small input perturbations.
   - Missing / corrupted value handling at serve time.
   - Adversarial or distribution-shift scenarios: sanity check on periods outside train window.
8. **Deployment and monitoring design.**
   - Batch vs. online; serving environment; latency and throughput budget.
   - Monitoring plan: data drift (feature distribution, prediction distribution), concept drift (ground truth when label arrives), performance monitoring, slice monitoring, job health.
   - Rollback plan: switch to the non-ML baseline with a config toggle.
9. **Post-deployment.**
   - First-N-days watch on predictions, monitors, and business outcome metrics.
   - Retrain cadence and trigger conditions (performance drop threshold, drift threshold).
   - Retire older models explicitly.

## Decision points
- If baseline + shallow model perform within X% of the complex model → stop and ship the simpler one. Document why.
- If primary metric gain is real but business impact (dollars, decisions) is smaller than operational cost → do not deploy ML; recommend baseline automation.
- If slice-level performance unacceptable → add slice to loss / sampling / collection plan, or scope out model from that slice.
- If ground truth delay > acceptable window → define proxy label + fallback monitoring.

## Validation
- Holdout primary metric strictly better than baseline by agreed margin.
- No slice performance below the guardrail threshold on critical segments.
- Predictions reproducible: same code + same random seed + same data → same model file and same outputs (to within floating tolerance).
- Calibration within tolerance on holdout.
- Feature importance sensible to domain expert; no obvious leakage signatures (e.g., near-perfect score from an ID-like feature).

## Expected outputs
- Problem framing document: objective, metrics, decision threshold, error costs.
- Baseline performance table and stored baseline predictions.
- Train/val/test split definition (with time/cohort boundaries) + leakage audit.
- Model comparison table: complexity vs. metrics per candidate.
- Final model card: data, features, architecture, metrics, slices, calibration, known limitations, owners.
- Interpretation: global + local.
- Deployment runbook + monitoring plan + rollback plan (with baseline toggle).
- Drift / performance retraining policy.

## Common failure modes
- ML-first: no baseline, so no idea whether model is useful.
- Random splits on time-series → inflated in-sample metrics, failure in production.
- Leakage: any aggregate computed over full data, or use of future values. Number one failure mode.
- Single-metric myopia: AUC great but calibration / slice performance / latency terrible.
- No plan for data or concept drift; model rots silently.
- Complex model chosen for aesthetics; cost >> value.
- Deployment without monitoring and baseline rollback → when it breaks, it breaks silently and users suffer.

## References to load
- `references/data-science.md`
- `references/statistics.md` — baseline stats, sampling, CI on metrics, effect size.
- `references/python.md` — training code, reproducibility, testing.
- `references/testing.md` — numerical equivalence, regression testing for models.
- `references/observability.md` — drift, performance monitoring, alerting.
- `references/ci-cd.md` — model CI, validation gates, rollback.

## Completion criteria
- Non-ML baseline implemented, measured, and beaten (or justification documented why ML was skipped).
- Leakage audit performed and documented; split logic explicit.
- Final model selected on holdout set; primary + guardrail metrics met.
- Slice-level performance checked; critical slices acceptable or in-scope failure documented.
- Interpretation available (global feature importance + local examples + failure modes).
- Deployment target, serving path, latency/freshness SLA, and monitoring defined.
- Rollback-to-baseline plan tested or trivially executable.
- Retraining cadence and triggers defined.

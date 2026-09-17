# Workflow: STATISTICS — Rigorous Inference for Analytics

## Purpose

Apply and interpret statistical methods correctly in support of analytics decisions: descriptive statistics, distributions, sampling, confidence intervals, hypothesis testing, correlation, regression, effect sizes, statistical vs practical significance, uncertainty quantification, outlier classification, bias detection, confounding control, Simpson's paradox detection, time-series decomposition, multiple comparison correction, and explicit acknowledgment of causal inference limitations. The goal of this workflow is not to "make numbers look significant" but to produce honest, caveat-bound statistical conclusions that stakeholders can trust when making decisions. Misapplied statistics are worse than no statistics.

## When to use

- When a dashboard or report includes a comparative claim: "Y is up 15%," "Region X outperforms others," "Change A drove result B."
- When a sample is used to generalize to a larger population (e.g., survey data, A/B test data, sample audit of invoices).
- When performing root cause analysis and using statistics to rule out chance as an explanation for a KPI movement.
- When building an anomaly detector or threshold/alert that uses statistical baselines.
- When interpreting regression or ML output to claim "X causes Y" (explicit causal claims need extra scrutiny).
- When reviewing work produced by others that contains statistical claims.

## Inputs

- The analytical question and a signed-off BUSINESS-SPEC identifying the decision, KPIs, and thresholds.
- A clean, validated dataset from gold marts / semantic models; run a DATA-QUALITY pass first.
- Context on sampling frames, survey methodology, or experiment design if data is from a sample.
- Access to statistical software: Python (numpy, scipy.stats, statsmodels, pingouin), R, or equivalent validated library.
- The decision-maker's tolerance for false positives and false negatives (α and β levels; or use defaults α=0.05, β=0.20 / Power=0.80 unless overridden by the BUSINESS-SPEC).

## Preconditions

- The underlying data has passed data quality checks for the relevant time periods and groups.
- The analyst can distinguish a population from a sample in the given dataset.
- The decision-maker has stated what magnitude of effect is practically meaningful (e.g., "a cost improvement of <1% is too small to act on, even if statistically significant").

## Procedure

1. **State the research question, hypotheses, and population explicitly before computing anything.**
   1. **Research question:** One sentence. "Is mean haul cost per tonne-kilometre significantly different between Site A and Site B during Q1–Q3?"
   2. **Population:** "All haul trips at Site A and Site B in Q1–Q3 that passed data-quality checks."
   3. **Sample vs population:** Clarify whether the data is the full population (all trips recorded) or a sample (random 10% audit). If it is a sample, document the sampling frame, sampling method (random/stratified/ convenience/snowball), and response rate.
   4. **Null hypothesis (H₀):** Statement of no effect / no difference. "Mean cost/TKm at Site A = Mean cost/TKm at Site B."
   5. **Alternative hypothesis (H₁):** Statement of the effect (one-sided or two-sided). Two-sided is the default; one-sided requires explicit justification: "Site A mean ≠ Site B mean (two-sided)."
   6. **Alpha (α):** Probability of Type I error (false positive). Default 0.05; 0.01 if false positives are very costly (e.g., financial fraud detection).
   7. **Power (1 − β):** Probability of detecting a true effect. Default 0.80. Minimum detectable effect (MDE): use SME-defined practical significance threshold from preconditions.
   8. **Practical significance threshold:** "We will only act on differences >1% absolute or >5% relative, regardless of p-value."
2. **Compute and report descriptive statistics first; plot before testing.**
   1. For every continuous variable involved:
      - Central tendency: mean, trimmed mean (5–25%), median.
      - Spread: standard deviation, IQR, MAD (median absolute deviation), range.
      - Shape: skewness, excess kurtosis, number of modes observed.
      - Quantiles: P5, P25, P50, P75, P95, P99.
   2. For every categorical variable: counts, percentages, mode.
   3. **Plot first, test second:** Always produce:
      - Histogram + KDE + rug plot for each continuous variable.
      - Boxplots per group.
      - QQ plots against theoretical distribution (normal is the default assumption for parametric tests).
      - Scatterplots with LOWESS/loess smooth for bivariate relationships.
   4. If descriptive plots show violations of assumptions (heavy skewness, multimodality, outliers), note them in step 4 and choose tests robust to those violations.
3. **Characterize distributions and choose appropriate statistical methodology.**
   1. **Normal/Gaussian assumption check:**
      - Visual: QQ plot, histogram.
      - Formal: Shapiro-Wilk (small N <5000), Anderson-Darling, Kolmogorov-Smirnov.
      - Note: With very large N (>100k), normality tests will almost always reject H₀ even for trivial deviations; rely on visual + central limit theorem (CLT) reasoning for sample means.
   2. **For heavy-tailed or skewed data:**
      - Prefer non-parametric tests (Mann-Whitney U, Kruskal-Wallis, Spearman's ρ) over parametric (t-test, ANOVA, Pearson's r), or robust variants of parametric tests.
      - Consider data transformations (log, Box-Cox, Yeo-Johnson) if interpretation is preserved; never report transformed-scale results without back-transforming and acknowledging caveats.
   3. **For count data (Poisson):** Use Poisson or negative-binomial regression; do not apply t-tests.
   4. **For proportion / binary data:** Use chi-squared, Fisher's exact, beta-binomial, or logistic regression.
   5. **For time-series:** Decompose first (STL, MSTL, X11) into trend, seasonal, residual; tests apply to stationary residuals, never to raw trending series.
4. **Classify outliers and handle bias, missingness, and confounding explicitly.**
   1. **Outlier classification (never "delete outliers" as a default):**
      - Flag candidates via: robust methods (MAD-based z-score, robust Mahalanobis distance, IQR × 1.5 Tukey fences).
      - For each candidate, consult SME and classify as one of:
        1. **Data entry error / measurement error → Correct or remove with documentation.**
        2. **Legitimate but extreme value (a real 99th-percentile case) → Keep and use robust methods; conduct sensitivity analyses with and without it.**
        3. **Mixing of populations (e.g., test + production rows combined) → Stratify analysis; do not aggregate populations.**
      - Report outlier count, classification, and disposition in the write-up.
   2. **Bias detection:**
      - **Selection bias:** Does the sample systematically under-represent some part of the population? (e.g., a survey on email usage conducted by email)
      - **Survivorship bias:** Are entities that dropped out (closed sites, churned customers, scrapped assets) excluded from the analysis when they should be included?
      - **Measurement bias:** Are variables measured differently across groups? (e.g., Site A rounds to the nearest kg and Site B to the nearest tonne)
      - Document each suspected bias and its likely direction of effect on the result.
   3. **Missingness:**
      - Classify missingness mechanism for each variable: MCAR (missing completely at random), MAR (missing at random given observed covariates), MNAR (missing not at random — depends on unobserved value itself).
      - For MCAR/MAR with <10% missing: complete-case analysis acceptable; otherwise multiple imputation (MICE) or full-information maximum likelihood.
      - For MNAR: acknowledge that no statistical fix fully removes bias; flag in limitations.
   4. **Confounders and Simpson's paradox detection:**
      - List all known variables that could cause both the "treatment" group assignment and the outcome. Example: "Comparing cost per tonne between two fleets, confounders include average payload weight, route distance mix, driver tenure mix, truck age mix."
      - Run the analysis: (a) aggregated, (b) stratified by each plausible confounder. If the sign of the effect flips or disappears when conditioning on a covariate, you have Simpson's paradox.
      - Always report the covariate-adjusted view when a confounder is present; never only the aggregate. Simpson's paradox is a leading cause of wrong decisions from dashboards that slice only one dimension.
5. **Perform sampling, compute confidence intervals, and conduct hypothesis tests with documented assumptions.**
   1. **Sample size / power calculation first (if designing a study/survey/test):**
      - Use the SME MDE, α, and power (1 − β) to compute required sample size. For two-sample means: `n = 16 σ² / δ²` per group (rule of thumb for α=0.05, power=0.8, two-sided; replace with exact formula from stats package).
      - If the dataset already exists and is under-powered, state this explicitly: "Given observed σ = 23 and MDE = 5, we have 42% power to detect the SME threshold. A non-significant result does not rule out a real effect."
   2. **Confidence intervals (CIs) for every estimate — always, not just p-values:**
      - 95% CI by default; report along with the point estimate: `Mean difference (A − B) = −3.2 €/TKm, 95% CI [−5.9, −0.5]`.
      - Use appropriate CI methods per the distribution: Student-t for normal, bootstrap BCa for non-normal, Clopper-Pearson for proportions, robust sandwich estimators for regression.
      - Interpret correctly: "If we repeated this sampling procedure infinitely, 95% of such intervals would contain the true population difference." Never say: "There is a 95% probability the true mean is in this interval" (frequentist interpretation).
   3. **Hypothesis tests per design:**
      - One numeric variable vs hypothesized value → one-sample t-test (normal) or Wilcoxon signed-rank (non-parametric).
      - Two independent groups numeric → two-sample t-test (Welch if unequal variances assumed) or Mann-Whitney U.
      - Paired (before/after, matched) → paired t-test or Wilcoxon signed-rank.
      - Three+ groups → one-way ANOVA (parametric) / Kruskal-Wallis (non-parametric). Follow-up with post-hoc Tukey/Dunn with correction for multiple comparisons.
      - Two categorical variables (contingency) → chi-squared (all expected counts ≥5) or Fisher's exact (small cells).
      - Numeric vs numeric correlation → Pearson (linear, bivariate normal) or Spearman/Kendall τ (monotonic, robust to outliers / ordinal).
      - Time-dependent groups → difference-in-differences or interrupted time series, never a plain t-test of aggregated post vs pre.
   4. **Multiple comparison correction:** If >1 hypothesis test is run on the same dataset, apply a correction: Bonferroni (conservative, few tests), Benjamini-Hochberg (controls FDR, many tests). Report both uncorrected and corrected p-values. Failure to correct for multiple comparisons is the most common cause of spurious "statistically significant" results in analytics dashboards.
6. **Fit and interpret regressions; report effect sizes, not just p-values.**
   1. **Model choice matches outcome variable type:**
      - Continuous linear outcome → OLS / robust linear regression / mixed-effects (hierarchical).
      - Binary outcome → logistic regression.
      - Count → Poisson / negative binomial.
      - Time-to-event → Cox proportional hazards.
      - Hierarchical / clustered data (sites within regions, trips within drivers) → mixed-effects / hierarchical / multilevel models with random intercepts/slopes, never plain OLS that treats observations as independent.
   2. **Coefficient interpretation:** Write a plain-English sentence per coefficient. Example: "After adjusting for payload, route length, and truck age, Fleet B is associated with a mean cost/TKm decrease of 1.8 € (95% CI [−3.1, −0.5], p = 0.007) relative to Fleet A."
   3. **Effect size reporting (always):**
      - Standardized: Cohen's d (mean difference / pooled SD) for two groups, η² (proportion of variance explained) for ANOVA, r/ρ for correlation.
      - Interpret: Cohen's d ≈ 0.2 small, 0.5 medium, 0.8 large (adjust thresholds for the domain — in high-stakes logistics, 0.1 may be large).
      - Unstandardized effect size in business units (€, tonnes, days) is more useful to stakeholders than standardized; report both.
   4. **Assumption checks for regression models:**
      - Residual plots (residuals vs fitted, residuals vs each predictor, QQ of residuals).
      - Multicollinearity: VIF (variance inflation factor). VIF > 5 → investigate; VIF >10 → drop a predictor or combine.
      - Influential points: Cook's distance, leverage. Re-run model excluding top 1% of Cook's distances; if coefficients change by >20%, flag sensitivity.
      - Homoscedasticity: Breusch-Pagan / White test. If violated, use robust HC3 standard errors.
7. **Explicitly separate statistical significance from practical significance; quantify overall uncertainty.**
   1. **The four-cell decision matrix:**
      |                                  | Statistically significant | Not statistically significant |
      |----------------------------------|---------------------------|-------------------------------|
      | **Effect ≥ practical threshold** | ✅ Act                    | ⚠️ Under-powered; do not act, collect more data |
      | **Effect < practical threshold** | ❌ Do not act (stat sig but trivial) | ❌ Do not act (no evidence) |
   2. Always state which cell your result falls into. Never use "p < 0.05" as the sole criterion for acting.
   3. **Uncertainty budget:** For any headline number, enumerate the largest sources of uncertainty and their approximate magnitude:
      - Sampling uncertainty (CI width).
      - Measurement error (instrument precision).
      - Missing data bias (±X% based on sensitivity analysis).
      - Unmeasured confounding (worst-case ±Y% using E-value or subject-matter estimate).
   4. **Avoid overclaiming.** Use language like: "is associated with," "is correlated with," "our estimate suggests." Never use "causes," "proves," or "guarantees" unless the study design (randomized controlled trial, regression discontinuity, instrumental variable with strong assumptions) explicitly supports causal claims.
8. **Apply time-series-specific methods: STL decomposition, stationarity, autocorrelation, multiple comparison.**
   1. Decompose the series into trend + seasonal + residual components using STL/MSTL/X11.
   2. Test stationarity: ADF, KPSS. Difference or detrend if needed before applying inferential tests to residuals.
   3. Account for autocorrelation: Use Newey-West HAC standard errors or ARIMA errors; never apply a plain OLS t-test to a serially-correlated time series — you will get tiny spurious p-values.
   4. Anomaly detection on time-series: Use residual-based thresholds from STL + MAD, or Prophet + 95% CI; never static ±10% thresholds that ignore seasonality.
9. **Explicitly state causal inference limitations, including Simpson's paradox, unobserved confounders, and selection.**
   1. If the study design is observational (non-experimental), write a paragraph explicitly stating: "This is an observational analysis. The association reported may be confounded by unmeasured factors, and no causal claim is made. To support a causal interpretation, we would need: ___ (list: RCT, natural experiment, DiD, IV, RDD, extensive covariate adjustment + E-value assessment)."
   2. State the minimum strength an unmeasured confounder would need to have to fully explain the observed result (E-value for observational designs). If E-value is small (<1.5), caution strongly; if large (>3), observational interpretation is more robust.
   3. Document any Simpson's paradox encountered: show both aggregate and stratified results, explain why aggregation is misleading, identify the confounder responsible, and state which view should guide decisions.
10. **Write up the analysis with full transparency and caveats; enable reproducibility.**
    1. **Mandatory sections in the statistical report:**
       - Background + decision context (from BUSINESS-SPEC).
       - Research question, H₀, H₁, α, power, MDE, practical significance threshold.
       - Population, sampling frame, sample size, response rate (if applicable).
       - Descriptive statistics table, visualizations, distribution assessment.
       - Outlier, bias, missingness, and confounding assessment; Simpson's paradox check results.
       - Chosen methods and justification (why this test/regression rather than alternatives).
       - Full results: point estimates + 95% CIs + effect sizes (standardized + unstandardized) + p-values (both raw and multiple-comparison corrected).
       - Four-cell statistical vs practical significance classification.
       - Uncertainty budget.
       - Assumption checks (regression diagnostics, normality, homoscedasticity, etc.) with plots.
       - Limitations, including causal inference caveats.
       - Conclusion + actionable recommendation to the decision-maker (in plain English, no jargon).
    2. **Reproducibility artefacts:**
       - Version-controlled code / notebook with: pinned library versions, random seeds, input data checksums, output file checksums.
       - Supplement: raw test outputs from the stats library (one row per test), not just summarized results.
       - Sensitivity analyses: show how the headline result changes under: (a) outlier inclusion/exclusion, (b) different missing-data treatments, (c) different model specifications, (d) different α levels.

## Decision points

- **Step 2 (Large N, normality test rejects).** If N>100k and normality test p<1e-9 but QQ plot shows only minor deviation: rely on CLT for means, report CIs via parametric t-based (still valid under CLT) + bootstrap BCa to confirm, document the minor deviation.
- **Step 4.1 (Outlier disposition disputed between analyst and SME).** Escalate to the decision-maker: present both the analysis-with-outlier and analysis-without-outlier as a sensitivity analysis, and let the decision-maker choose which to act on. Document the choice.
- **Step 5.4 (Multiple tests).** If the dashboard or report contains >1 comparison or >1 regression coefficient, apply Benjamini-Hochberg FDR correction before reporting any result as "statistically significant." If >20 tests, consider reducing the scope of testing (pre-register the primary comparison and treat the rest as exploratory).
- **Step 6 (Hierarchical data).** If sites within regions, or trips within drivers, exist: mandatory mixed-effects / hierarchical model. Reject flat OLS; do not ignore clustering.
- **Step 7 (Stat sig but practically trivial).** If p<0.001 and Cohen's d=0.03, conclusion is "no action"; the effect is too small to be worth the cost of intervention. Do not let stakeholders interpret the p-value as evidence of a "large" effect.
- **Step 9 (Causal claim requested).** If the stakeholder asks "does X cause Y" and the design is observational, either (a) refuse the causal claim and propose a designed experiment or quasi-experimental method, or (b) attach a prominent disclaimer + E-value estimate; never present an observational association as causal without a study design to support it.

## Validation

- Research question, hypotheses, population, α, power, MDE, practical-significance threshold are all written down before any computation.
- Descriptive statistics are reported in a table for every variable; histogram + boxplot + QQ plot are produced for every continuous variable.
- Outliers are individually classified and dispositioned with SME input; no outlier is deleted silently.
- Missingness mechanism is stated per variable; analysis method matches (complete-case only acceptable for <10% MCAR/MAR).
- At least one Simpson's-paradox check (stratify analysis by each major plausible confounder and compare sign of effect with aggregate) has been performed.
- Sample size / power calculation is reported; if underpowered, this is stated explicitly in limitations.
- Every point estimate is accompanied by a 95% CI (or appropriate level). CI method matches the distribution.
- If >1 test/coefficient is reported, multiple comparison correction is applied and both raw and corrected p-values are shown.
- Effect sizes are reported in both standardized and unstandardized (business-unit) terms.
- Regression assumption diagnostics exist. VIFs reported; influential-point sensitivity analysis exists.
- Four-cell statistical vs practical significance matrix is populated for the headline result.
- Uncertainty budget enumerates top 3 uncertainty sources with rough magnitudes.
- Observational analyses carry a causal-inference limitations paragraph and an E-value or equivalent.
- Report contains all mandatory sections from step 10.1. Code is reproducible: pinned deps, seeds, input/output checksums on file.
- Stakeholder sign-off: the decision-maker confirms they understand the conclusion, the uncertainty, and the limitations.

## Expected outputs

- Statistical report markdown/PDF with all 10 mandatory sections, titled `STATISTICAL-ANALYSIS-<Name>-<Date>.md/pdf`.
- Descriptive statistics table CSV (`descriptives.csv`).
- Plots exported: `plots/distribution_<var>.png`, `plots/boxplot_<group_by_<var>.png`, `plots/qq_<var>.png`, `plots/scatter_<var_x>_<var_y>.png`, regression diagnostics plots.
- Statistical test results CSV: `tests/results.csv` with one row per test (method, variable, groups, statistic, df, p_raw, p_corrected, estimate, CI_low, CI_high, effect_size_std, effect_size_raw, assumption_check_pass).
- Regression outputs CSV: `regressions/<model_name>.csv` with coefficient, estimate, std_error, CI_low/high, z/t value, p, VIF, and sensitivity analysis columns.
- Sensitivity analysis workbook / markdown: `sensitivity.md` — headline result under outlier / missingness / model-spec variations.
- Code/notebook in git: pinned `requirements.lock`, seeds, checksum of input data, checksum of output files.
- Stakeholder sign-off email/minutes on file.
- Work tracking system updated: conclusion, recommendation, sign-off link.

## Common failure modes

1. **p-hacking / garden of forking paths.** Analysts try 12 filters, 3 outlier rules, 5 test variants, and report the one that came out p<0.05. Remedy: pre-register analysis plan (hypotheses, tests, correction method) in the work tracking system before data access; enforce via code review.
2. **Correlation presented as causation.** "Regions with higher marketing spend have higher sales → marketing causes sales" without considering the confounder that high-potential regions get more spend. Remedy: step 9 causal limitations paragraph mandatory for observational designs.
3. **Simpson's paradox missed.** Fleet B looks cheaper overall, but within every payload class Fleet A is cheaper, because Fleet B is assigned all the short-haul (inherently cheaper per TK) routes. Remedy: step 4.4 explicit stratification check before reporting aggregates.
4. **No multiple comparison correction on dashboards with 20 KPIs × 10 regions.** Users find "p < 0.05" somewhere by chance. Remedy: step 5.4 BH-FDR; only label pre-registered comparisons as "significant."
5. **Statistical significance without effect size / practical significance.** "p = 0.002, we should change fleet" but effect size = 0.02% (€0.0004/TKm) — far below the cost of changing fleet. Remedy: step 7 mandatory four-cell matrix before any recommendation.
6. **OLS applied to time-series data without accounting for autocorrelation.** Neat p=0.003 on a trend that any naive seasonal forecast would have predicted. Remedy: step 8 STL decomposition + Newey-West SEs or ARIMA errors.
7. **Outliers silently deleted.** "After cleaning, the effect is significant" — but cleaning dropped the 2% of rows that told the real story. Remedy: step 4.1 classification by SME, report count + disposition, sensitivity analysis with/without.
8. **Confusing sample with population.** The dataset has all trips (population); a p-value is meaningless because there is no sampling uncertainty — use effect size and practical significance only, and note the dataset is the population.
9. **CI interpretation reversed.** Stakeholders think "95% chance the true value is in this interval." Remedy: report in plain English and attach a one-paragraph interpretation note.
10. **Missingness ignored.** 30% missing on a key variable, complete-case analysis run. Result is biased if missingness is MNAR. Remedy: step 4.3 missingness mechanism classification + multiple imputation or flag in limitations.

## References to load

- `references/statistics-method-decision-tree.md` — Decision-tree flow chart: given the research question, variable types, groups, and design, which test/model to use (40 leaf nodes with references and worked examples).
- `references/descriptive-statistics-template.py` — Python function: takes a DataFrame + groupby columns → returns formatted LaTeX/markdown descriptives table plus auto-generates distribution, boxplot, QQ, scatter plots.
- `references/outlier-classification-sop.md` — Standard Operating Procedure: IQR fences, robust MAD-z, Cook's distance; SME classification matrix (error / legitimate extreme / mixed-population); disposition rules with mandatory documentation.
- `references/simpsons-paradox-detection.py` — Python function: given outcome, treatment, and list of candidate confounders → runs aggregate + stratified regressions, flags sign-flip or >50% coefficient-magnitude change, produces a report.
- `references/power-and-sample-size-calculator.xlsx` — Excel + Python versions: 2-sample t, 2-proportion, ANOVA, logistic regression; computes N given α, power, MDE, σ; includes lookup charts.
- `references/confidence-interval-methods-cheatsheet.md` — Per-distribution CI methods: t, bootstrap BCa, Clopper-Pearson, Poisson, robust regression HC3; Python/R code snippets.
- `references/multiple-comparison-correction-guide.md` — When to use Bonferroni vs Holm vs Benjamini-Hochberg vs Šidák; how to count the number of tests; FDR interpretation; worked Python example using statsmodels multipletests.
- `references/effect-size-interpretation-by-domain.md` — Default Cohen's d/η²/r thresholds with domain-specific adjustments (logistics cost, HR attrition, finance fraud, mining throughput) + reference benchmarks per domain.
- `references/regression-diagnostics-checklist.md` — 15-item checklist: residual plots, multicollinearity, VIF, Cook's distance, heteroscedasticity tests, RESET for functional form, link-test for logistic.
- `references/time-series-stl-and-anomaly-detection.py` — STL/MSTL decomposition + Newey-West regression + residual-based anomaly detection using MAD/Prophet CI, auto-generated anomaly report with annotated time-series chart.
- `references/causal-inference-limitations-template.md` — Mandatory fillable limitations paragraph for observational analyses, plus E-value calculator (Python function) and a catalogue of quasi-experimental methods (DiD, RDD, IV, PSM, synthetic control) with applicability thresholds.
- `references/statistical-report-template.md` — Fillable markdown template with all 10 mandatory sections from step 10.1, plus appendices for raw test output and sensitivity tables.
- `references/statistics-review-checklist.md` — 50-item pass/fail checklist covering every step.

## Completion criteria

- Report contains all mandatory sections; hypotheses, α, power, MDE, practical significance are pre-registered before computation.
- Descriptives + plots exist for every variable; distribution assumptions documented.
- Outliers classified by SME with dispositions reported; no silent deletion.
- Simpson's paradox check performed on headline result via stratification by every major confounder.
- CIs on every estimate; effect sizes reported (standardized + unstandardized).
- Multiple comparison correction applied if >1 test/coefficient.
- Four-cell matrix populated for headline result with explicit recommendation (Act / Do not act / Collect more data).
- Uncertainty budget states top 3 uncertainty sources.
- Observational analyses carry causal limitations paragraph + E-value or equivalent.
- Code is reproducible: pinned deps, seeds, checksums, all data cleaning/analysis steps versioned.
- Stakeholder sign-off on file confirming understanding of conclusion, uncertainty, and limitations.

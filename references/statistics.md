# Statistics Reference Guide (Analytics Engineering)

## When Used
Statistics is the **mathematics of uncertainty**. Apply statistical methods in analytics when you need to:
- Draw **reliable conclusions from samples** rather than full populations (surveys, A/B tests, sensor sub-samples)
- Quantify **uncertainty around metrics** (margin of error, confidence intervals)
- Compare groups (e.g., revenue after feature rollout vs control, treatment A vs treatment B)
- Detect **anomalies / outliers** in time-series or cohort data
- Quantify **relationships** between variables (correlation, regression, confounding)
- Justify **decisions with evidence** rather than anecdotes — "statistically significant" != "business meaningful"
- Validate assumptions before applying ML models (distribution shape, stationarity, class balance)

## When NOT Used
- **Pure descriptive reporting on full populations** — If you have 100% of the transactions, "France total revenue in January is €1.2M" is a fact, not a statistic. No CI needed.
- **Decisions where statistics cannot reduce uncertainty** — "Should we enter Market X?" is primarily a strategy call; stats support, don't decide.
- **Small samples (< 30 observations, no CLT)** with unknown distribution — use non-parametric tests (Mann–Whitney U) or better, gather more data.
- **Data with massive leakage or selection bias** — No statistical test can rescue a badly collected dataset; garbage in, garbage out.
- **A/B tests without proper randomization and pre-power calculation** — Running a test until p<0.05 ("p-hacking") is unethical and produces false results.
- **Correlation used as causation evidence without causal design** (see Simpson's paradox and confounding).

---

## Common Mistakes

1. **Confusing statistical significance with practical (business) significance.** A tiny p-value (p<0.0001) with an effect size of €0.03 per user means nothing for the business; report both p and effect.
2. **p-hacking / multiple comparisons without correction.** Running 20 tests at α=0.05 guarantees, on average, **1 false positive**. Use Bonferroni correction (α/n), Šidák, FDR (Benjamini-Hochberg) or Bayesian methods.
3. **Confusing correlation (r) with causation.** `ice_cream_sales` ↑ is correlated with `drowning_deaths` ↑; both are driven by temperature (confounder). No amount of r fixes this.
4. **Reporting a mean without dispersion.** "Average order value is €78" — is this €78 ± €2 or €78 ± €400? Always include SD/IQR/quantiles.
5. **Using mean on heavily skewed data.** Revenue per customer is heavily right-skewed (most spend €10, one spends €1M). Mean is pulled to €78 while median is €32 → **misleading reporting**. Use median + IQR or log-transform.
6. **Confidence interval interpreted as "there is a 95% probability the true mean lies in this interval."** Frequentist CIs are not Bayesian credible intervals; correct interpretation: "If we repeated this experiment infinitely, 95% of the intervals constructed this way would contain the true parameter."
7. **Confusing p-value with the probability H0 is true.** p=0.04 does NOT mean "4% chance H0 is true." p=P(data or more extreme | H0 true). Not P(H0|data).
8. **Using parametric tests (t-test, ANOVA) when assumptions are violated** (normality, homoscedasticity, independence). → Use non-parametric (Wilcoxon, Kruskal-Wallis, permutation) or bootstrap.
9. **Simpson's paradox ignored:** A treatment appears beneficial overall, but harmful in every subgroup (due to a confounding variable). Disaggregate before concluding.
10. **Using linear regression on non-stationary time-series** → spurious correlation (GDP vs number of PhDs both trend upward over time → high r², meaningless relationship).
11. **Accepting the null hypothesis.** "p > 0.05, so there is no effect" is wrong. Correct: "We failed to reject H0 at this alpha; may be due to low power."
12. **Outliers dropped arbitrarily.** If an outlier is a genuine data point (not data entry error), it represents real information. Use robust methods (median, quantile regression) instead of deletion.

---

## Trade-offs

| Decision | Advantages | Disadvantages |
|----------|-----------|---------------|
| **Frequentist (p-values, CIs) vs Bayesian (credible intervals, posterior)** | Frequentist: universally taught, no prior needed, `scipy.stats` one-liner. Bayesian: naturally encodes prior knowledge; gives direct P(H|data) statement; multiple comparisons handled via hierarchical models. | Frequentist: confusing interpretation; strict α rules; no prior. Bayesian: computation heavier; requires prior specification; requires domain expertise. |
| **Parametric test (t, ANOVA) vs non-parametric (Wilcoxon, permutation)** | Parametric: more power when assumptions hold. Non-parametric: no normality/homoscedasticity assumption; robust to outliers. | Parametric: Type I error skyrockets if violated. Non-parametric: lower power when parametric assumptions *are* true. |
| **Mean vs Median** | Mean: uses every data point; mathematically convenient for linear models. Median: robust to outliers, more interpretable on skewed data. | Mean: distorted by skews/outliers. Median: loses information, mathematically awkward in models. |
| **Pearson r vs Spearman ρ vs Kendall τ** | Pearson: measures linear correlation, interpretable as R² in linear regression. Spearman: rank-based, captures monotonic nonlinear relationships. Kendall: handles ties + small N better. | Pearson: wildly wrong on non-linear. Spearman/Kendall: no linear interpretability. |
| **Simple linear regression vs Multivariate regression** | Simple: one predictor, easy to explain. Multivariate: controls for confounders → less biased estimate of main coefficient. | Simple: biased by confounding. Multivariate: multicollinearity risks; overfitting without regularization; harder to interpret. |
| **Cross-sectional vs Panel/longitudinal data** | Cross-sectional: one observation per entity; cheapest to collect. Panel: same entity over time → fixed/random effects; control for unobserved heterogeneity. | Cross-sectional: can't account for entity-level omitted variables. Panel: harder to collect; attrition bias. |
| **α=0.05 vs α=0.005** | α=0.05: field convention; larger n needed to reach same power vs α=0.005. α=0.005: reduces false-positive rate; better for decisions with big consequences. | α=0.05: 5% false-positive rate → if you run 20 tests, expect 1 FP. α=0.005: requires more sample (higher power budget); may block legitimate discoveries. |
| **Classical ANOVA vs Mixed-effects / Hierarchical models** | ANOVA: simple, ubiquitous F-tests. Mixed: handles group structure (students within classrooms within schools); borrows strength across groups. | ANOVA: broken if groups are unbalanced or have nested structure. Mixed: harder to explain to stakeholders; requires ML/REML convergence. |

---

## Good Implementation

### Descriptive Statistics Workflow

```python
import numpy as np
import pandas as pd
from scipy import stats

def describe_numeric(x: pd.Series) -> dict:
    x_clean = x.dropna()
    q1, med, q3 = np.quantile(x_clean, [0.25, 0.5, 0.75])
    return {
        "n":              len(x_clean),
        "missing_pct":    x.isna().mean() * 100,
        "mean":           x_clean.mean(),
        "sd":             x_clean.std(),
        "min":            x_clean.min(),
        "q1":             q1,
        "median":         med,
        "q3":             q3,
        "max":            x_clean.max(),
        "iqr":            q3 - q1,
        "skew":           x_clean.skew(),       # >1 right-skewed, <-1 left-skewed
        "kurtosis":       x_clean.kurtosis(),   # excess kurtosis (0 = normal)
        "outlier_count":  int(  # Tukey fence
            (x_clean < (q1 - 1.5*(q3-q1))) |
            (x_clean > (q3 + 1.5*(q3-q1)))
        ).sum(),
    }
```

### Confidence Intervals (Two-Ways)

```python
# (1) Analytical: t-interval (N < 30 or σ unknown)
def t_ci(x: pd.Series, conf=0.95):
    x = x.dropna()
    mean, se = x.mean(), stats.sem(x)
    h = se * stats.t.ppf((1 + conf) / 2, df=len(x) - 1)
    return mean, mean - h, mean + h

# (2) Bootstrap (ANY distribution, works for medians/percentiles too)
def bootstrap_ci(x: pd.Series, stat_fn=np.median, n_boot=10_000, conf=0.95, seed=42):
    rng = np.random.default_rng(seed)
    x = x.dropna().to_numpy()
    draws = np.array([stat_fn(rng.choice(x, size=len(x))) for _ in range(n_boot)])
    alpha = (1 - conf) / 2
    return stat_fn(x), np.quantile(draws, alpha), np.quantile(draws, 1 - alpha)

# Example: A/B test revenue per user
np.random.seed(0)
ctrl = np.random.lognormal(mean=3.4, sigma=0.9, size=10_000)  # skewed
treat= np.random.lognormal(mean=3.45, sigma=0.9, size=10_000)

median_ctrl, lo, hi = bootstrap_ci(ctrl, stat_fn=np.median)
print(f"Control median revenue: €{median_ctrl:.2f} (95% CI €{lo:.2f}–€{hi:.2f})")
```

### Hypothesis Testing — A/B Test

```python
# Continuous metric (revenue/user), skewed → Welch's t-test or Mann-Whitney U
t_stat, p_t = stats.ttest_ind(treat, ctrl, equal_var=False, alternative="two-sided")
u_stat, p_u = stats.mannwhitneyu(treat, ctrl, alternative="two-sided")

# Binary metric (conversion rate) → two-proportion z-test or Fisher
conversions_ctrl = np.random.binomial(10_000, p=0.03)
conversions_treat= np.random.binomial(10_000, p=0.035)
z_stat, p_z = stats.proportions_ztest(
    count=[conversions_treat, conversions_ctrl],
    nobs=[10_000, 10_000],
    alternative="larger"
)

# ALWAYS report:
delta_abs = (treat.mean() - ctrl.mean())
delta_rel = delta_abs / ctrl.mean() * 100
print(f"Δ Revenue: €{delta_abs:.2f} ({delta_rel:+.1f}%) | Welch p={p_t:.3f} | MWU p={p_u:.3f}")
# → "Δ Revenue: €2.35 (+4.2%) | Welch p=0.004 | MWU p=0.006"
```

### Multiple Comparisons Correction

```python
from statsmodels.stats.multitest import multipletests

p_values = [0.001, 0.012, 0.031, 0.048, 0.071, 0.11]
reject, p_corrected, _, _ = multipletests(p_values, alpha=0.05, method="fdr_bh")
# Benjamini-Hochberg (FDR) preferred for exploratory / large N tests
# Use method="bonferroni" for strict FWER control when false-positives are very costly
for p_raw, p_adj, r in zip(p_values, p_corrected, reject):
    print(f"p={p_raw:.3f} → adjusted p={p_adj:.3f} reject={r}")
```

### Linear Regression (Controlling Confounders)

```python
import statsmodels.formula.api as smf

# Dataset: revenue ~ treatment + customer_tenure + country + segment
model = smf.ols(
    formula="revenue ~ treatment + tenure + C(country) + C(segment)",
    data=df
).fit(cov_type="HC3")  # Heteroskedasticity-robust SEs (White/Eicker-White)
print(model.summary())

# Key outputs to read:
#  - treatment coef: +€X, holding tenure/country/segment constant
#  - P>|t|: 2-tailed p-value for treatment effect
#  - R²: % of variance explained (don't chase high R²; use AIC/BIC)
#  - Condition Number: >30 = multicollinearity; investigate VIF
```

### ANOVA (3+ Groups)

```python
# One-way: revenue across 3 marketing channels (email, paid, social)
groups = [df_channel.email, df_channel.paid, df_channel.social]
F_stat, p = stats.f_oneway(*groups)
# If p < α, follow up with Tukey HSD for pairwise comparisons
from statsmodels.stats.multicomp import pairwise_tukeyhsd
tukey = pairwise_tukeyhsd(endog=df.revenue, groups=df.channel, alpha=0.05)
print(tukey)
```

### Chi-Squared (Categorical Independence)

```python
# Test: churn status (stay/leave) independent of plan_type (basic/pro/enterprise)?
contingency = pd.crosstab(df.churn_label, df.plan_type)
chi2, p, dof, expected = stats.chi2_contingency(contingency)
# Before running: confirm 80%+ of expected cell counts ≥ 5
# If not → Fisher's exact test (2×2) or combine categories
```

### Causal Inference in Observational Data (When RCT isn't Possible)

```python
# Propensity score matching (conceptual): match each treated user to an untreated
# user with identical propensity to be treated (given observables)
from causalinference import CausalModel

cm = CausalModel(
    Y=df.revenue.values,          # outcome
    D=df.treatment.values,        # 0/1 assignment
    X=df[["tenure", "country_id", "segment_id"]].values  # observables
)
cm.est_via_matching(matches=1, bias_adj=True)
print(cm.estimates)  # ATT (average treatment effect on the treated)
# Caveat: only controls for OBSERVED confounders. If unobserved confounders exist,
# use: Difference-in-Differences, Regression Discontinuity, Instrumental Variables.
```

---

## Concepts Deep-Dive

### Effect Size — The Missing Piece
p-values conflate *magnitude* with *sample size*. With n=1,000,000, a €0.02 difference is highly significant. Report:
- **Absolute difference** (e.g., +€2.35 per user)
- **Relative difference** (+4.2% over control)
- **Standardised effect size** (Cohen's d = (μ1−μ2)/σ_pooled): 0.2 = small, 0.5 = medium, 0.8 = large

### Sampling & Central Limit Theorem (CLT)
- Simple random sample (SRS) every time if you can; stratified sampling by known subgroups ensures cell sizes; cluster sampling is cheaper but inflates variance (need cluster-robust SEs).
- **CLT**: The sampling distribution of the *sample mean* becomes normal as n grows, *regardless of the population distribution*. Rule of thumb: n≥30 for moderate skew, n≥100 for very heavy tailed. If you have the *full population*, you don't need CLT or CIs.

### Uncertainty, Bias, Outliers
- **Bias** is systematic error (bad sampling frame, leading survey questions, omitted variable). You can't fix bias with more n. Detect via stratified comparisons, domain knowledge, causal diagrams.
- **Outliers** are extreme but valid observations. Investigate first (data entry? genuine event?). Winsorize (cap at p01/p99) or use robust regression (Huber, RANSAC) instead of deleting.
- **Uncertainty** is random noise that decreases with √n; budget your sample size with power analysis BEFORE running the test:

```python
from statsmodels.stats.power import TTestIndPower
# How many users/group to detect +3% lift (d=0.1, small effect) at 80% power, α=0.05?
analysis = TTestIndPower()
n = analysis.solve_power(effect_size=0.1, alpha=0.05, power=0.8, ratio=1.0)
print(f"N required per group ≈ {int(np.ceil(n)):,}")  # ≈ 1571 per group
```

### Simpson's Paradox
**Classic:** Overall treatment seems to reduce survival, but within every age stratum treatment *increases* survival. Cause: confounding variable (age) drives both treatment assignment AND outcome. **Rule:** Always disaggregate by plausible confounders before concluding. Draw a Directed Acyclic Graph (DAG) with domain experts to identify which variables to condition on.

### Time-Series Specifics
- **Stationarity**: mean/variance/autocorrelation constant over time. Test with Augmented Dickey-Fuller (`statsmodels.tsa.stattools.adfuller`). If non-stationary, difference or use SARIMA/Prophet that handle trends/seasonality.
- **Autocorrelation**: Residuals correlated with lagged self → use Newey-West SEs or ARIMA errors, not OLS SEs (which are too optimistic).
- **Seasonality**: Weekly + monthly + yearly cycles in retail data → Fourier features or STL decomposition.

---

## How to Test Statistical Analyses (Validation Checklist)

1. **Synthetic data test** — Generate data with KNOWN effect size; does the method recover it within CI? If not, bug in pipeline.
2. **Power vs n curve** — Plot detected effect vs sample size for 80% power; ensure you collected enough data.
3. **Sensitivity to assumptions** — Parametric test + non-parametric alternative on same data; do they agree? (If p=0.02 by t-test but p=0.15 by Wilcoxon → investigate distribution shape.)
4. **Leave-one-out / Jackknife** — Does the coefficient change dramatically if you drop one subgroup? Stability check.
5. **Outlier robustness** — Winsorize 1% tails; re-run; does conclusion change?
6. **Collinearity diagnostics** — VIF > 10 → drop or combine predictors.
7. **Regression residual checks** — Residuals: Q-Q plot (normality), residuals vs fitted (heteroskedasticity → use HC3 SEs), residual vs time (autocorrelation).
8. **False-positive control** — Permutation test: scramble treatment assignment; do 5% of permutations still give p<0.05? If >20%, method is anti-conservative.

---

## Performance Behavior

| Method | Complexity | Notes |
|--------|-----------|-------|
| Descriptive statistics (mean, quantile) | O(n) one-pass; sort-based quantile O(n log n) | Use t-digest / sketching for distributed 100M+ rows |
| Confidence interval (analytical) | O(n) | Very fast |
| Bootstrap (10k resamples, size n) | O(n × n_boot) | Parallelise; use 1000–10000; for big n use bca (bias-corrected) |
| Linear regression OLS (n rows, k predictors) | O(n · k²) | k fixed → linear in n; use statsmodels for small data, sklearn/GradientBoosting for big sparse data |
| Logistic/GLM (IRLS) | O(n · k²) per iter | 5–20 iterations typical |
| Random Forest / XGBoost inference | O(n_estimators × depth × n) | Much more accurate on tabular but 100× OLS compute |
| ANOVA | O(groups × n log n) | Fast |
| Permutation test (n_boot) | O(n × n_boot) | More accurate than parametric but 100× slower |
| Bayesian MCMC (NUTS/HMC) | O(n × draws × k × tree_depth) | 1000–10000 draws; parallel chains; most compute-heavy |

---

## What to Inspect First (Weird Results)

1. **Data collection / sampling methodology.** Is the sample representative? Non-response bias? Selection bias (e.g., only users who opted in)?
2. **Missing data patterns.** Is missingness correlated with treatment or outcome? (MCAR vs MAR vs MNAR). Use Little's MCAR test; impute cautiously.
3. **Distributions — is the variable heavily skewed?** Switch from mean to median, from t-test to MWU/bootstrap.
4. **Confounders / DAG:** Did you condition on a collider? Or FAIL to condition on a common cause? → Wrong sign on coefficient (Simpson/Berkson).
5. **Multiple comparisons.** You ran 40 subgroup tests. Is the one "significant" result just a false positive? Correct for FDR.
6. **Assumptions check.** Normality: Shapiro-Wilk / Q-Q. Homoscedasticity: Breusch-Pagan / Levene. Independence of errors: Durbin-Watson. If violated → robust methods.
7. **p-hacking / forking paths.** Were 10 different outcome variables tried? 5 exclusion criteria? Report everything, pre-register.
8. **Sample size.** Tiny n (n=20) failing to reject H0 → low power, not "no effect". Run post-hoc power.
9. **Perfect separation in logistic regression.** One category predicts 100% outcome → inflated coefficients; use Firth logistic regression.
10. **Measurement error.** A/B test on revenue where 20% of revenue is attributed incorrectly → huge attenuation bias; validate measurement first.

---

## Common Misuse of p-values (ASA Principles)

1. **p-values do not measure the probability that the studied hypothesis is true**, or the probability that the data were produced by random chance alone.
2. **p-values do not measure the size of an effect** or the importance of a result.
3. **By themselves, p-values do not provide a good measure of evidence** regarding a model or hypothesis.
4. **A p-value, or statistical significance, does not measure the size of an effect.**
5. **Never conclude "no difference" or "no association"** just because p > α.
6. **Proper inference requires full reporting and transparency.** Don't cherry-pick significant results.
7. **A p-value does not provide a good measure of evidence** by itself. Use it alongside effect size, CI, prior domain knowledge, replication.

**Practical heuristic:** Always print 3 numbers for every comparison: `Δ = +X% | 95% CI [Y%, Z%] | p = 0.XXX`

# Data Science & Machine Learning Reference Guide (Analytics-Focused)

## When Used
ML/data science is warranted **only when simple rules + descriptive analytics cannot solve the problem**, and:
- You need to **predict** an unknown outcome (churn, demand forecasting, fraud, lead scoring, price elasticity)
- Patterns are **non-linear and high-dimensional** (too many interacting factors for an analyst to hand-write rules)
- The decision repeats at **scale** (scoring 1M customers/month automatically vs. manual review of 20 cases)
- You have **enough labelled historical data** (generally ≥1000 labelled examples for tabular; more for images/text)
- The **cost of being wrong is acceptable** and measurable; you can tolerate and manage model error
- A baseline (rule-based, last-value, average) is not accurate enough, and you have quantified the *accuracy gap*

## When NOT Used
- **A simple rule / deterministic logic would work** — "Churn = no login in 90 days" is usually good enough. Always establish a baseline first.
- **Descriptive / diagnostic question** — "Why did sales drop last week?" → use SQL + statistics, not ML.
- **You have <100 labelled examples** — overfitting is guaranteed; collect more data or use rule-based + expert judgement.
- **Prediction is legally/ethically high-stakes without auditability** — credit scoring, recidivism, medical diagnosis without explainability + regulatory review.
- **The environment changes faster than you can retrain** — a model trained on 2019 customer behaviour is useless in 2025 if the business pivoted.
- **No feedback loop exists** — if you never know whether a prediction was actually correct, you can't validate or improve.
- **Stakeholders cannot consume probability scores / rankings** — if the output can't be integrated into a dashboard, workflow, or decision, don't build it.

---

## Common Mistakes

1. **No baseline.** "My model has AUC 0.78 — great!" Meanwhile the "always predict majority class" baseline already has 0.76 accuracy. Build baselines before any ML.
2. **Data leakage (biggest ML failure cause).**
   - Using a feature that would not be available at prediction time (e.g., `days_to_churn` as a feature when predicting churn).
   - Scaling / imputing using statistics computed across full dataset *before* train/test split.
   - Including columns derived from the label in features (e.g., `total_lifetime_value` column that includes future revenue when predicting future revenue).
   - Time leakage: random split on time-series data → model trains on "future" rows, "predicts" past.
3. **Accuracy as metric for imbalanced data** (fraud, churn, click prediction). 99% class 0 → 99% accuracy from predicting "0" is useless. Use precision, recall, F1, AUC-ROC, AUC-PR, calibration.
4. **Hyperparameter tuning on the test set / data leakage during CV.** Tuning 500 hyperparameter combos on test set = overfit test set like a glove. Keep a *hold-out* or use nested CV.
5. **Chasing model complexity.** Deep learning → XGBoost → Random Forest → Logistic Regression on a 5k-row tabular dataset; LR often wins in reliability, speed, and interpretability. *Always justify complexity.*
6. **Ignoring calibration.** Predicted probability 0.8 means, across 100 such predictions, ~80 should actually be positive. Uncalibrated models give wrong expected values → bad financial decisions.
7. **Single train/test split on small data.** N=500 and a single 80/20 split → your metric varies ±0.1 depending on the split. Use 5- or 10-fold stratified CV and report mean ± SD.
8. **Training then deploying without monitoring drift.** Models decay. If you put a model in production without PSI/CSI drift monitoring + retraining cadence, it's silently wrong within 6–18 months.
9. **SHAP/LIME afterthought.** You deploy a black-box model then someone asks "why did this customer get flagged as fraud?" No way to answer. Build explainability from day one.
10. **Target leakage in data joins.** You join an `orders` table that contains orders *after* the churn-event date to the training set.
11. **Not enough "negative engineering."** Half the work of a good tabular model is filtering bad data, handling rare categories, clipping outliers, smart imputation, time-windowed aggregations (not just `mean()` of entire history).
12. **Evaluating clustering (k-means, DBSCAN) with no ground truth.** Silhouette score + inertia are poor proxies for business value. Always evaluate against a business metric (e.g., "does cluster 3 have 3× higher churn?").

---

## Trade-offs

| Decision | Advantages | Disadvantages |
|----------|-----------|---------------|
| **Rule-based baseline → Gradient Boosted Tree → DL** | Baseline: interpretable, debuggable, no data required. GBT (XGBoost/LightGBM/CatBoost): state-of-art on tabular, handles mixed types, fast to train. DL: handles unstructured (images, text, audio); captures interactions. | DL: 10× more data/compute; black-box; overfitting risk on small tabular; harder explainability. GBT: can overfit; hyperparameters matter. Baseline: limited accuracy ceiling. |
| **Interpretability (Linear, GBT + SHAP) vs Black Box (DL, Stacking)** | Interpretable: auditable, easier stakeholder buy-in, debuggable. Black-box: sometimes +2–5% accuracy. | Black-box: 90% of production issues (drift, wrong segment predictions, bias) are harder to diagnose; regulatory risk. Usually not worth the trade unless accuracy gap is quantified + meaningful. |
| **Hold-out validation vs k-fold CV vs nested CV** | Hold-out: simplest, fastest. k-fold: better metric estimate on small data. Nested CV: unbiased estimate when doing hyperparameter tuning. | Hold-out: single split noise (large CI). k-fold: k× slower. Nested CV: k₁ × k₂ × n_hyper trials → slow. |
| **AUC-ROC vs AUC-PR (imbalanced classes)** | AUC-ROC: standard, well-understood, invariant to class ratio. AUC-PR: better reflects precision/recall trade-off when classes imbalanced (e.g., fraud 0.1%). | AUC-ROC on 99.9% neg data: optimistic (classifier predicting all neg = 0.5 AUC ROC → appears "not bad"). Use AUC-PR whenever imbalance > 10:1. |
| **Online learning vs Batch retraining** | Online: adapts instantly to drift. Batch: simpler pipeline, reproducible, easier validation. | Online: catastrophic drift if fed bad data; harder A/B. Batch: stale during drift events. Hybrid: batch weekly + streaming features. |
| **Custom models vs pre-built SaaS (Vertex AI, Azure ML AutoML)** | Custom: full control, exact feature engineering, cost transparency. SaaS: faster POC, managed serving. | SaaS: expensive at scale, vendor lock-in, limited debugging. Custom: needs ML engineering + MLOps. |
| **Regression vs Classification (Threshold)** | Regression predicts raw number (revenue, demand). Classification (with threshold) gives a binary decision. | Regression: metrics MAPE, MAE, RMSE; sensitive to outliers (use MAPE only for >0 values). Classification: threshold-tuning directly ties to business cost (FN cost vs FP cost). |
| **Single model vs Ensemble / Stacking** | Ensemble: usually +1–3% performance, more robust. Single model: 10× simpler to debug, deploy, explain. | Ensembles add complexity and compute; marginal gain 0.5% is rarely worth it in production. |

---

## Standard Workflow (CRISP-DM + Modern MLOps)

```
1. Business Understanding
   └── Define: prediction task, what decision uses the score? cost per FN/FP? baseline accuracy needed?
2. Data Understanding
   └── EDA, distribution checks, label quality, missingness, join cardinality, leakage audit.
3. Data Preparation
   └── Label definition window (prediction_point_date → label_window 30–90d later)
       Feature engineering with strict time windows, no look-ahead.
       Train-valid-test split (time-based, NOT random, for any sequential problem).
4. Modeling
   └── Baseline → Linear → Tree → Ensemble.
       Hyperparameter tuning via Optuna/Hyperopt on validation.
       Cross-validation with correct resampling strategy (time-series split if needed).
5. Evaluation
   └── Metrics + business KPI impact, calibration, fairness across segments,
       error analysis (which subgroups perform poorly?), SHAP global + local.
6. Deployment
   └── Batch scoring or online serving, model registry + versioning,
       Shadow mode (score but don't act) for 2+ weeks before cutover.
7. Monitoring & Maintenance
   └── Data drift (PSI), Prediction drift, Performance drift, Retraining cadence.
```

**Mantra: 80% of the work is steps 1–3. Not 4.**

---

## Good Implementation

### Train/Val/Test Split (Time-Based, No Leakage)

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, TimeSeriesSplit

def split_temporal(df: pd.DataFrame,
                   date_col: str = "as_of_date",
                   train_end: str = "2023-12-31",
                   val_end:   str = "2024-06-30") -> tuple[pd.DataFrame, ...]:
    """Chronological split. TRAIN: before train_end; VAL: train_end..val_end; TEST: after val_end.
    NEVER use random split on customer behaviour / time-series tasks."""
    train_mask = df[date_col] < train_end
    val_mask   = (df[date_col] >= train_end) & (df[date_col] < val_end)
    test_mask  = df[date_col] >= val_end
    return df.loc[train_mask], df.loc[val_mask], df.loc[test_mask]

def time_series_cv(n_splits=5, max_train_size=None):
    return TimeSeriesSplit(n_splits=n_splits, max_train_size=max_train_size, gap=7)  # 7-day gap to avoid label leakage
```

### Label + Feature Window (Churn Example)

```
Prediction as-of date: 1st of each month (e.g., 2024-01-01)
  │
  ├── Feature window: [-180d, -1d] relative to as-of
  │      → login counts, revenue, ticket count, email open rate, product usage
  │      (must be 100% observable by 2023-12-31 inclusive)
  │
  └── Label window: [+30d, +120d] relative to as-of
         → churn = 1 if no login in this 90-day window.
            Label is "future" from prediction date's perspective.
```

### Baseline Model (ALWAYS Build This First)

```python
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score

baseline_clf = DummyClassifier(strategy="stratified", random_state=42)
baseline_clf.fit(X_train, y_train)
y_baseline_pred = baseline_clf.predict_proba(X_val)[:,1]

print(f"Baseline (stratified random) AUC-ROC: {roc_auc_score(y_val, y_baseline_pred):.3f}")
print(f"Baseline (stratified random) AUC-PR : {average_precision_score(y_val, y_baseline_pred):.3f}")

# Rule-based baseline 2: "churn if no login in last 60 days"
rule_baseline = (X_val["login_count_last_60d"] == 0).astype(int)
print(f"Rule-based F1 @ default threshold: {f1_score(y_val, rule_baseline):.3f}")
```

### Feature Engineering (Windowed Aggregations — NO LOOK-AHEAD)

```python
def build_user_features(df_events: pd.DataFrame, as_of_dates: pd.DatetimeIndex) -> pd.DataFrame:
    """For each as_of_date, aggregate events [180d prior, 1 day prior] (strictly historical)."""
    features = []
    for as_of in as_of_dates:
        window_start = as_of - pd.Timedelta(days=180)
        window_end   = as_of - pd.Timedelta(days=1)
        in_window = df_events[(df_events.event_date >= window_start) &
                              (df_events.event_date <= window_end)]
        agg = in_window.groupby("user_id").agg(
            login_count_last_180d    = ("event_id", "count"),
            login_count_last_30d     = ("event_date", lambda s: (s >= as_of - pd.Timedelta(days=30)).sum()),
            days_since_last_login    = ("event_date", lambda s: (as_of - s.max()).days if len(s) else np.inf),
            total_spend_last_180d    = ("spend_amount", "sum"),
            support_tickets_count    = ("event_type", lambda s: (s == "support_ticket").sum()),
        )
        agg["as_of_date"] = as_of
        features.append(agg.reset_index())
    return pd.concat(features, ignore_index=True)
```

### Training Loop with Cross-Validation + Nested Tuning

```python
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
import optuna

# -- Step 1: Define preprocessor (scaling NEVER needed for tree models; only ordinal encode categoricals)
numeric_features = X_train.select_dtypes(include=[np.number]).columns.tolist()
categorical_features = X_train.select_dtypes(exclude=[np.number]).columns.tolist()

preprocessor = ColumnTransformer(
    transformers=[
        ("num", SimpleImputer(strategy="median"), numeric_features),
        ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), categorical_features),
    ]
)

def objective(trial: optuna.Trial) -> float:
    params = dict(
        n_estimators      = trial.suggest_int("n_estimators", 200, 2000),
        learning_rate     = trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        num_leaves        = trial.suggest_int("num_leaves", 8, 256),
        min_child_samples = trial.suggest_int("min_child_samples", 5, 500),
        reg_alpha         = trial.suggest_float("reg_alpha", 1e-8, 10, log=True),
        reg_lambda        = trial.suggest_float("reg_lambda", 1e-8, 10, log=True),
        random_state      = 42,
        verbose           = -1,
    )
    clf = Pipeline([("pre", preprocessor), ("lgb", lgb.LGBMClassifier(**params))])
    cv = TimeSeriesSplit(n_splits=5, gap=7)
    aucs = []
    for tr_idx, va_idx in cv.split(X_train):
        X_tr, X_va = X_train.iloc[tr_idx], X_train.iloc[va_idx]
        y_tr, y_va = y_train.iloc[tr_idx], y_train.iloc[va_idx]
        clf.fit(X_tr, y_tr)
        preds = clf.predict_proba(X_va)[:,1]
        aucs.append(roc_auc_score(y_va, preds))
    return float(np.mean(aucs))

study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=40)

final_model = Pipeline([("pre", preprocessor),
                        ("lgb", lgb.LGBMClassifier(**study.best_params, random_state=42, verbose=-1))])
final_model.fit(X_train, y_train)

# Evaluate ONLY once on TEST (after all tuning/decision)
y_val_pred  = final_model.predict_proba(X_val)[:,1]
y_test_pred = final_model.predict_proba(X_test)[:,1]
print(f"VAL  AUC-ROC: {roc_auc_score(y_val, y_val_pred):.3f}  AUC-PR: {average_precision_score(y_val, y_val_pred):.3f}")
print(f"TEST AUC-ROC: {roc_auc_score(y_test, y_test_pred):.3f} AUC-PR: {average_precision_score(y_test, y_test_pred):.3f}")
```

### Threshold Tuning with Business Costs

```python
def expected_profit(y_true, y_prob, cost_fp=10, cost_fn=100):
    """Treat each FP (intervene wrongly) as cost_fp €; each FN (missed churn) as cost_fn €."""
    best_p, best_cost = 0.5, np.inf
    for p in np.linspace(0.01, 0.99, 99):
        y_pred = (y_prob >= p).astype(int)
        fp = ((y_pred == 1) & (y_true == 0)).sum()
        fn = ((y_pred == 0) & (y_true == 1)).sum()
        cost = fp * cost_fp + fn * cost_fn
        if cost < best_cost:
            best_cost, best_p = cost, p
    return best_p, best_cost

opt_threshold, _ = expected_profit(y_val, y_val_pred, cost_fp=10, cost_fn=200)
y_test_pred_label = (y_test_pred >= opt_threshold).astype(int)
```

### Calibration Check + Fix

```python
from sklearn.calibration import CalibratedClassifierCV, CalibrationDisplay

# 1. Visually check reliability diagram BEFORE deploying
CalibrationDisplay.from_predictions(y_val, y_val_pred, n_bins=10, name="Raw LGBM")
# If sigmoid shape (underconfident) or diagonal mismatch:
calibrated = CalibratedClassifierCV(final_model, method="isotonic", cv="prefit")
calibrated.fit(X_val, y_val)  # Fit calibrator on VALIDATION, never TRAIN (avoids overfit)
y_test_cal = calibrated.predict_proba(X_test)[:,1]
```

### Explainability (SHAP)

```python
import shap

explainer = shap.TreeExplainer(final_model.named_steps["lgb"])
X_val_preprocessed = final_model.named_steps["pre"].transform(X_val)
shap_values = explainer.shap_values(X_val_preprocessed)

# Global feature importance plot
shap.summary_plot(shap_values, X_val_preprocessed,
                  feature_names=numeric_features + categorical_features,
                  max_display=15)

# Local explanation for single prediction
shap.force_plot(explainer.expected_value, shap_values[42],
                feature_names=numeric_features + categorical_features)
```

### Drift Monitoring (Production)

```python
def psi(expected: np.ndarray, actual: np.ndarray, bins=10) -> float:
    """Population Stability Index: <0.1 low drift, 0.1–0.25 moderate, >0.25 high."""
    breakpoints = np.linspace(0, 100, bins + 1)
    cuts = np.percentile(expected, breakpoints)
    cuts = np.unique(cuts)
    expected_counts = np.histogram(expected, bins=cuts)[0] / len(expected)
    actual_counts   = np.histogram(actual,   bins=cuts)[0] / len(actual)
    expected_counts = np.where(expected_counts == 0, 1e-6, expected_counts)
    actual_counts   = np.where(actual_counts   == 0, 1e-6, actual_counts)
    return float(np.sum((actual_counts - expected_counts) * np.log(actual_counts / expected_counts)))

# Weekly check: compare today's production feature distribution to training distribution
for col in numeric_features:
    drift_score = psi(X_train[col].dropna().values, X_production_this_week[col].dropna().values)
    if drift_score > 0.25:
        raise Warning(f"High drift detected on {col}: PSI={drift_score:.3f} → retrain suggested")
```

---

## Task-Typical Metrics

| Task | Primary Metrics | Baseline Benchmark |
|------|----------------|-------------------|
| **Binary classification (balanced)** | AUC-ROC, F1, accuracy, confusion matrix | ~50% AUC (random), ~majority class% accuracy |
| **Binary classification (imbalanced 10:1 or worse)** | AUC-PR, precision@k, recall@k, F_beta (β>1 for recall priority), calibration | AUC-PR = prevalence; precision@k = random pick rate |
| **Multi-class classification** | Macro/micro F1, per-class confusion matrix, top-k accuracy | 1/n_classes random accuracy |
| **Regression** | MAE, RMSE, MAPE (only for values ≥0), R² (be careful: R² can be negative) | Naive: predict training mean, or last value for time-series |
| **Time-series forecasting** | MASE (mean absolute scaled error vs naive), WAPE, coverage of prediction intervals | Seasonal naive = value from same period last cycle |
| **Ranking / recommendations** | NDCG@k, MAP@k, precision@k, recall@k | Random order → 1/n_classes precision@k |
| **Clustering (unsupervised)** | Business metric per cluster (lift, size, outcome differential) | Silhouette score (secondary, only as sanity check) |

---

## How to Test an ML Model

1. **Sanity test with synthetic data:** Generate 1000 rows with label fully determined by 1 feature → model should reach ~1.0 AUC. If not, pipeline bug.
2. **Label permutation test:** Randomly shuffle labels. AUC on test set should collapse to ~0.5. If it stays at 0.85, you have data leakage.
3. **Feature permutation importance:** Permute each feature column one-by-one. AUC drop > 0.05 = feature actually drives predictions; 0 drop = suspicious, may be 0-variance or leakage.
4. **Sliding window time CV:** Walk-forward validation on time-series.
5. **Segment-level evaluation:** Per-country, per-customer-segment, per-ERA. AUC differs >0.10 across segments → data-quality or representation issues.
6. **Shadow + A/B in production:** Score model alongside current process for 4 weeks without acting; then run A/B test with random assignment.
7. **Fairness:** Equalized odds / demographic parity across protected attributes (age group, gender, region) → document differences.
8. **Adversarial validation:** Train a classifier to distinguish train rows vs production rows. If AUC > 0.7, train and prod distributions differ → drift / missing feature transformations.

---

## Performance Behavior

| Model | Training time (1M rows, 20 cols) | Inference latency (row) | Typical AUC lift over LogReg |
|-------|----------------------------------|-------------------------|------------------------------|
| Logistic Regression | 2–10 s | <1 µs | Baseline 0 |
| Random Forest | 30–120 s | 5–20 µs | +0.02–0.06 |
| LightGBM / XGBoost | 10–60 s | 2–10 µs | +0.04–0.10 |
| CatBoost (many categoricals) | 15–90 s | 2–10 µs | +0.03–0.10 (best when lots of unordered cats) |
| TabNet / Neural Net | 5–30 min (GPU) | 10–100 µs | +0–0.05; often worse than GBT on small tabular |
| Deep FM / Wide-and-Deep | 10–60 min | 10–100 µs | best with large cross-product categorical spaces |

**Big-O summary for training:** LogReg O(n·k), Tree O(n·k·depth·trees), NN O(n·k·layers·epochs·batch_size_iterations). Inference: O(k·depth) per tree; constant per layer for NN.

---

## What to Inspect First (Model Underperforms / Weird Scores)

1. **Label quality.** Is 20% of your training data mislabelled? Fix labels before touching hyperparameters.
2. **Data leakage audit.** Did any feature get computed using data after the prediction date? Print max(feature_date) vs label_date; check for future joins.
3. **Random split used instead of time-split.** Time-leakage → great validation score, garbage production performance. This is #1 cause.
4. **Train-test distribution mismatch.** Run adversarial validation classifier; if it can separate, what's the most discriminative feature? Fix drift in feature pipeline.
5. **Single categorical column dominates importance (perm SHAP).** e.g., `customer_id` got ordinal-encoded → model memorised IDs → test set has new customers → collapse. Drop or hash + frequency-encode.
6. **Missing value strategy.** Model uses 0-imputation for spend; 0-spend has a real business meaning ≈ missing → wrong. Use separate `is_na` flag + median imputation, or use tree models' native missing handling.
7. **Threshold mis-tuned.** Recall drops because default 0.5 threshold is wrong for 99:1 class imbalance → tune with cost matrix.
8. **Calibration broken.** Model predicts 0.9 prob → only 60% of such cases churn → bad expected revenue calculation.
9. **Target re-definition during project:** "Churn = no login 90 days" mid-project changed to "no login 60 days" → label dates overlap feature windows → leakage.
10. **Class weight / sample weight bugs:** you set `class_weight='balanced'` but threshold on raw probability without recalibration → massively over-predicts minority class.

---

## When *Not* to Use ML: The Checklist

Before training any model, answer YES to ALL:
- [ ] There is a **repeatable** decision this model scores.
- [ ] A **human/rule baseline exists** and I've measured its accuracy/cost.
- [ ] The ML model needs to **beat the baseline by ≥ X%** to justify build + maintenance cost (X usually 5–20% depending on scale).
- [ ] I have at least **~1000 labelled examples** (tabular). More for text/image.
- [ ] I know the **cost per FP and FN** to set an optimal threshold.
- [ ] A **feedback loop exists** (we observe true labels in production within a reasonable horizon).
- [ ] I can run **shadow mode + A/B test** before full rollout.
- [ ] I have **resources to monitor drift and retrain** monthly/quarterly.

If any box is "no", the correct tool is usually: descriptive analytics, better data, a rule engine, or a human decision-maker.

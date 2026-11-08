# Vulnara ML — Vulnerability Priority Predictor: Evaluation

A supervised classifier that predicts whether a finding is **HIGH priority** (likely exploitable, act now) from scan context — complementing the static CVSS score.

## Dataset

- 5000 findings, 39.9% labelled HIGH priority.
- Synthetic, generated from a documented domain labelling function with 6% label noise (see `generate_dataset.py`), because labelled real-world exploitation data is scarce.
- 75% train / 25% stratified held-out test; 5-fold cross-validation on the training set.

## Model comparison (held-out test set)

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | CV F1 (mean±std) |
|---|---|---|---|---|---|---|
| LogisticRegression | 0.8528 | 0.8261 | 0.7996 | 0.8126 | 0.912 | 0.8206±0.0054 |
| DecisionTree | 0.828 | 0.7996 | 0.7595 | 0.779 | 0.873 | 0.7778±0.0147 |
| RandomForest | 0.8456 | 0.8148 | 0.7936 | 0.8041 | 0.899 | 0.7995±0.0147 |

**Best F1:** LogisticRegression (0.8126).

## Deployed model

**Logistic Regression** is deployed: it is competitive, fully interpretable, and runs on the backend with pure numpy (exported to `app/ml/model_params.json`) — no heavy ML dependency in production.

### Feature influence (logistic-regression coefficients, standardized)

| Feature | Coefficient | Direction |
|---|---|---|
| active_verified | +1.502 | raises priority |
| cvss_score | +1.332 | raises priority |
| unauthenticated | +1.042 | raises priority |
| internet_exposed | +0.827 | raises priority |
| service_risk | +0.537 | raises priority |
| has_cve | +0.352 | raises priority |
| ai_confidence | +0.294 | raises priority |
| severity_ord | -0.197 | lowers priority |
| port_uncommon | -0.004 | lowers priority |

## Confusion matrix (deployed Logistic Regression)

```
                predicted LOW   predicted HIGH
actual LOW             667              84
actual HIGH            100             399
```

## Classification report (Logistic Regression)

```
              precision    recall  f1-score   support

         LOW       0.87      0.89      0.88       751
        HIGH       0.83      0.80      0.81       499

    accuracy                           0.85      1250
   macro avg       0.85      0.84      0.85      1250
weighted avg       0.85      0.85      0.85      1250
```

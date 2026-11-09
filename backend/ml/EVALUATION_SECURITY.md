# Vulnara ML — Security Augmentation Models: Evaluation

Two supervised models that **augment** the LLM triage/remediation (an independent cross-check, not a replacement for the scanner or NVD):

1. **Vulnerability Detection** — binary: is a finding a genuine, exploitable vulnerability or a likely false positive?
2. **Patch Technique Recommender** — multi-class: which remediation class fits a confirmed vulnerability? The LLM then writes the detailed script.

Both: synthetic data from a documented domain labelling function with label noise (see `generate_security_datasets.py`); 75% train / 25% stratified held-out test; 5-fold CV on the training set; deployed as **Logistic Regression** exported to pure numpy (`app/ml/*_model_params.json`) — no scikit-learn in production.

## Vulnerability Detection (6000 findings)

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | CV F1 |
|---|---|---|---|---|---|---|
| LogisticRegression | 0.8813 | 0.8913 | 0.9018 | 0.8965 | 0.9231 | 0.8799 |
| DecisionTree | 0.8353 | 0.84 | 0.8784 | 0.8588 | 0.8647 | 0.8379 |
| RandomForest | 0.868 | 0.8729 | 0.8994 | 0.8859 | 0.9169 | 0.8681 |

**Best F1:** LogisticRegression (0.8965). **Deployed: Logistic Regression** (exported to `app/ml/detection_model_params.json`).

### Classification report (Logistic Regression)

```
                precision    recall  f1-score   support

FALSE_POSITIVE       0.87      0.85      0.86       645
    VULNERABLE       0.89      0.90      0.90       855

      accuracy                           0.88      1500
     macro avg       0.88      0.88      0.88      1500
  weighted avg       0.88      0.88      0.88      1500
```

## Patch Technique Recommender (6000 findings)

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | CV F1 |
|---|---|---|---|---|---|
| LogisticRegression | 0.824 | 0.6141 | 0.6208 | 0.6052 | 0.6224 |
| DecisionTree | 0.9213 | 0.8994 | 0.8412 | 0.8663 | 0.878 |
| RandomForest | 0.9247 | 0.911 | 0.8496 | 0.8759 | 0.8939 |

**Patch classes:** `VERSION_UPGRADE`, `PATCH_AND_RESTART`, `CREDENTIAL_ROTATION`, `ACCESS_CONTROL`, `DISABLE_SERVICE`, `NETWORK_SEGMENTATION`, `WAF_RULE`, `CONFIG_HARDENING`


**Best F1:** RandomForest (0.8759). **Deployed: Decision Tree** (exported to `app/ml/patch_model_params.json`).

### Classification report (Decision Tree)

```
                      precision    recall  f1-score   support

     VERSION_UPGRADE       0.94      0.97      0.96       360
   PATCH_AND_RESTART       0.93      0.96      0.94       355
 CREDENTIAL_ROTATION       0.92      0.94      0.93       217
      ACCESS_CONTROL       0.91      0.77      0.83        69
     DISABLE_SERVICE       0.89      0.83      0.86        89
NETWORK_SEGMENTATION       0.76      0.57      0.65        54
            WAF_RULE       0.92      0.73      0.81        48
    CONFIG_HARDENING       0.92      0.95      0.94       308

            accuracy                           0.92      1500
           macro avg       0.90      0.84      0.87      1500
        weighted avg       0.92      0.92      0.92      1500
```


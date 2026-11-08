"""
ml/train.py

Trains and compares models for the vulnerability **priority predictor**, then
exports the chosen model in a tiny JSON format the backend can run with just
numpy (no scikit-learn at runtime).

Pipeline:
  1. Load ml/dataset.csv (run generate_dataset.py first).
  2. Stratified train/test split.
  3. Train + 5-fold cross-validate three models:
       - Logistic Regression  (linear, interpretable, deployable in numpy)
       - Decision Tree
       - Random Forest        (ensemble baseline)
  4. Evaluate on the held-out test set: accuracy, precision, recall, F1,
     ROC-AUC, and a confusion matrix.
  5. Deploy Logistic Regression (competitive + lightweight + interpretable):
     export StandardScaler + coefficients to app/ml/model_params.json.
  6. Write ml/metrics.json and ml/EVALUATION.md for the report.
"""

from __future__ import annotations

import csv
import json
import os

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
)

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
FEATURES = [
    "cvss_score", "severity_ord", "has_cve", "active_verified",
    "ai_confidence", "unauthenticated", "internet_exposed",
    "service_risk", "port_uncommon",
]


def load():
    rows = []
    with open(os.path.join(HERE, "dataset.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append([float(r[c]) for c in FEATURES] + [int(r["priority"])])
    arr = np.array(rows)
    return arr[:, :-1], arr[:, -1].astype(int)


def evaluate(name, model, Xtr, Xte, ytr, yte):
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    proba = model.predict_proba(Xte)[:, 1]
    cv = cross_val_score(model, Xtr, ytr, cv=5, scoring="f1")
    cm = confusion_matrix(yte, pred)
    return {
        "model": name,
        "accuracy": round(accuracy_score(yte, pred), 4),
        "precision": round(precision_score(yte, pred), 4),
        "recall": round(recall_score(yte, pred), 4),
        "f1": round(f1_score(yte, pred), 4),
        "roc_auc": round(roc_auc_score(yte, proba), 4),
        "cv_f1_mean": round(cv.mean(), 4),
        "cv_f1_std": round(cv.std(), 4),
        "confusion_matrix": cm.tolist(),
    }, classification_report(yte, pred, target_names=["LOW", "HIGH"])


def main():
    X, y = load()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    print(f"dataset: {len(y)} rows | train {len(ytr)} | test {len(yte)} | HIGH-priority rate {y.mean():.2%}")

    models = {
        "LogisticRegression": Pipeline([("scaler", StandardScaler()),
                                        ("clf", LogisticRegression(max_iter=1000))]),
        "DecisionTree": DecisionTreeClassifier(max_depth=6, random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42),
    }

    results = []
    reports = {}
    for name, m in models.items():
        metrics, report = evaluate(name, m, Xtr, Xte, ytr, yte)
        results.append(metrics)
        reports[name] = report
        print(f"  {name:20s} acc={metrics['accuracy']} prec={metrics['precision']} "
              f"rec={metrics['recall']} f1={metrics['f1']} auc={metrics['roc_auc']}")

    # ---- export the deployed model (Logistic Regression) -----------------
    lr = models["LogisticRegression"]
    scaler = lr.named_steps["scaler"]
    clf = lr.named_steps["clf"]
    params = {
        "model": "logistic_regression",
        "features": FEATURES,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coef": clf.coef_[0].tolist(),
        "intercept": float(clf.intercept_[0]),
        "threshold": 0.5,
    }
    app_ml = os.path.join(BACKEND, "app", "ml")
    os.makedirs(app_ml, exist_ok=True)
    with open(os.path.join(app_ml, "model_params.json"), "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)
    print(f"  exported deployed model -> app/ml/model_params.json")

    # ---- write metrics + evaluation report -------------------------------
    with open(os.path.join(HERE, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, indent=2)

    best = max(results, key=lambda r: r["f1"])
    coef_rank = sorted(zip(FEATURES, clf.coef_[0]), key=lambda t: abs(t[1]), reverse=True)
    lines = [
        "# Vulnara ML — Vulnerability Priority Predictor: Evaluation\n",
        "A supervised classifier that predicts whether a finding is **HIGH priority** "
        "(likely exploitable, act now) from scan context — complementing the static CVSS score.\n",
        "## Dataset\n",
        f"- {len(y)} findings, {y.mean():.1%} labelled HIGH priority.",
        "- Synthetic, generated from a documented domain labelling function with 6% label noise "
        "(see `generate_dataset.py`), because labelled real-world exploitation data is scarce.",
        "- 75% train / 25% stratified held-out test; 5-fold cross-validation on the training set.\n",
        "## Model comparison (held-out test set)\n",
        "| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | CV F1 (mean±std) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['model']} | {r['accuracy']} | {r['precision']} | {r['recall']} | "
                     f"{r['f1']} | {r['roc_auc']} | {r['cv_f1_mean']}±{r['cv_f1_std']} |")
    lines += [
        f"\n**Best F1:** {best['model']} ({best['f1']}).",
        "\n## Deployed model\n",
        "**Logistic Regression** is deployed: it is competitive, fully interpretable, and runs on "
        "the backend with pure numpy (exported to `app/ml/model_params.json`) — no heavy ML "
        "dependency in production.\n",
        "### Feature influence (logistic-regression coefficients, standardized)\n",
        "| Feature | Coefficient | Direction |",
        "|---|---|---|",
    ]
    for feat, c in coef_rank:
        lines.append(f"| {feat} | {c:+.3f} | {'raises' if c > 0 else 'lowers'} priority |")
    lines += [
        "\n## Confusion matrix (deployed Logistic Regression)\n",
        "```",
        "                predicted LOW   predicted HIGH",
    ]
    cm = next(r for r in results if r["model"] == "LogisticRegression")["confusion_matrix"]
    lines += [
        f"actual LOW        {cm[0][0]:>8}        {cm[0][1]:>8}",
        f"actual HIGH       {cm[1][0]:>8}        {cm[1][1]:>8}",
        "```\n",
        "## Classification report (Logistic Regression)\n",
        "```", reports["LogisticRegression"].rstrip(), "```",
    ]
    with open(os.path.join(HERE, "EVALUATION.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("  wrote ml/metrics.json and ml/EVALUATION.md")


if __name__ == "__main__":
    main()

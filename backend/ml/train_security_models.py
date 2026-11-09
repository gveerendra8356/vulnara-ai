"""
ml/train_security_models.py

Trains, cross-validates and compares models for Vulnara's two augmentation
models, then exports each chosen model to a tiny JSON the backend runs with
pure numpy (no scikit-learn at runtime):

  1. Vulnerability DETECTION  (binary)       -> app/ml/detection_model_params.json
  2. Patch TECHNIQUE          (multi-class)  -> app/ml/patch_model_params.json

For each task it trains Logistic Regression, Decision Tree and Random Forest,
evaluates on a stratified held-out test set with 5-fold CV, and deploys
Logistic Regression (competitive, interpretable, numpy-deployable). Writes
ml/security_metrics.json and ml/EVALUATION_SECURITY.md for the report.

Run:  python ml/generate_security_datasets.py && python ml/train_security_models.py
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

from generate_security_datasets import (
    DETECTION_FEATURES, PATCH_FEATURES, PATCH_CLASSES,
)

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
APP_ML = os.path.join(BACKEND, "app", "ml")


def _load(csv_name: str, features: list[str], label_col: str):
    rows = []
    with open(os.path.join(HERE, csv_name), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append([float(r[c]) for c in features] + [int(r[label_col])])
    arr = np.array(rows)
    return arr[:, :-1], arr[:, -1].astype(int)


def _models(multiclass: bool) -> dict:
    # Newer scikit-learn (>=1.7) dropped the `multi_class` argument and always
    # uses multinomial (softmax) when the target has >2 classes, which is
    # exactly what we want for the patch-technique model -- so no extra kwarg.
    return {
        "LogisticRegression": Pipeline([("scaler", StandardScaler()),
                                        ("clf", LogisticRegression(max_iter=2000))]),
        "DecisionTree": DecisionTreeClassifier(max_depth=8, random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42),
    }


def _evaluate(name, model, Xtr, Xte, ytr, yte, multiclass: bool):
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    avg = "macro" if multiclass else "binary"
    metrics = {
        "model": name,
        "accuracy": round(accuracy_score(yte, pred), 4),
        "precision": round(precision_score(yte, pred, average=avg, zero_division=0), 4),
        "recall": round(recall_score(yte, pred, average=avg, zero_division=0), 4),
        "f1": round(f1_score(yte, pred, average=avg, zero_division=0), 4),
        "cv_f1_mean": round(cross_val_score(model, Xtr, ytr, cv=5,
                            scoring="f1_macro" if multiclass else "f1").mean(), 4),
    }
    if not multiclass:
        proba = model.predict_proba(Xte)[:, 1]
        metrics["roc_auc"] = round(roc_auc_score(yte, proba), 4)
    return metrics


def _export_logreg(pipeline, features, out_name, multiclass, classes=None):
    scaler = pipeline.named_steps["scaler"]
    clf = pipeline.named_steps["clf"]
    params = {
        "model": "logistic_regression",
        "multiclass": multiclass,
        "features": features,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        # binary: coef_ is (1, n) -> store flat; multiclass: (n_classes, n)
        "coef": clf.coef_.tolist(),
        "intercept": clf.intercept_.tolist(),
    }
    if multiclass:
        params["classes"] = [classes[i] for i in clf.classes_]
    else:
        params["threshold"] = 0.5
    os.makedirs(APP_ML, exist_ok=True)
    with open(os.path.join(APP_ML, out_name), "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)


def _export_decision_tree(tree_clf, features, classes, out_name):
    """Exports a fitted DecisionTreeClassifier as a flat node table the backend
    traverses with pure python (no scikit-learn at runtime). The patch cascade
    is rule-structured, so a tree both scores best and stays interpretable."""
    t = tree_clf.tree_
    params = {
        "model": "decision_tree",
        "features": features,
        "classes": [classes[i] for i in tree_clf.classes_],
        "children_left": t.children_left.tolist(),
        "children_right": t.children_right.tolist(),
        "feature": t.feature.tolist(),       # -2 at a leaf
        "threshold": t.threshold.tolist(),
        "value": [row[0].tolist() for row in t.value],  # per-node class counts
    }
    os.makedirs(APP_ML, exist_ok=True)
    with open(os.path.join(APP_ML, out_name), "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)


def _train_task(title, csv_name, features, label_col, multiclass, classes=None):
    X, y = _load(csv_name, features, label_col)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    results = []
    reports = {}
    for name, m in _models(multiclass).items():
        results.append(_evaluate(name, m, Xtr, Xte, ytr, yte, multiclass))
        reports[name] = classification_report(
            yte, m.predict(Xte),
            target_names=classes if multiclass else ["FALSE_POSITIVE", "VULNERABLE"],
            zero_division=0,
        )
    lr = _models(multiclass)["LogisticRegression"]
    lr.fit(Xtr, ytr)
    dt = DecisionTreeClassifier(max_depth=8, random_state=42)
    dt.fit(Xtr, ytr)
    return {
        "title": title, "csv": csv_name, "features": features,
        "multiclass": multiclass, "classes": classes,
        "n": int(len(y)), "results": results, "reports": reports,
        "pipeline": lr, "tree": dt, "Xte": Xte, "yte": yte,
    }


def main():
    det = _train_task("Vulnerability Detection", "detection_dataset.csv",
                      DETECTION_FEATURES, "is_vulnerable", multiclass=False)
    _export_logreg(det["pipeline"], DETECTION_FEATURES, "detection_model_params.json", False)
    print("detection model ->", {r["model"]: r["f1"] for r in det["results"]})

    det["deployed"] = "Logistic Regression"

    patch = _train_task("Patch Technique Recommender", "patch_dataset.csv",
                        PATCH_FEATURES, "patch_class", multiclass=True, classes=PATCH_CLASSES)
    # The patch target is a rule cascade -> a tree captures it far better than a
    # linear model, and stays interpretable, so the Decision Tree is deployed.
    _export_decision_tree(patch["tree"], PATCH_FEATURES, PATCH_CLASSES, "patch_model_params.json")
    patch["deployed"] = "Decision Tree"
    print("patch model ->", {r["model"]: r["f1"] for r in patch["results"]})

    # ---- metrics.json + EVALUATION_SECURITY.md ---------------------------
    with open(os.path.join(HERE, "security_metrics.json"), "w", encoding="utf-8") as f:
        json.dump({"detection": det["results"], "patch": patch["results"]}, f, indent=2)

    lines = [
        "# Vulnara ML — Security Augmentation Models: Evaluation\n",
        "Two supervised models that **augment** the LLM triage/remediation (an "
        "independent cross-check, not a replacement for the scanner or NVD):\n",
        "1. **Vulnerability Detection** — binary: is a finding a genuine, exploitable "
        "vulnerability or a likely false positive?",
        "2. **Patch Technique Recommender** — multi-class: which remediation class fits "
        "a confirmed vulnerability? The LLM then writes the detailed script.\n",
        "Both: synthetic data from a documented domain labelling function with label noise "
        "(see `generate_security_datasets.py`); 75% train / 25% stratified held-out test; "
        "5-fold CV on the training set; deployed as **Logistic Regression** exported to pure "
        "numpy (`app/ml/*_model_params.json`) — no scikit-learn in production.\n",
    ]

    for task in (det, patch):
        lines.append(f"## {task['title']} ({task['n']} findings)\n")
        if task["multiclass"]:
            lines += ["| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | CV F1 |",
                      "|---|---|---|---|---|---|"]
            for r in task["results"]:
                lines.append(f"| {r['model']} | {r['accuracy']} | {r['precision']} | "
                             f"{r['recall']} | {r['f1']} | {r['cv_f1_mean']} |")
            lines += ["\n**Patch classes:** " + ", ".join(f"`{c}`" for c in task["classes"]) + "\n"]
        else:
            lines += ["| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | CV F1 |",
                      "|---|---|---|---|---|---|---|"]
            for r in task["results"]:
                lines.append(f"| {r['model']} | {r['accuracy']} | {r['precision']} | "
                             f"{r['recall']} | {r['f1']} | {r['roc_auc']} | {r['cv_f1_mean']} |")
        best = max(task["results"], key=lambda r: r["f1"])
        report_key = task["deployed"].replace(" ", "")  # "Decision Tree" -> "DecisionTree"
        lines.append(f"\n**Best F1:** {best['model']} ({best['f1']}). "
                     f"**Deployed: {task['deployed']}** "
                     f"(exported to `app/ml/{'detection' if not task['multiclass'] else 'patch'}_model_params.json`).\n")
        lines += [f"### Classification report ({task['deployed']})\n", "```",
                  task["reports"][report_key].rstrip(), "```\n"]

    with open(os.path.join(HERE, "EVALUATION_SECURITY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote ml/security_metrics.json and ml/EVALUATION_SECURITY.md")


if __name__ == "__main__":
    main()

"""
ml/generate_dataset.py

Generates the training dataset for Vulnara's vulnerability **priority
predictor** -- a model that estimates how urgently a finding should be acted
on (exploit-likelihood), going beyond the static CVSS severity by using
scan *context*.

Why synthetic data?
    Labelled real-world exploitation outcomes ("was this finding actually
    exploited / a true priority?") are proprietary and scarce. So, like the
    public EPSS project motivates, we define a transparent, domain-driven
    labelling function over realistic features, add noise, and let the model
    *learn* that function. The data-generation process is documented here in
    full so the experiment is reproducible and defensible.

Each row is one vulnerability finding with these features:
    cvss_score        0-10   CVSS v3 base score
    severity_ord      0-4    INFO/LOW/MEDIUM/HIGH/CRITICAL
    has_cve           0/1    a concrete CVE was matched
    active_verified   0/1    active testing confirmed exploitability
    ai_confidence     0-1    the LLM triage confidence
    unauthenticated   0/1    service reachable without credentials
    internet_exposed  0/1    target is public-facing
    service_risk      0-3    service class risk (web<ssh<db<remote-exec)
    port_uncommon     0/1    service on a non-standard port

Label:
    priority          0/1    1 = HIGH priority (act now), 0 = LOW priority
"""

from __future__ import annotations

import csv
import os

import numpy as np

FEATURES = [
    "cvss_score", "severity_ord", "has_cve", "active_verified",
    "ai_confidence", "unauthenticated", "internet_exposed",
    "service_risk", "port_uncommon",
]

RNG = np.random.default_rng(42)  # fixed seed -> reproducible


def generate(n: int = 5000) -> tuple[np.ndarray, np.ndarray]:
    cvss = np.clip(RNG.normal(6.0, 2.5, n), 0, 10)
    severity_ord = np.clip((cvss / 2.5).round(), 0, 4).astype(int)
    has_cve = (RNG.random(n) < 0.55).astype(int)
    active_verified = (RNG.random(n) < 0.30).astype(int)
    ai_conf = np.clip(RNG.normal(0.6, 0.2, n), 0.05, 0.99)
    unauth = (RNG.random(n) < 0.35).astype(int)
    exposed = (RNG.random(n) < 0.5).astype(int)
    service_risk = RNG.integers(0, 4, n)          # 0..3
    port_uncommon = (RNG.random(n) < 0.4).astype(int)

    X = np.column_stack([
        cvss, severity_ord, has_cve, active_verified, ai_conf,
        unauth, exposed, service_risk, port_uncommon,
    ])

    # ---- documented domain labelling function (the "ground truth") --------
    latent = (
        0.34 * (cvss / 10.0)
        + 0.22 * active_verified
        + 0.14 * unauth
        + 0.12 * exposed
        + 0.10 * (service_risk / 3.0)
        + 0.06 * has_cve
        - 0.12 * (1.0 - ai_conf)          # low AI confidence lowers priority
    )
    latent += RNG.normal(0, 0.06, n)       # measurement noise
    label = (latent > 0.45).astype(int)

    # realistic label noise: ~6% of labels flipped (no model should hit 100%)
    flip = RNG.random(n) < 0.06
    label[flip] = 1 - label[flip]
    return X, label


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    X, y = generate()
    path = os.path.join(out_dir, "dataset.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FEATURES + ["priority"])
        for row, label in zip(X, y):
            w.writerow([f"{v:.4f}" for v in row] + [int(label)])
    pos = int(y.sum())
    print(f"Wrote {len(y)} rows to {path}  (priority=1: {pos}, priority=0: {len(y)-pos})")


if __name__ == "__main__":
    main()

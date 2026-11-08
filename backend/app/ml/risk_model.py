"""
app/ml/risk_model.py

Runtime inference for the vulnerability **priority predictor**. The model is a
Logistic Regression trained offline (see backend/ml/train.py); here we load
only its exported parameters and run inference with the standard library, so
the production backend needs no scikit-learn dependency.

prediction = sigmoid( sum( ((x - mean) / scale) * coef ) + intercept )
"""

from __future__ import annotations

import json
import math
import os

_PARAMS: dict | None = None

# How a finding's service maps to a 0-3 "service class risk".
_SERVICE_RISK = {
    "redis": 3, "mysql": 3, "postgresql": 3, "mongodb": 3, "mssql": 3,
    "ms-wbt-server": 3, "rdp": 3, "vnc": 3, "microsoft-ds": 3, "smb": 3,
    "ssh": 2, "ftp": 2, "telnet": 2, "snmp": 2, "smtp": 2,
    "http": 1, "https": 1, "http-proxy": 1, "http-alt": 1, "ssl/http": 1,
}
_SEVERITY_ORD = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
_COMMON_PORTS = {21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 3389, 5432, 6379, 8080, 8443}


def _load() -> dict:
    global _PARAMS
    if _PARAMS is None:
        path = os.path.join(os.path.dirname(__file__), "model_params.json")
        with open(path, encoding="utf-8") as f:
            _PARAMS = json.load(f)
    return _PARAMS


def predict(features: dict) -> dict:
    """features: a dict with the keys in the trained feature list. Missing keys
    default to 0. Returns a 0-100 priority score, a HIGH/LOW label, and the raw
    probability."""
    p = _load()
    z = p["intercept"]
    for name, mean, scale, coef in zip(p["features"], p["mean"], p["scale"], p["coef"]):
        x = float(features.get(name, 0.0))
        z += ((x - mean) / scale) * coef
    prob = 1.0 / (1.0 + math.exp(-z))
    return {
        "priority_score": round(prob * 100, 1),
        "priority_label": "HIGH" if prob >= p.get("threshold", 0.5) else "LOW",
        "probability": round(prob, 4),
    }


def features_from_finding(
    *,
    cvss_score: float | None,
    severity: str | None,
    cve_id: str | None,
    service_name: str | None,
    port: int | None,
    confidence_score: float | None,
    active_verified: bool = False,
    internet_exposed: bool = True,
) -> dict:
    """Derives the model's feature vector from a vulnerability finding."""
    svc = (service_name or "").lower()
    unauth = 1 if svc in ("redis", "memcached", "mongodb") else 0
    return {
        "cvss_score": float(cvss_score or 0.0),
        "severity_ord": _SEVERITY_ORD.get((severity or "INFO").upper(), 0),
        "has_cve": 1 if cve_id else 0,
        "active_verified": 1 if active_verified else 0,
        "ai_confidence": float(confidence_score if confidence_score is not None else 0.5),
        "unauthenticated": unauth,
        "internet_exposed": 1 if internet_exposed else 0,
        "service_risk": _SERVICE_RISK.get(svc, 1),
        "port_uncommon": 0 if (port in _COMMON_PORTS) else 1,
    }

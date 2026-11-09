"""
app/ml/security_model.py

Runtime inference for Vulnara's two LLM-augmentation models, trained offline
(see backend/ml/train_security_models.py) and exported to JSON so production
needs no scikit-learn:

  • detect(features)         -> Logistic Regression (binary): is this finding a
                               genuine, exploitable vulnerability?
  • recommend_patch(features)-> Decision Tree (multi-class): which remediation
                               technique fits this confirmed vulnerability?

Both expose a features_* helper that derives the model's feature vector from a
stored Vulnerability row, so the API never has to know the model internals.
"""

from __future__ import annotations

import json
import math
import os

_DET: dict | None = None
_PATCH: dict | None = None

# ---- shared finding -> feature mappings ----------------------------------
_SEVERITY_ORD = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
_SERVICE_RISK = {
    "redis": 3, "mysql": 3, "postgresql": 3, "mongodb": 3, "mssql": 3,
    "ms-wbt-server": 3, "rdp": 3, "vnc": 3, "microsoft-ds": 3, "smb": 3,
    "ssh": 2, "ftp": 2, "telnet": 2, "snmp": 2, "smtp": 2,
    "http": 1, "https": 1, "http-proxy": 1, "http-alt": 1, "ssl/http": 1,
}
_COMMON_PORTS = {21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 3389, 5432, 6379, 8080, 8443}

# service_class buckets for the patch model (0 web .. 5 other)
_WEB = {"http", "https", "http-proxy", "http-alt", "ssl/http"}
_REMOTE_LOGIN = {"ssh", "ftp", "telnet"}
_DATABASE = {"mysql", "postgresql", "mongodb", "redis", "mssql"}
_REMOTE_EXEC = {"rdp", "ms-wbt-server", "vnc", "smb", "microsoft-ds"}
_MAIL_DNS = {"smtp", "dns", "imap", "pop3", "domain"}
# services that commonly ship with default / weak credentials
_DEFAULT_CRED = {"redis", "mongodb", "mysql", "mssql", "vnc", "telnet", "ftp", "snmp"}

PATCH_DESCRIPTIONS = {
    "VERSION_UPGRADE": "Upgrade the affected software to the vendor-patched version.",
    "PATCH_AND_RESTART": "Apply the vendor security patch/hotfix and restart the service.",
    "CREDENTIAL_ROTATION": "Rotate credentials, remove default/weak accounts and enforce strong authentication.",
    "ACCESS_CONTROL": "Restrict access with authentication, firewall rules and least-privilege.",
    "DISABLE_SERVICE": "Disable or remove the unnecessary / legacy service.",
    "NETWORK_SEGMENTATION": "Move the asset off the public network into a segmented internal zone.",
    "WAF_RULE": "Deploy a WAF / virtual-patch rule to block the exploit at the edge.",
    "CONFIG_HARDENING": "Harden the service configuration to secure defaults.",
}


def _load(name: str) -> dict:
    with open(os.path.join(os.path.dirname(__file__), name), encoding="utf-8") as f:
        return json.load(f)


def _det() -> dict:
    global _DET
    if _DET is None:
        _DET = _load("detection_model_params.json")
    return _DET


def _patch() -> dict:
    global _PATCH
    if _PATCH is None:
        _PATCH = _load("patch_model_params.json")
    return _PATCH


def _service_class(svc: str) -> int:
    if svc in _WEB:
        return 0
    if svc in _REMOTE_LOGIN:
        return 1
    if svc in _DATABASE:
        return 2
    if svc in _REMOTE_EXEC:
        return 3
    if svc in _MAIL_DNS:
        return 4
    return 5


# =========================================================================
# Vulnerability detection (binary logistic regression)
# =========================================================================
def detection_features_from_finding(*, cvss_score, severity, cve_id, service_name,
                                     service_version, port, confidence_score,
                                     active_verified=False) -> dict:
    svc = (service_name or "").lower()
    has_cve = 1 if cve_id else 0
    return {
        "cvss_score": float(cvss_score or 0.0),
        "has_cve": has_cve,
        "ai_confidence": float(confidence_score if confidence_score is not None else 0.5),
        # a matched CVE on a known running version implies an outdated build
        "version_outdated": 1 if (has_cve and service_version) else 0,
        "banner_cve_match": 1 if (has_cve and service_version) else 0,
        "service_risk": _SERVICE_RISK.get(svc, 1),
        "port_uncommon": 0 if port in _COMMON_PORTS else 1,
        "unauthenticated": 1 if svc in ("redis", "memcached", "mongodb") else 0,
        "active_verified": 1 if active_verified else 0,
    }


def detect(features: dict) -> dict:
    p = _det()
    coef = p["coef"][0] if isinstance(p["coef"][0], list) else p["coef"]
    z = p["intercept"][0] if isinstance(p["intercept"], list) else p["intercept"]
    for name, mean, scale, c in zip(p["features"], p["mean"], p["scale"], coef):
        x = float(features.get(name, 0.0))
        z += ((x - mean) / scale) * c
    prob = 1.0 / (1.0 + math.exp(-z))
    return {
        "is_vulnerable": prob >= p.get("threshold", 0.5),
        "detection_score": round(prob * 100, 1),
        "probability": round(prob, 4),
    }


# =========================================================================
# Patch technique (multi-class decision tree)
# =========================================================================
def patch_features_from_finding(*, cvss_score, severity, cve_id, service_name,
                                service_version, internet_exposed=True) -> dict:
    svc = (service_name or "").lower()
    has_cve = 1 if cve_id else 0
    cvss = float(cvss_score or 0.0)
    return {
        "service_class": _service_class(svc),
        "severity_ord": _SEVERITY_ORD.get((severity or "INFO").upper(), 0),
        "has_cve": has_cve,
        "version_outdated": 1 if (has_cve and service_version) else 0,
        "unauthenticated": 1 if svc in ("redis", "memcached", "mongodb") else 0,
        "internet_exposed": 1 if internet_exposed else 0,
        "default_creds_risk": 1 if svc in _DEFAULT_CRED else 0,
        # proxy for "a public exploit exists": a matched CVE at high severity
        "exploit_public": 1 if (has_cve and cvss >= 7.0) else 0,
    }


def recommend_patch(features: dict) -> dict:
    p = _patch()
    x = [float(features.get(name, 0.0)) for name in p["features"]]
    cl, cr = p["children_left"], p["children_right"]
    feat, thr, val = p["feature"], p["threshold"], p["value"]
    node = 0
    # a leaf has no children (both set to -1 by scikit-learn)
    while cl[node] != -1:
        node = cl[node] if x[feat[node]] <= thr[node] else cr[node]
    counts = val[node]
    total = sum(counts) or 1.0
    idx = max(range(len(counts)), key=lambda i: counts[i])
    technique = p["classes"][idx]
    return {
        "technique": technique,
        "technique_label": technique.replace("_", " ").title(),
        "description": PATCH_DESCRIPTIONS.get(technique, ""),
        "confidence": round(counts[idx] / total, 4),
    }

"""
ml/generate_security_datasets.py

Generates the training data for Vulnara's two supervised security models that
*augment* the LLM (they cross-check it, they don't replace the scanner/NVD):

  1. Vulnerability DETECTION classifier  -> detection_dataset.csv
     Binary: is a raw finding a GENUINE, exploitable vulnerability (1) or a
     likely false-positive / benign artefact (0)? This is an independent
     confirmation of the LLM triage's own true/false-positive decision.

  2. Patch TECHNIQUE recommender         -> patch_dataset.csv
     Multi-class: given a confirmed vulnerability's characteristics, which
     remediation *class* is appropriate (upgrade, harden, disable, ...)?
     The LLM then writes the detailed script for that class.

Why synthetic data?
    Labelled real-world "was this exploited / which fix was applied" outcomes
    are proprietary and scarce. As the public EPSS project motivates, we write
    a transparent, documented domain labelling function over realistic
    features, add noise, and let the models *learn* it. The whole process is
    reproducible (fixed seed) and defensible for the report.
"""

from __future__ import annotations

import csv
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RNG = np.random.default_rng(1337)  # fixed seed -> reproducible

# ---------------------------------------------------------------------------
# Model 1: Vulnerability detection (binary)
# ---------------------------------------------------------------------------
DETECTION_FEATURES = [
    "cvss_score",       # 0-10  CVSS v3 base score
    "has_cve",          # 0/1   a concrete CVE was matched
    "ai_confidence",    # 0-1   LLM triage confidence
    "version_outdated", # 0/1   running version older than the fixed version
    "banner_cve_match", # 0/1   the service banner matched a CVE signature
    "service_risk",     # 0-3   service class risk (web<ssh<db<remote-exec)
    "port_uncommon",    # 0/1   service on a non-standard port
    "unauthenticated",  # 0/1   reachable with no credentials
    "active_verified",  # 0/1   active testing confirmed behaviour
]


def generate_detection(n: int = 6000) -> tuple[np.ndarray, np.ndarray]:
    cvss = np.clip(RNG.normal(6.0, 2.6, n), 0, 10)
    has_cve = (RNG.random(n) < 0.55).astype(int)
    ai_conf = np.clip(RNG.normal(0.62, 0.2, n), 0.05, 0.99)
    version_outdated = (RNG.random(n) < 0.5).astype(int)
    banner_match = (RNG.random(n) < 0.45).astype(int)
    service_risk = RNG.integers(0, 4, n)
    port_uncommon = (RNG.random(n) < 0.4).astype(int)
    unauth = (RNG.random(n) < 0.35).astype(int)
    active_verified = (RNG.random(n) < 0.30).astype(int)

    X = np.column_stack([
        cvss, has_cve, ai_conf, version_outdated, banner_match,
        service_risk, port_uncommon, unauth, active_verified,
    ])

    # ---- documented domain labelling function (the "ground truth") --------
    # A finding is a genuine vulnerability when the exploit-signal evidence
    # (CVE match, outdated version, banner signature, active confirmation,
    # severity) outweighs the noise; low AI confidence pulls it toward a
    # false positive.
    latent = (
        0.30 * (cvss / 10.0)
        + 0.22 * banner_match
        + 0.18 * has_cve
        + 0.15 * version_outdated
        + 0.14 * active_verified
        + 0.10 * (service_risk / 3.0)
        + 0.08 * unauth
        + 0.10 * ai_conf
        - 0.18 * (1.0 - ai_conf)   # low confidence -> likely false positive
    )
    latent += RNG.normal(0, 0.06, n)
    label = (latent > 0.52).astype(int)

    # realistic label noise: ~6% flipped (no model should hit 100%)
    flip = RNG.random(n) < 0.06
    label[flip] = 1 - label[flip]
    return X, label


# ---------------------------------------------------------------------------
# Model 2: Patch technique (multi-class)
# ---------------------------------------------------------------------------
PATCH_FEATURES = [
    "service_class",     # 0 web, 1 remote-login(ssh/ftp/telnet), 2 database,
                         # 3 remote-exec(rdp/vnc/smb), 4 mail/dns, 5 other
    "severity_ord",      # 0-4  INFO..CRITICAL
    "has_cve",           # 0/1
    "version_outdated",  # 0/1
    "unauthenticated",   # 0/1
    "internet_exposed",  # 0/1
    "default_creds_risk",# 0/1  service commonly ships with default creds
    "exploit_public",    # 0/1  a public exploit/PoC exists
]

PATCH_CLASSES = [
    "VERSION_UPGRADE",
    "PATCH_AND_RESTART",
    "CREDENTIAL_ROTATION",
    "ACCESS_CONTROL",
    "DISABLE_SERVICE",
    "NETWORK_SEGMENTATION",
    "WAF_RULE",
    "CONFIG_HARDENING",
]
_CLASS_IDX = {c: i for i, c in enumerate(PATCH_CLASSES)}


def _patch_label(svc, sev, has_cve, outdated, unauth, exposed, default_creds, exploit_public) -> int:
    """Documented decision cascade (first match wins), ordered most-specific
    first. Maps a confirmed vulnerability's traits to a remediation class."""
    # 1. A patchable CVE on an outdated build -> upgrade to the fixed version.
    if has_cve and outdated:
        return _CLASS_IDX["VERSION_UPGRADE"]
    # 2. A CVE but already on a current build -> hotfix / patch + restart.
    if has_cve and not outdated:
        return _CLASS_IDX["PATCH_AND_RESTART"]
    # 3. Default / weak credentials, or an unauthenticated DB/login service.
    if default_creds or (unauth and svc in (1, 2)):
        return _CLASS_IDX["CREDENTIAL_ROTATION"]
    # 4. Internet-exposed database or remote-exec at high severity -> isolate.
    if exposed and svc in (2, 3) and sev >= 3:
        return _CLASS_IDX["NETWORK_SEGMENTATION"]
    # 5. Web service with a public exploit -> virtual-patch at the WAF.
    if svc == 0 and exploit_public:
        return _CLASS_IDX["WAF_RULE"]
    # 6. Legacy remote-exec service with no fix available -> turn it off.
    if svc == 3 and not has_cve:
        return _CLASS_IDX["DISABLE_SERVICE"]
    # 7. Reachable without auth -> put access control in front of it.
    if unauth and exposed:
        return _CLASS_IDX["ACCESS_CONTROL"]
    # 8. Everything else -> configuration hardening.
    return _CLASS_IDX["CONFIG_HARDENING"]


def generate_patch(n: int = 6000) -> tuple[np.ndarray, np.ndarray]:
    svc = RNG.integers(0, 6, n)
    sev = RNG.integers(0, 5, n)
    has_cve = (RNG.random(n) < 0.5).astype(int)
    outdated = (RNG.random(n) < 0.5).astype(int)
    unauth = (RNG.random(n) < 0.4).astype(int)
    exposed = (RNG.random(n) < 0.55).astype(int)
    default_creds = (RNG.random(n) < 0.18).astype(int)
    exploit_public = (RNG.random(n) < 0.35).astype(int)

    X = np.column_stack([
        svc, sev, has_cve, outdated, unauth, exposed, default_creds, exploit_public,
    ])

    y = np.array([
        _patch_label(*row) for row in zip(
            svc, sev, has_cve, outdated, unauth, exposed, default_creds, exploit_public
        )
    ])

    # realistic label noise: ~7% nudged to a different class.
    flip = RNG.random(n) < 0.07
    y[flip] = RNG.integers(0, len(PATCH_CLASSES), int(flip.sum()))
    return X, y


# ---------------------------------------------------------------------------
def _write(path: str, header: list[str], X: np.ndarray, y: np.ndarray, int_cols: set[int]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row, label in zip(X, y):
            cells = [str(int(v)) if i in int_cols else f"{v:.4f}" for i, v in enumerate(row)]
            w.writerow(cells + [int(label)])


def main():
    Xd, yd = generate_detection()
    # every detection feature except cvss_score (0) and ai_confidence (2) is integer
    det_int_cols = {i for i in range(len(DETECTION_FEATURES))} - {0, 2}
    _write(os.path.join(HERE, "detection_dataset.csv"),
           DETECTION_FEATURES + ["is_vulnerable"], Xd, yd, det_int_cols)
    print(f"detection_dataset.csv: {len(yd)} rows | vulnerable rate {yd.mean():.1%}")

    Xp, yp = generate_patch()
    patch_int_cols = set(range(len(PATCH_FEATURES)))  # all integer
    _write(os.path.join(HERE, "patch_dataset.csv"),
           PATCH_FEATURES + ["patch_class"], Xp, yp, patch_int_cols)
    dist = {PATCH_CLASSES[i]: int((yp == i).sum()) for i in range(len(PATCH_CLASSES))}
    print(f"patch_dataset.csv: {len(yp)} rows | class distribution:")
    for k, v in dist.items():
        print(f"    {k:22s} {v}")


if __name__ == "__main__":
    main()

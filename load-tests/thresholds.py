"""
load-tests/thresholds.py — CI-friendly performance acceptance criteria.

Thresholds are deliberately realistic for a free-tier single-worker backend on
a 2-vCPU GitHub runner, so the gate fails on genuine regressions, not on an
unrealistic target (per the brief). Each endpoint group has a p95 latency
ceiling (ms) and a maximum error rate (%). A global error-rate ceiling applies
to the whole run.
"""

# Per-endpoint-group ceilings. Keys are matched as a prefix of the Locust
# "Name" column (the grouped request name), longest-prefix wins.
ENDPOINT_THRESHOLDS = {
    "GET /health":            {"p95_ms": 800,  "max_error_rate": 1.0},
    "POST /auth/login":       {"p95_ms": 2500, "max_error_rate": 2.0},
    "GET /auth/me":           {"p95_ms": 1500, "max_error_rate": 2.0},
    "GET /scans":             {"p95_ms": 2500, "max_error_rate": 3.0},
    "GET /scans/:id":         {"p95_ms": 2500, "max_error_rate": 3.0},
    "GET /scans/:id/risk":    {"p95_ms": 3000, "max_error_rate": 3.0},
    "GET /overview":          {"p95_ms": 3000, "max_error_rate": 3.0},
    "GET /remediations":      {"p95_ms": 2500, "max_error_rate": 3.0},
    "GET /departments":       {"p95_ms": 2000, "max_error_rate": 3.0},
    "GET /schedules":         {"p95_ms": 2000, "max_error_rate": 3.0},
    "POST /ml/analyze":       {"p95_ms": 2000, "max_error_rate": 2.0},
    "POST /ml/risk-score":    {"p95_ms": 2000, "max_error_rate": 2.0},
}

# Applied to the aggregated run.
GLOBAL_MAX_ERROR_RATE = 5.0   # percent of all requests
GLOBAL_P95_CEILING_MS = 4000  # aggregated p95 ceiling


def threshold_for(name: str) -> dict:
    """Longest-prefix match of a grouped request name to its threshold."""
    best = None
    for prefix, cfg in ENDPOINT_THRESHOLDS.items():
        if name.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, cfg)
    return best[1] if best else {"p95_ms": GLOBAL_P95_CEILING_MS, "max_error_rate": GLOBAL_MAX_ERROR_RATE}

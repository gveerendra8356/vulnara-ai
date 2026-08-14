# Performance Report -- Vulnara Backend

## Why this isn't a full k6 run
This sandbox has no outbound network access to install the `k6` binary
(it isn't on PyPI/npm), so a full k6 load test could not be executed here.
`performance/k6-load-test.js` is included and ready to run in any
environment with `k6` installed and network access to a deployed instance:

```bash
BASE_URL=https://your-deployed-instance.example k6 run performance/k6-load-test.js
```

It exercises the same core flows as this suite -- login, scan creation,
scan retrieval, vulnerability listing -- ramping from 1 to 50 virtual users
over 5 minutes, with thresholds of p95 < 500ms and error rate < 1%.

## In-process load sample (this run)

A lightweight async load generator (not k6 -- see below for why) hit
`GET /health` and `GET /scans` concurrently against the same ephemeral
instance used for the functional suite, immediately after the 400-case run.

| Metric | GET /health | GET /scans (client1) |
|---|---|---|
| Requests | 300 | 300 |
| Concurrency | 20 | 20 |
| p50 latency (ms) | 32.25 | 56.61 |
| p95 latency (ms) | 213.43 | 227.84 |
| p99 latency (ms) | 502.16 | 561.95 |
| Max latency (ms) | 563.71 | 614.32 |
| Error rate | 0.0% | 0.0% |
| Throughput (req/s) | 275.6 | 202.4 |


## Interpreting these numbers
This sample is against a single-worker `uvicorn` process on ephemeral
SQLite with no connection pooling tuning -- it is **not** representative of
production (Postgres + whatever hosting tier is actually deployed). Treat
it as a smoke-level sanity check that the app doesn't fall over under light
concurrency, not as a capacity-planning number. Run `k6-load-test.js`
against a real staging deployment for numbers you can actually act on.

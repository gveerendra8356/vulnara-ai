/**
 * k6-load-test.js
 *
 * Not runnable in the sandbox this suite was built in (no network access to
 * install the k6 binary), so this has not been executed here -- but it's a
 * complete, ready-to-run script for CI or a staging environment that has
 * k6 installed.
 *
 * Usage:
 *   BASE_URL=https://staging.vulnara.example \
 *   TEST_EMAIL=client1.qa@vulnara-qa-suite.com \
 *   TEST_PASSWORD=Client1QA123! \
 *   k6 run performance/k6-load-test.js
 *
 * Exercises the core authenticated flow: login -> create scan -> get scan
 * -> list scans -> list scan vulnerabilities, ramping 1 -> 50 VUs over 5
 * minutes. Thresholds fail the run if p95 latency or the error rate drift
 * out of an acceptable range for a QA/staging gate.
 */
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const TEST_EMAIL = __ENV.TEST_EMAIL || 'client1.qa@vulnara-qa-suite.com';
const TEST_PASSWORD = __ENV.TEST_PASSWORD || 'Client1QA123!';

const errorRate = new Rate('errors');
const scanCreateDuration = new Trend('scan_create_duration');
const scanGetDuration = new Trend('scan_get_duration');

export const options = {
  stages: [
    { duration: '30s', target: 1 },
    { duration: '1m', target: 10 },
    { duration: '2m', target: 50 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    errors: ['rate<0.01'],
  },
};

export default function () {
  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  const loginOk = check(loginRes, {
    'login: status is 200': (r) => r.status === 200,
    'login: has access_token': (r) => !!r.json('access_token'),
  });
  errorRate.add(!loginOk);
  if (!loginOk) {
    sleep(1);
    return;
  }

  const token = loginRes.json('access_token');
  const authHeaders = { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } };

  const createRes = http.post(
    `${BASE_URL}/scans`,
    JSON.stringify({
      target: `k6-load-${__VU}-${__ITER}.qa.internal`,
      authorization_confirmed: true,
      authorization_justification: 'k6 load-test synthetic scan, in-house target only.',
    }),
    authHeaders,
  );
  scanCreateDuration.add(createRes.timings.duration);
  const createOk = check(createRes, {
    'create scan: status is 201': (r) => r.status === 201,
    'create scan: has scan_id': (r) => !!r.json('scan_id'),
  });
  errorRate.add(!createOk);

  if (createOk) {
    const scanId = createRes.json('scan_id');

    const getRes = http.get(`${BASE_URL}/scans/${scanId}`, authHeaders);
    scanGetDuration.add(getRes.timings.duration);
    errorRate.add(!check(getRes, { 'get scan: status is 200': (r) => r.status === 200 }));

    const vulnRes = http.get(`${BASE_URL}/scans/${scanId}/vulnerabilities`, authHeaders);
    errorRate.add(!check(vulnRes, { 'list vulnerabilities: status is 200': (r) => r.status === 200 }));
  }

  const listRes = http.get(`${BASE_URL}/scans`, authHeaders);
  errorRate.add(!check(listRes, { 'list scans: status is 200': (r) => r.status === 200 }));

  sleep(1);
}

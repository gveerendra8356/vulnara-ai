# Vulnara — Multi-Role Test Scan Results

_Generated: 2026-11-06 09:23 · Backend: https://vulnara-backend.onrender.com_

All targets are sanctioned public practice hosts (pentest-ground.com, scanme.nmap.org).


## Summary

| Role / User | Department | Target | Status | Findings | Severities |
|---|---|---|---|---|---|
| admin@vulnara.com | ALL (admin) | `scanme.nmap.org` | COMPLETED | 2 | MEDIUM:2 |
| it.analyst@vulnara.com | scoped | `https://pentest-ground.com:4280` | COMPLETED | 5 | CRITICAL:1, HIGH:3, LOW:1 |
| finance.analyst@vulnara.com | scoped | `pentest-ground.com:6379` | COMPLETED | 7 | CRITICAL:1, HIGH:3, INFO:2, LOW:1 |
| hr.analyst@vulnara.com | scoped | `https://pentest-ground.com:5013` | COMPLETED | 5 | CRITICAL:1, HIGH:3, LOW:1 |
| eng.analyst@vulnara.com | scoped | `https://pentest-ground.com:9000` | COMPLETED | 5 | CRITICAL:1, HIGH:2, LOW:1, MEDIUM:1 |
| ops.analyst@vulnara.com | scoped | `https://pentest-ground.com:81` | COMPLETED | 5 | CRITICAL:1, HIGH:3, LOW:1 |

## Detailed findings

### admin@vulnara.com  →  `scanme.nmap.org`
- Role: **admin** · Active AI Testing: **False** · Scan: `aee4df1f-d7d8-4b10-b99f-2c69d53a25af` · Status: **COMPLETED**

| Severity | CVE | Host:Port | Service | CVSS | AI reasoning (excerpt) |
|---|---|---|---|---|---|
| MEDIUM | — | scanme.nmap.org:80 | http | — | Apache 2.4.7 (released in 2013) is out of support and contains multiple publicly disclosed vulnerabilities. Even without a specific CVE match, the version itself is a security concern and should be upgraded to a supporte |
| MEDIUM | — | scanme.nmap.org:22 | ssh | — | OpenSSH 6.6.1 is several years old and has known vulnerabilities (e.g., CVE-2016-0777, CVE-2016-0778). While no specific CVE was supplied, the outdated version represents a moderate security risk and should be upgraded. |

### it.analyst@vulnara.com  →  `https://pentest-ground.com:4280`
- Role: **analyst** · Active AI Testing: **True** · Scan: `eae73e6a-4a12-40e7-b3bf-771e63f252e9` · Status: **COMPLETED**

| Severity | CVE | Host:Port | Service | CVSS | AI reasoning (excerpt) |
|---|---|---|---|---|---|
| HIGH | — | pentest-ground.com:6379 | redis | — | Redis instances are often unauthenticated by default. The scan shows an open Redis port with no authentication banner, indicating that an attacker could connect and issue commands without credentials, which is a high‑ris |
| CRITICAL | CVE-2016-8339 | pentest-ground.com:6379 | redis | 9.8 | This critical buffer overflow affects Redis 3.2.x prior to 3.2.4. The scan did not disclose the Redis version, so we cannot verify if the instance falls in that range, but the potential impact is severe, warranting a low |
| LOW | CVE-2013-7458 | pentest-ground.com:6379 | redis | 3.3 | This issue affects Redis versions prior to 3.2.3. Since the exact version is unknown, we cannot be certain, but the vulnerability may be present, so we flag it with low confidence. |
| HIGH | CVE-2015-8080 | pentest-ground.com:6379 | redis | 7.5 | This CVE targets Redis 2.8.x before 2.8.24 and 3.0.x before 3.0.6. Without version information we cannot know if the server is vulnerable, but the risk cannot be ruled out, so we note it with low confidence. |
| HIGH | CVE-2015-4335 | pentest-ground.com:6379 | redis | 10.0 | This CVE affects Redis versions before 2.8.21 and 3.x before 3.0.2. Because the scan did not reveal the Redis version, we cannot confirm whether the running instance is within the vulnerable range, but the possibility ex |

### finance.analyst@vulnara.com  →  `pentest-ground.com:6379`
- Role: **analyst** · Active AI Testing: **False** · Scan: `08ac9d49-8915-431e-9c54-4f3ec3c9dca5` · Status: **COMPLETED**

| Severity | CVE | Host:Port | Service | CVSS | AI reasoning (excerpt) |
|---|---|---|---|---|---|
| INFO | — | pentest-ground.com:443 | https | — | The HTTPS service also runs nginx/1.31.8. No CVE matches were found for this exact version, and the banner does not reveal any misconfiguration, so the finding is informational. |
| INFO | — | pentest-ground.com:80 | http | — | The web server reports nginx version 1.31.8. No specific CVE was matched, but the version is relatively recent and no known critical vulnerabilities are publicly disclosed for this exact release. No immediate risk is ide |
| HIGH | — | pentest-ground.com:6379 | redis | — | The Redis service is reachable without authentication (no password was required to connect). Unauthenticated access to a Redis server allows an attacker to read, modify, or delete data and to execute arbitrary commands,  |
| CRITICAL | CVE-2016-8339 | pentest-ground.com:6379 | redis | 9.8 | CVE-2016-8339 targets Redis 3.2.x prior to 3.2.4 and describes a buffer overflow that can lead to remote code execution. Since the Redis version was not disclosed, we cannot confirm if the instance is patched, so we flag |
| LOW | CVE-2013-7458 | pentest-ground.com:6379 | redis | 3.3 | CVE-2013-7458 applies to Redis versions before 3.2.3 where the .rediscli_history file is world‑readable. Because the exact version is unknown, we cannot rule the issue out, but the impact is limited to local users, so we |
| HIGH | CVE-2015-8080 | pentest-ground.com:6379 | redis | 7.5 | CVE-2015-8080 impacts Redis 2.8.x before 2.8.24 and 3.0.x before 3.0.6, causing an integer overflow in Lua handling. Without a version banner we cannot tell if the server is vulnerable, so we flag it as a potential issue |
| HIGH | CVE-2015-4335 | pentest-ground.com:6379 | redis | 10.0 | CVE-2015-4335 affects Redis versions prior to 2.8.21 and 3.0.2, allowing execution of arbitrary Lua bytecode. Because the scan did not reveal the Redis version, we cannot confirm whether the running instance is within th |

### hr.analyst@vulnara.com  →  `https://pentest-ground.com:5013`
- Role: **analyst** · Active AI Testing: **True** · Scan: `79fbf1a3-e129-4897-a017-5a22f0715ec8` · Status: **COMPLETED**

| Severity | CVE | Host:Port | Service | CVSS | AI reasoning (excerpt) |
|---|---|---|---|---|---|
| HIGH | — | pentest-ground.com:6379 | redis | — | Redis is reachable on its default port without any authentication required. An unauthenticated Redis instance can allow attackers to read or modify data, execute Lua scripts, or, if the server runs a vulnerable version,  |
| CRITICAL | CVE-2016-8339 | pentest-ground.com:6379 | redis | 9.8 | This critical buffer overflow affects Redis 3.2.x prior to 3.2.4 via a crafted CONFIG SET command. Since the Redis version was not revealed, we cannot confirm vulnerability, but the potential impact is severe, so we flag |
| LOW | CVE-2013-7458 | pentest-ground.com:6379 | redis | 3.3 | The CVE describes world‑readable .rediscli_history files in Redis versions before 3.2.3. Because the version is unknown, we cannot know if this applies, so we note it as a low‑severity possibility. |
| HIGH | CVE-2015-8080 | pentest-ground.com:6379 | redis | 7.5 | This vulnerability impacts Redis 2.8.x before 2.8.24 and 3.0.x before 3.0.6 via an integer overflow in Lua handling. Without version information we cannot tell if the instance falls in that range, so we flag it as a poss |
| HIGH | CVE-2015-4335 | pentest-ground.com:6379 | redis | 10.0 | This CVE affects Redis versions prior to 2.8.21 and 3.0.2, allowing execution of arbitrary Lua bytecode. Because the exact Redis version is not disclosed, we cannot confirm whether the running instance is vulnerable, so  |

### eng.analyst@vulnara.com  →  `https://pentest-ground.com:9000`
- Role: **analyst** · Active AI Testing: **True** · Scan: `c994a0c8-f6ef-4db7-a926-24763fe641a4` · Status: **COMPLETED**

| Severity | CVE | Host:Port | Service | CVSS | AI reasoning (excerpt) |
|---|---|---|---|---|---|
| MEDIUM | — | pentest-ground.com:6379 | redis | — | Redis is reachable on the network without authentication. An unauthenticated Redis instance can allow attackers to read, modify, or delete data and, in some configurations, execute arbitrary commands. This exposure is a  |
| CRITICAL | CVE-2016-8339 | pentest-ground.com:6379 | redis | 9.8 | This critical buffer‑overflow vulnerability affects Redis 3.2.x prior to 3.2.4. Because the exact version is not known, we cannot confirm exposure, but the risk is serious enough to flag with low confidence. |
| LOW | CVE-2013-7458 | pentest-ground.com:6379 | redis | 3.3 | This CVE concerns world‑readable .rediscli_history files in Redis versions before 3.2.3. The version is unknown, so we cannot say definitively whether it applies, but we note the risk with low confidence. |
| HIGH | CVE-2015-8080 | pentest-ground.com:6379 | redis | 7.5 | This vulnerability impacts Redis 2.8.x before 2.8.24 and 3.0.x before 3.0.6. Without a disclosed version we cannot know if the instance falls in that range, so we mark it as a potential issue with low confidence. |
| HIGH | CVE-2015-4335 | pentest-ground.com:6379 | redis | 10.0 | This CVE affects Redis versions before 2.8.21 and 3.x before 3.0.2. Because the exact Redis version is not disclosed, we cannot confirm whether the running instance is vulnerable, but the possibility exists, so we flag i |

### ops.analyst@vulnara.com  →  `https://pentest-ground.com:81`
- Role: **analyst** · Active AI Testing: **True** · Scan: `0fa0df3b-09e7-47af-95ad-b57d9fe9a4c0` · Status: **COMPLETED**

| Severity | CVE | Host:Port | Service | CVSS | AI reasoning (excerpt) |
|---|---|---|---|---|---|
| HIGH | — | pentest-ground.com:6379 | redis | — | Redis is exposed on its default port without authentication. Unauthenticated access allows an attacker to read, modify, or delete data and potentially use the server for malicious purposes. This configuration is a known  |
| CRITICAL | CVE-2016-8339 | pentest-ground.com:6379 | redis | 9.8 | A buffer overflow in Redis 3.2.x prior to 3.2.4 can lead to arbitrary code execution via a crafted CONFIG SET command. The exact Redis version is unknown, so we cannot definitively say the server is vulnerable, but the r |
| LOW | CVE-2013-7458 | pentest-ground.com:6379 | redis | 3.3 | This CVE describes world‑readable permissions on a Redis history file in versions before 3.2.3. If the server runs an older version, local users could read the file, but we lack version data to confirm. |
| HIGH | CVE-2015-8080 | pentest-ground.com:6379 | redis | 7.5 | This vulnerability impacts Redis 2.8.x before 2.8.24 and 3.0.x before 3.0.6, causing a possible denial‑of‑service or sandbox bypass via a crafted Lua number. Without version information we cannot be certain, but the issu |
| HIGH | CVE-2015-4335 | pentest-ground.com:6379 | redis | 10.0 | This CVE affects Redis versions before 2.8.21 and 3.x before 3.0.2, allowing remote code execution via Lua bytecode. Because the exact Redis version is unknown, we cannot confirm if the server is vulnerable, but the risk |

# Vulnara — System Diagrams

Diagrams for the project report. They are written in **Mermaid**, which renders
automatically on GitHub and in most Markdown tools (VS Code with the Mermaid
extension, Typora, Obsidian, HackMD). To export an image, paste a block into
<https://mermaid.live> and download the SVG/PNG.

---

## 1. System Architecture

```mermaid
flowchart TB
    subgraph Clients
        WEB["React Web Dashboard<br/>(GitHub Pages)"]
        MOB["Flutter Mobile App<br/>(Android / iOS)"]
    end

    subgraph Backend["FastAPI Backend (Render)"]
        API["REST API + Auth (JWT)"]
        WS["WebSocket Manager<br/>(live scan status)"]
        SCAN["Scanner<br/>(recon + active testing)"]
        TRIAGE["AI Triage Pipeline"]
        REM["Remediation Service"]
        ML["ML Priority Predictor<br/>(Logistic Regression)"]
    end

    DB[("Neon PostgreSQL")]
    NVD["NVD CVE Database<br/>(external API)"]
    GROQ["Groq LLM API<br/>(gpt-oss-120b)"]
    FCM["Firebase Cloud<br/>Messaging"]

    WEB -- HTTPS / WSS --> API
    MOB -- HTTPS / WSS --> API
    WEB -. live updates .- WS
    MOB -. live updates .- WS

    API --> DB
    API --> SCAN
    SCAN --> TRIAGE
    TRIAGE --> NVD
    TRIAGE --> GROQ
    REM --> GROQ
    API --> ML
    SCAN --> WS
    API --> FCM
    TRIAGE --> DB
    REM --> DB
```

---

## 2. Scan Data-Flow Pipeline

```mermaid
flowchart LR
    A["Authorized scan request<br/>(target + justification)"] --> B["Recon<br/>host discovery · port scan · banner grab"]
    B --> C["Normalize results<br/>(hosts / ports / services)"]
    C --> D["AI Triage"]
    D --> D1["Retrieve candidate CVEs<br/>(NVD keyword search)"]
    D1 --> D2["LLM reasons on applicability<br/>→ severity + confidence"]
    D2 --> E{"Active AI<br/>Testing on?"}
    E -- yes --> F["Fire SQLi/XSS/CMDi payloads<br/>→ differential response analysis<br/>→ LLM verifies exploit"]
    E -- no --> G
    F --> G["Persist findings<br/>(CVE, CVSS, reasoning)"]
    G --> H["ML Priority Predictor<br/>→ exploit-likelihood score"]
    G --> I["On demand: AI Remediation<br/>→ fix script"]
    I --> J["Approve → Mark Executed<br/>(closed loop)"]
```

---

## 3. Entity-Relationship (Database)

```mermaid
erDiagram
    DEPARTMENTS ||--o{ USERS : "scopes"
    DEPARTMENTS ||--o{ SCANS : "owns"
    USERS ||--o{ SCANS : "initiates"
    SCANS ||--o{ VULNERABILITIES : "has"
    SCANS ||--o{ THREAT_LOGS : "records"
    CVE_DEFINITIONS ||--o{ VULNERABILITIES : "classifies"
    VULNERABILITIES ||--o{ REMEDIATIONS : "fixed by"
    VULNERABILITIES ||--o{ THREAT_LOGS : "tested in"

    DEPARTMENTS {
        uuid department_id PK
        string name
        string description
    }
    USERS {
        uuid user_id PK
        string email
        string password_hash
        string role
        uuid department_id FK
        bool is_active
    }
    SCANS {
        uuid scan_id PK
        uuid user_id FK
        uuid department_id FK
        string target
        string status
        bool active_testing_enabled
    }
    VULNERABILITIES {
        uuid vuln_id PK
        uuid scan_id FK
        string cve_id FK
        string host
        int port
        string severity
        float cvss_score
        float confidence_score
        string ai_reasoning
        string status
    }
    CVE_DEFINITIONS {
        string cve_id PK
        float cvss_v3_score
        string severity
    }
    REMEDIATIONS {
        uuid remediation_id PK
        uuid vuln_id FK
        string technical_script
        float ai_confidence
        string status
    }
    THREAT_LOGS {
        uuid log_id PK
        uuid scan_id FK
        uuid vuln_id FK
        string attack_type
        string payload_used
        bool ai_verified
    }
```

---

## 4. Sequence — A Scan from Start to Finding

```mermaid
sequenceDiagram
    actor Analyst
    participant Web
    participant API as FastAPI
    participant Scanner
    participant NVD
    participant Groq as Groq LLM
    participant DB
    participant WS as WebSocket

    Analyst->>Web: New scan (target + authorize)
    Web->>API: POST /scans (JWT)
    API->>DB: insert Scan (PENDING, department_id)
    API-->>Web: 201 scan_id
    API->>Scanner: start background task
    Scanner->>WS: status IN_PROGRESS
    WS-->>Web: live update
    Scanner->>Scanner: recon (ports, services)
    Scanner->>NVD: candidate CVEs for service
    NVD-->>Scanner: CVE list
    Scanner->>Groq: triage (service + CVEs)
    Groq-->>Scanner: applicable? severity, confidence, reasoning
    Scanner->>DB: insert Vulnerabilities
    Scanner->>WS: status COMPLETED + severity counts
    WS-->>Web: live update
    Analyst->>Web: open finding
    Web->>API: GET /scans/{id}/vulnerabilities
    API-->>Web: findings (CVE, CVSS, AI reasoning)
```

---

## 5. RBAC & Department Scoping

```mermaid
flowchart TD
    REQ["Request + JWT"] --> AUTH["Resolve CurrentUser<br/>(role, department_id)"]
    AUTH --> ROLE{"role == admin?"}
    ROLE -- yes --> ALL["See ALL scans / activity<br/>(every department)"]
    ROLE -- no --> DEP{"has department?"}
    DEP -- yes --> SCOPED["Filter WHERE<br/>department_id = user's dept"]
    DEP -- no --> OWN["Filter WHERE<br/>user_id = self"]
    ALL --> RESP["Response"]
    SCOPED --> RESP
    OWN --> RESP
```

---

## 6. Machine-Learning Pipeline (Priority Predictor)

```mermaid
flowchart LR
    DG["Dataset generator<br/>(documented domain labels + noise)"] --> DS["dataset.csv<br/>(9 features, 5000 rows)"]
    DS --> SPLIT["Stratified 75/25 split<br/>+ 5-fold CV"]
    SPLIT --> TRAIN["Train & compare:<br/>LogReg · DecisionTree · RandomForest"]
    TRAIN --> EVAL["Evaluate<br/>accuracy · precision · recall · F1 · ROC-AUC"]
    EVAL --> PICK["Select Logistic Regression<br/>(best F1, interpretable)"]
    PICK --> EXP["Export weights →<br/>app/ml/model_params.json"]
    EXP --> INF["Runtime inference (pure numpy)<br/>sigmoid((x-μ)/σ · w + b)"]
    INF --> EP["API: /ml/risk-score,<br/>/scans/{id}/risk"]
```

"""
security/endpoint_inventory.py

Phase 1-2 deliverable: static backend + API discovery for the FastAPI backend.
Parses app/api/routes/*.py, extracts every route (method + path + handler),
infers whether authentication is required (the handler depends on
get_current_user) and the expected role (admin-only handlers reference the
"admin" role / an admin dependency), and writes:

  <out>/endpoint-inventory.xlsx   (Endpoint Inventory sheet)
  <out>/backend-inventory.md      (framework/auth/db summary + API table)

Pure standard library + openpyxl; no app import, so it runs anywhere.

Usage:  python security/endpoint_inventory.py [--routes backend/app/api/routes] [--out "Vulnerability Test Results"]
"""

from __future__ import annotations

import argparse
import os
import re

DECORATOR = re.compile(r"@router\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']", re.I)
DEF_LINE = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)")


def _analyze_file(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    routes = []
    i = 0
    while i < len(lines):
        m = DECORATOR.search(lines[i])
        if not m:
            i += 1
            continue
        method, route = m.group(1).upper(), m.group(2)

        # Collect the handler block: from here to the next decorator or EOF.
        j = i + 1
        handler = None
        block = []
        while j < len(lines):
            dl = DEF_LINE.match(lines[j])
            if dl and handler is None:
                handler = dl.group(1)
            if j > i + 1 and lines[j].lstrip().startswith("@router."):
                break
            block.append(lines[j])
            j += 1
        body = "".join(block)

        auth = "get_current_user" in body or "CurrentUser" in body or "Depends(get_current" in body
        # role inference
        roles = "admin, analyst"
        if "require_admin" in body or re.search(r'role\s*!=\s*["\']admin["\']', body) \
           or re.search(r'role\s+not\s+in\s*\(?\[?["\']admin', body) or '/admin' in route:
            roles = "admin"
        if not auth:
            roles = "public"

        routes.append({
            "method": method,
            "path": route,
            "handler": handler or "?",
            "auth": "Yes" if auth else "No",
            "roles": roles,
            "file": os.path.relpath(path).replace("\\", "/"),
        })
        i = i + 1
    return routes


def discover(routes_dir: str) -> list[dict]:
    all_routes = []
    for name in sorted(os.listdir(routes_dir)):
        if name.endswith(".py") and name != "__init__.py":
            all_routes.extend(_analyze_file(os.path.join(routes_dir, name)))
    # Stable sort by path then method
    all_routes.sort(key=lambda r: (r["path"], r["method"]))
    return all_routes


BACKEND_INVENTORY = """# Backend Inventory

| Property | Detected value |
|---|---|
| **Framework** | FastAPI (async) |
| **Language** | Python 3.12 |
| **API architecture** | REST (JSON over HTTPS) + WebSocket for live scan events |
| **Authentication** | JWT (HS256) bearer tokens; access + refresh; bcrypt password hashing |
| **Authorization** | Role-based (admin / analyst) + department-scoped row filtering |
| **Database** | PostgreSQL (Neon) in prod, SQLite locally — via `DATABASE_URL` |
| **ORM** | SQLAlchemy 2.0 (async) |
| **API docs** | FastAPI automatic OpenAPI (`/docs`, `/openapi.json`) |
| **Middleware** | CORS; JWT auth dependency (`get_current_user`) |
| **File uploads** | None (no multipart upload endpoints) |
| **Session handling** | Stateless JWT (no server session); refresh-token denylist on logout |
| **Third-party integrations** | Groq (LLM), NVD (CVE data), Firebase Cloud Messaging (push) |
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--routes", default=os.path.join("backend", "app", "api", "routes"))
    ap.add_argument("--out", default="Vulnerability Test Results")
    args = ap.parse_args()

    routes = discover(args.routes)
    os.makedirs(args.out, exist_ok=True)

    # ---- Excel ----
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Endpoint Inventory"
    head = Font(bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="1F4E78")
    cols = ["Endpoint", "HTTP Method", "Authentication Required", "Expected Roles", "Controller/File Path"]
    ws.append(cols)
    for c in ws[1]:
        c.font = head
        c.fill = fill
    for r in routes:
        ws.append([r["path"], r["method"], r["auth"], r["roles"], f'{r["file"]} :: {r["handler"]}'])
    ws.freeze_panes = "A2"
    for col, w in zip("ABCDE", (34, 12, 14, 16, 46)):
        ws.column_dimensions[col].width = w
    wb.save(os.path.join(args.out, "endpoint-inventory.xlsx"))

    # ---- Markdown ----
    md = [BACKEND_INVENTORY, "## API Inventory", "",
          f"Discovered **{len(routes)}** routes across `{args.routes}`.", "",
          "| Endpoint | Method | Auth | Roles | File :: Handler |",
          "|---|---|---|---|---|"]
    for r in routes:
        md.append(f"| `{r['path']}` | {r['method']} | {r['auth']} | {r['roles']} | `{r['file']}::{r['handler']}` |")
    with open(os.path.join(args.out, "backend-inventory.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    pub = sum(1 for r in routes if r["auth"] == "No")
    print(f"Discovered {len(routes)} routes ({pub} public, {len(routes)-pub} authenticated). "
          f"Wrote endpoint-inventory.xlsx + backend-inventory.md to '{args.out}'.")


if __name__ == "__main__":
    main()

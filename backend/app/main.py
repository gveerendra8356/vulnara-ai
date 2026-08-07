"""
main.py

Minimal FastAPI app entrypoint, just enough to show the routers built
across Task 3 (scans) and Task 4 (remediations) actually mount together.
Auth routes (Task 2's /auth/*) aren't implemented yet -- app/core/auth.py
is still the stub described in Task 3 -- so this app is runnable for
import/schema-validation purposes but not a full working server until
that module exists for real.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.routes.scans import router as scans_router
from app.api.routes.remediations import router as remediations_router
from app.api.routes.devices import router as devices_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Vulnara API")

app.include_router(scans_router, tags=["scans"])
app.include_router(remediations_router, tags=["remediations"])
app.include_router(devices_router, tags=["devices"])


@app.get("/health")
async def health():
    return {"status": "ok"}
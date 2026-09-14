"""
main.py — FastAPI application entry point.

Endpoints:
    GET  /health
    POST /signals   — Drug safety signal detection (PRR + LLM rationale)
    POST /readiness — CTD submission readiness check (ICH M4 diff + gap report)
"""

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure sibling packages are importable when running via uvicorn from src/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.models import (
    HealthResponse,
    ReadinessRequest,
    ReadinessResponse,
    SignalsRequest,
    SignalsResponse,
)
from backend.prr import compute_prr
from backend.readiness import check_readiness
from data.openfda_client import fetch_faers_reports
from llm.client import generate
from llm.prompts import build_gap_report_prompt, build_signal_rationale_prompt

app = FastAPI(
    title="Drug Safety Signal Detector & Submission Readiness Checker",
    description=(
        "Two-mode AI platform: "
        "(1) detect adverse drug safety signals from FDA FAERS data using PRR statistics, "
        "(2) check CTD dossier completeness against ICH M4 standard."
    ),
    version="1.0.0",
)

import os as _os
_CORS_ORIGINS = [
    o.strip()
    for o in _os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    return {"status": "ok", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Mode 1 — Signal Detection
# ---------------------------------------------------------------------------

@app.post("/signals", response_model=SignalsResponse, tags=["Signal Detection"])
def signals(req: SignalsRequest):
    """
    Fetch FAERS adverse event reports for *drug_name*, compute PRR for all
    drug–event pairs, flag signals with PRR >= 2.0 and count >= 3, then
    use IBM watsonx.ai to generate a plain-language rationale for each signal.
    """
    # 1. Fetch data
    fetched = fetch_faers_reports(req.drug_name, limit=req.limit)
    reports = fetched["results"]
    fallback_used = fetched["fallback_used"]

    if not reports:
        return SignalsResponse(
            drug_name=req.drug_name,
            total_reports=0,
            fallback_used=fallback_used,
            signals=[],
        )

    # 2. Compute PRR
    flagged = compute_prr(reports, req.drug_name)

    # 3. LLM rationale for top signals (cap at 10 to keep prompt size reasonable)
    top = flagged[:10]
    if top:
        rationale_text = generate(build_signal_rationale_prompt(top))
        # Parse numbered list back into per-signal rationale
        rationale_lines = _parse_numbered_list(rationale_text, len(top))
        for i, sig in enumerate(top):
            sig["rationale"] = rationale_lines[i] if i < len(rationale_lines) else rationale_text

    return SignalsResponse(
        drug_name=req.drug_name,
        total_reports=len(reports),
        fallback_used=fallback_used,
        signals=top,
    )


# ---------------------------------------------------------------------------
# Mode 2 — Submission Readiness
# ---------------------------------------------------------------------------

@app.post("/readiness", response_model=ReadinessResponse, tags=["Submission Readiness"])
def readiness(req: ReadinessRequest):
    """
    Diff *outline* against the ICH M4 CTD checklist, score completeness per
    module, then use IBM watsonx.ai to generate a regulatory gap report.
    """
    if not req.outline:
        raise HTTPException(status_code=400, detail="outline must contain at least one section")

    # 1. Check readiness
    result = check_readiness(req.outline)

    # 2. Build missing-by-module dict for LLM prompt
    missing_by_module = {
        f"{m['module']} — {m['module_name']}": m["missing"]
        for m in result["modules"]
        if m["missing"]
    }

    # 3. LLM gap report
    gap_report = ""
    if missing_by_module:
        gap_report = generate(build_gap_report_prompt(missing_by_module))

    return ReadinessResponse(
        overall_score=result["overall_score"],
        modules=result["modules"],
        gap_report=gap_report,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_numbered_list(text: str, expected: int) -> list[str]:
    """
    Split a numbered-list LLM response into individual items.
    Falls back to returning the full text for every item if parsing fails.
    """
    import re
    parts = re.split(r"\n\s*\d+[\.\)]\s*", text)
    # Remove leading empty string from split
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= expected:
        return parts[:expected]
    # Fallback: return full text for all
    return [text] * expected

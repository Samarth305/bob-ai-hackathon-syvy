"""
models.py — Pydantic request/response schemas for the FastAPI endpoints.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# POST /signals
# ---------------------------------------------------------------------------

class SignalsRequest(BaseModel):
    drug_name: str = Field(..., min_length=1, description="Drug name to search in FAERS")
    limit: int = Field(1000, ge=10, le=1000, description="Max reports to fetch from openFDA")


class SignalItem(BaseModel):
    drug: str
    adverse_event: str
    prr: float
    report_count: int
    rationale: str = ""


class SignalsResponse(BaseModel):
    drug_name: str
    total_reports: int
    fallback_used: bool
    signals: list[SignalItem]


# ---------------------------------------------------------------------------
# POST /readiness
# ---------------------------------------------------------------------------

class ReadinessRequest(BaseModel):
    outline: list[str] = Field(..., min_length=1, description="List of CTD section titles present in the dossier")


class ModuleResult(BaseModel):
    module: str
    module_name: str
    score: float
    present: int
    required: int
    missing: list[str]
    present_sections: list[str]


class ReadinessResponse(BaseModel):
    overall_score: float
    modules: list[ModuleResult]
    gap_report: str = ""


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str

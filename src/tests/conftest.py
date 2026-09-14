"""
conftest.py — shared pytest fixtures for unit and integration tests.
"""

import json
import sys
from pathlib import Path

import pytest

# Make sibling packages importable when pytest runs from src/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Minimal synthetic FAERS report builders
# ---------------------------------------------------------------------------

def _make_report(drug: str, event: str, safetyreportid: str = "0") -> dict:
    """Build a minimal FAERS-shaped report dict."""
    return {
        "safetyreportid": safetyreportid,
        "patient": {
            "drug": [{"medicinalproduct": drug}],
            "reaction": [{"reactionmeddrapt": event}],
        },
    }


# ---------------------------------------------------------------------------
# Sample report list — a 10-report dataset with controlled frequencies
#
# DRUG_A: event X  ×5,  event Y  ×1
# DRUG_B: event X  ×1,  event Y  ×3
#
# For DRUG_A + event X:
#   a=5, b=1, c=1, d=3  → N=10
#   PRR = (5/6) / (1/4) = 3.33
#   χ²  = 10*(5*3 - 1*1)² / (6*4*6*4) = 10*196/576 ≈ 3.40   → below 4.0
#
# For DRUG_B + event Y:
#   a=3, b=1, c=1, d=5  → N=10
#   PRR = (3/4) / (1/6) = 4.50
#   χ²  = 10*(3*5 - 1*1)² / (4*6*4*6) = 10*196/576 ≈ 3.40   → below 4.0
# ---------------------------------------------------------------------------

@pytest.fixture
def small_reports():
    """10-report synthetic dataset with two drugs and two events."""
    reports = []
    for i in range(5):
        reports.append(_make_report("DRUG_A", "EVENT_X", str(i)))
    reports.append(_make_report("DRUG_A", "EVENT_Y", "5"))
    reports.append(_make_report("DRUG_B", "EVENT_X", "6"))
    for i in range(3):
        reports.append(_make_report("DRUG_B", "EVENT_Y", str(7 + i)))
    return reports


# ---------------------------------------------------------------------------
# Larger dataset built from sample_faers.json
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_reports():
    """Load the bundled sample_faers.json (101 reports)."""
    sample_path = Path(__file__).resolve().parent.parent / "data" / "sample_faers.json"
    with open(sample_path, encoding="utf-8") as f:
        raw = json.load(f)
    return raw if isinstance(raw, list) else raw.get("results", [])


# ---------------------------------------------------------------------------
# Full CTD checklist outline (all sections present)
# ---------------------------------------------------------------------------

@pytest.fixture
def full_ctd_outline():
    """An outline that contains every CTD section ID — score should be 100%."""
    from data.ctd_checklist import CTD_CHECKLIST
    lines = []
    for mod in CTD_CHECKLIST:
        for sec in mod["sections"]:
            lines.append(f"{sec['id']} {sec['title']}")
    return lines


@pytest.fixture
def partial_ctd_outline():
    """Outline with only Module 1 and 2.3 present."""
    return [
        "1.0 Cover letter",
        "1.1 Comprehensive table of contents",
        "1.2 Application form",
        "1.3 Prescribing information and labeling",
        "1.4 Information about the experts",
        "1.5 Environmental assessment or exclusion",
        "1.6 Patent certifications and financial disclosure",
        "2.3 Quality overall summary",
    ]


@pytest.fixture
def empty_ctd_outline():
    """Completely empty outline — every section should be missing."""
    return ["Unrelated text with no matching IDs"]


# ---------------------------------------------------------------------------
# FastAPI test client (integration tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    """
    Return a TestClient for the FastAPI app.
    The LLM generate() call is NOT mocked here — the app naturally returns
    the stub string when watsonx credentials are absent.
    """
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)

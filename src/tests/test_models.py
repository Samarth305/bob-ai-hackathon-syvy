"""
test_models.py — Unit tests for src/backend/models.py (Pydantic schemas)

Covers:
  - SignalsRequest validation (required fields, constraints)
  - SignalItem construction and field defaults
  - SignalsResponse serialisation round-trip
  - ReadinessRequest validation
  - ModuleResult construction
  - ReadinessResponse serialisation round-trip
  - HealthResponse
  - Extra keys from compute_prr dict (a/b/c/d) are silently dropped
"""

import pytest
from pydantic import ValidationError

from backend.models import (
    HealthResponse,
    ModuleResult,
    ReadinessRequest,
    ReadinessResponse,
    SignalItem,
    SignalsRequest,
    SignalsResponse,
)


# ---------------------------------------------------------------------------
# SignalsRequest
# ---------------------------------------------------------------------------

class TestSignalsRequest:
    def test_valid_minimal(self):
        req = SignalsRequest(drug_name="aspirin")
        assert req.drug_name == "aspirin"
        assert req.limit == 1000  # default

    def test_custom_limit(self):
        req = SignalsRequest(drug_name="ibuprofen", limit=100)
        assert req.limit == 100

    def test_empty_drug_name_rejected(self):
        with pytest.raises(ValidationError):
            SignalsRequest(drug_name="")

    def test_limit_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            SignalsRequest(drug_name="aspirin", limit=5)

    def test_limit_above_maximum_rejected(self):
        with pytest.raises(ValidationError):
            SignalsRequest(drug_name="aspirin", limit=1001)

    def test_limit_boundary_10_accepted(self):
        req = SignalsRequest(drug_name="aspirin", limit=10)
        assert req.limit == 10

    def test_limit_boundary_1000_accepted(self):
        req = SignalsRequest(drug_name="aspirin", limit=1000)
        assert req.limit == 1000

    def test_missing_drug_name_rejected(self):
        with pytest.raises(ValidationError):
            SignalsRequest()


# ---------------------------------------------------------------------------
# SignalItem
# ---------------------------------------------------------------------------

class TestSignalItem:
    def _item(self, **kwargs):
        defaults = {
            "drug": "ASPIRIN",
            "adverse_event": "GASTROINTESTINAL HAEMORRHAGE",
            "prr": 9.56,
            "report_count": 5,
            "chi_square": 15.60,
        }
        defaults.update(kwargs)
        return SignalItem(**defaults)

    def test_valid_construction(self):
        item = self._item()
        assert item.drug == "ASPIRIN"
        assert item.prr == 9.56
        assert item.chi_square == 15.60
        assert item.rationale == ""  # default

    def test_chi_square_field_present(self):
        item = self._item()
        assert hasattr(item, "chi_square")

    def test_chi_square_default_is_zero(self):
        item = SignalItem(
            drug="X", adverse_event="Y", prr=2.5, report_count=4
        )
        assert item.chi_square == 0.0

    def test_rationale_custom_value(self):
        item = self._item(rationale="Known GI irritant.")
        assert item.rationale == "Known GI irritant."

    def test_extra_keys_from_prr_dict_ignored(self):
        """compute_prr returns a/b/c/d — Pydantic must not crash."""
        raw = {
            "drug": "ASPIRIN",
            "adverse_event": "GI HAEMORRHAGE",
            "prr": 9.56,
            "report_count": 5,
            "chi_square": 15.60,
            "a": 5, "b": 10, "c": 15, "d": 71,  # extra fields
            "rationale": "",
        }
        item = SignalItem(**raw)
        assert item.drug == "ASPIRIN"
        assert not hasattr(item, "a")

    def test_json_serialisation_includes_chi_square(self):
        item = self._item()
        data = item.model_dump()
        assert "chi_square" in data
        assert data["chi_square"] == 15.60

    def test_missing_required_drug_rejected(self):
        with pytest.raises(ValidationError):
            SignalItem(adverse_event="X", prr=2.0, report_count=3)

    def test_missing_required_adverse_event_rejected(self):
        with pytest.raises(ValidationError):
            SignalItem(drug="ASPIRIN", prr=2.0, report_count=3)


# ---------------------------------------------------------------------------
# SignalsResponse
# ---------------------------------------------------------------------------

class TestSignalsResponse:
    def test_valid_construction(self):
        resp = SignalsResponse(
            drug_name="ASPIRIN",
            total_reports=101,
            fallback_used=False,
            signals=[],
        )
        assert resp.drug_name == "ASPIRIN"
        assert resp.signals == []

    def test_with_signal_items(self):
        item = SignalItem(
            drug="ASPIRIN",
            adverse_event="GI HAEMORRHAGE",
            prr=9.56,
            report_count=5,
            chi_square=15.60,
        )
        resp = SignalsResponse(
            drug_name="ASPIRIN",
            total_reports=101,
            fallback_used=False,
            signals=[item],
        )
        assert len(resp.signals) == 1
        assert resp.signals[0].chi_square == 15.60

    def test_json_round_trip(self):
        item = SignalItem(
            drug="ASPIRIN",
            adverse_event="GI HAEMORRHAGE",
            prr=9.56,
            report_count=5,
            chi_square=15.60,
            rationale="GI irritant.",
        )
        resp = SignalsResponse(
            drug_name="ASPIRIN",
            total_reports=101,
            fallback_used=False,
            signals=[item],
        )
        json_str = resp.model_dump_json()
        restored = SignalsResponse.model_validate_json(json_str)
        assert restored.signals[0].chi_square == 15.60
        assert restored.signals[0].rationale == "GI irritant."


# ---------------------------------------------------------------------------
# ReadinessRequest
# ---------------------------------------------------------------------------

class TestReadinessRequest:
    def test_valid_outline(self):
        req = ReadinessRequest(outline=["1.0 Cover letter", "2.3 Quality summary"])
        assert len(req.outline) == 2

    def test_empty_outline_rejected(self):
        with pytest.raises(ValidationError):
            ReadinessRequest(outline=[])

    def test_missing_outline_rejected(self):
        with pytest.raises(ValidationError):
            ReadinessRequest()


# ---------------------------------------------------------------------------
# ModuleResult
# ---------------------------------------------------------------------------

class TestModuleResult:
    def test_valid_construction(self):
        mod = ModuleResult(
            module="Module 1",
            module_name="Administrative Information",
            score=85.7,
            present=6,
            required=7,
            missing=["1.6 — Patent certifications"],
            present_sections=["Cover letter", "Application form"],
        )
        assert mod.score == 85.7
        assert len(mod.missing) == 1

    def test_empty_missing_list_valid(self):
        mod = ModuleResult(
            module="Module 1",
            module_name="Administrative Information",
            score=100.0,
            present=7,
            required=7,
            missing=[],
            present_sections=["Cover letter"],
        )
        assert mod.missing == []


# ---------------------------------------------------------------------------
# ReadinessResponse
# ---------------------------------------------------------------------------

class TestReadinessResponse:
    def test_valid_construction(self):
        resp = ReadinessResponse(overall_score=72.3, modules=[])
        assert resp.overall_score == 72.3
        assert resp.gap_report == ""  # default

    def test_gap_report_custom(self):
        resp = ReadinessResponse(overall_score=50.0, modules=[], gap_report="Missing sections in M3.")
        assert resp.gap_report == "Missing sections in M3."


# ---------------------------------------------------------------------------
# HealthResponse
# ---------------------------------------------------------------------------

class TestHealthResponse:
    def test_valid(self):
        h = HealthResponse(status="ok", version="1.0.0")
        assert h.status == "ok"
        assert h.version == "1.0.0"

    def test_missing_status_rejected(self):
        with pytest.raises(ValidationError):
            HealthResponse(version="1.0.0")

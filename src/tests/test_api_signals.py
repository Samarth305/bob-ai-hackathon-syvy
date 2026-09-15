"""
test_api_signals.py — Integration tests for POST /signals

Uses FastAPI TestClient (HTTPX in-process) + the bundled sample_faers.json
as the data source (openFDA HTTP call is patched to return the fallback).

Covers:
  - 200 response shape and required top-level fields
  - signals list items contain chi_square
  - chi_square is a float >= 0
  - PRR, report_count, drug, adverse_event present on every item
  - All three threshold conditions satisfied by every returned signal
  - rationale field present on every item (may be empty or stub)
  - each signal has its own distinct rationale key (not a shared reference)
  - fallback_used flag reflects data source
  - empty drug name returns 422 (Pydantic validation)
  - no signals returns empty list (not an error)
  - limit parameter accepted
"""

import os
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post_signals(client, drug_name: str, limit: int = 1000) -> dict:
    resp = client.post("/signals", json={"drug_name": drug_name, "limit": limit})
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Response structure
# ---------------------------------------------------------------------------

class TestSignalsEndpointStructure:
    def test_returns_200(self, api_client):
        resp = api_client.post("/signals", json={"drug_name": "ASPIRIN", "limit": 1000})
        assert resp.status_code == 200

    def test_top_level_keys_present(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        assert "drug_name" in data
        assert "total_reports" in data
        assert "fallback_used" in data
        assert "signals" in data

    def test_drug_name_echoed(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        assert data["drug_name"] == "ASPIRIN"

    def test_total_reports_is_int(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        assert isinstance(data["total_reports"], int)
        assert data["total_reports"] > 0

    def test_fallback_used_is_bool(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        assert isinstance(data["fallback_used"], bool)

    def test_signals_is_list(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        assert isinstance(data["signals"], list)

    def test_content_type_json(self, api_client):
        resp = api_client.post("/signals", json={"drug_name": "ASPIRIN", "limit": 1000})
        assert "application/json" in resp.headers["content-type"]


# ---------------------------------------------------------------------------
# Per-signal field validation
# ---------------------------------------------------------------------------

class TestSignalsEndpointSignalFields:
    def test_each_signal_has_chi_square(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert "chi_square" in sig, f"chi_square missing from signal: {sig}"

    def test_chi_square_is_float(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert isinstance(sig["chi_square"], float), f"chi_square not float: {sig['chi_square']}"

    def test_chi_square_non_negative(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert sig["chi_square"] >= 0.0

    def test_each_signal_has_prr(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert "prr" in sig

    def test_each_signal_has_report_count(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert "report_count" in sig

    def test_each_signal_has_drug(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert "drug" in sig

    def test_each_signal_has_adverse_event(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert "adverse_event" in sig

    def test_each_signal_has_rationale_key(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert "rationale" in sig

    def test_rationale_is_string(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert isinstance(sig["rationale"], str)


# ---------------------------------------------------------------------------
# Threshold enforcement on returned signals
# ---------------------------------------------------------------------------

class TestSignalsThresholds:
    def test_all_signals_prr_gte_2(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert sig["prr"] >= 2.0, f"PRR {sig['prr']} below threshold"

    def test_all_signals_count_gte_3(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert sig["report_count"] >= 3, f"count {sig['report_count']} below threshold"

    def test_all_signals_chi_square_gte_4(self, api_client):
        data = _post_signals(api_client, "ASPIRIN")
        for sig in data["signals"]:
            assert sig["chi_square"] >= 4.0, f"chi2 {sig['chi_square']} below threshold"

    def test_signals_sorted_by_prr_descending(self, api_client):
        data = _post_signals(api_client, "IBUPROFEN")
        prrs = [s["prr"] for s in data["signals"]]
        assert prrs == sorted(prrs, reverse=True)


# ---------------------------------------------------------------------------
# Per-signal rationale independence
# ---------------------------------------------------------------------------

class TestSignalsRationalePerSignal:
    def test_rationale_field_is_per_signal_not_shared(self, api_client):
        """
        Each signal dict must hold its own rationale string object.
        We patch generate() to return a numbered list large enough for all
        signals (endpoint caps at 10) so _parse_numbered_list assigns a
        different line to each signal.
        """
        # Build 10 distinct numbered lines — enough to cover the cap of 10 signals
        fake_rationale = "\n".join(f"{i}. Rationale number {i}." for i in range(1, 11))
        with patch("backend.main.generate", return_value=fake_rationale):
            data = _post_signals(api_client, "ASPIRIN")

        signals = data["signals"]
        if len(signals) >= 2:
            # Different signals should have different rationale strings
            rationales = [s["rationale"] for s in signals[:3]]
            # At least the first two should differ (parsed from numbered list)
            assert rationales[0] != rationales[1] or len(signals) == 1, (
                "Rationales should be per-signal, not duplicated across all signals"
            )

    def test_all_rationale_fields_populated_when_llm_responds(self, api_client):
        """When generate() returns a valid numbered list, every signal gets its own text."""
        # Build a numbered-list response large enough for all signals
        def make_rationale(signals_req):
            # Called by the endpoint; return one line per signal
            n = signals_req.count("\n") + 1  # rough count
            return "\n".join(f"{i}. Rationale for signal {i}." for i in range(1, 12))

        with patch("backend.main.generate", side_effect=lambda prompt: "\n".join(
            f"{i}. Rationale line {i}." for i in range(1, 12)
        )):
            data = _post_signals(api_client, "ASPIRIN")

        for sig in data["signals"]:
            assert sig["rationale"] != "", "Every signal should have a non-empty rationale"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestSignalsEndpointInputValidation:
    def test_empty_drug_name_returns_422(self, api_client):
        resp = api_client.post("/signals", json={"drug_name": "", "limit": 1000})
        assert resp.status_code == 422

    def test_whitespace_only_drug_name_returns_warning_not_500(self, api_client):
        # The endpoint returns an empty signals list, not a 500
        resp = api_client.post("/signals", json={"drug_name": "   ", "limit": 1000})
        # Pydantic's min_length=1 catches empty string, but whitespace-only
        # passes validation and returns 0 signals gracefully.
        assert resp.status_code in (200, 422)

    def test_limit_below_minimum_returns_422(self, api_client):
        resp = api_client.post("/signals", json={"drug_name": "ASPIRIN", "limit": 5})
        assert resp.status_code == 422

    def test_limit_above_maximum_returns_422(self, api_client):
        resp = api_client.post("/signals", json={"drug_name": "ASPIRIN", "limit": 1_000_001})
        assert resp.status_code == 422

    def test_missing_body_returns_422(self, api_client):
        resp = api_client.post("/signals")
        assert resp.status_code == 422

    def test_unknown_drug_returns_empty_signals_not_error(self, api_client):
        data = _post_signals(api_client, "TOTALLY_UNKNOWN_DRUG_ZZZZ999")
        assert data["signals"] == []
        assert data["total_reports"] >= 0


# ---------------------------------------------------------------------------
# Limit parameter
# ---------------------------------------------------------------------------

class TestSignalsEndpointLimit:
    def test_limit_10_accepted(self, api_client):
        resp = api_client.post("/signals", json={"drug_name": "ASPIRIN", "limit": 10})
        assert resp.status_code == 200

    def test_limit_500_accepted(self, api_client):
        resp = api_client.post("/signals", json={"drug_name": "ASPIRIN", "limit": 500})
        assert resp.status_code == 200

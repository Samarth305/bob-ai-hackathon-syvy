"""
test_openfda_client.py — Unit tests for src/data/openfda_client.py

Covers:
  - fetch_faers_reports returns correct structure
  - successful HTTP response is parsed correctly
  - 403 API_KEY_MISSING triggers fallback
  - network error triggers fallback
  - fallback loads sample_faers.json
  - fallback returns fallback_used=True
  - live path returns fallback_used=False
  - _load_fallback handles missing file gracefully
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_RESULTS = [
    {
        "safetyreportid": "TEST001",
        "patient": {
            "drug": [{"medicinalproduct": "ASPIRIN"}],
            "reaction": [{"reactionmeddrapt": "Nausea"}],
        },
    }
]

FAKE_FDA_RESPONSE = {"results": FAKE_RESULTS, "meta": {"results": {"total": 1}}}


def _make_mock_response(status_code: int, json_body: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ---------------------------------------------------------------------------
# Return structure
# ---------------------------------------------------------------------------

class TestFetchFaersReportsStructure:
    def test_returns_dict_with_required_keys(self):
        from data.openfda_client import fetch_faers_reports
        result = fetch_faers_reports("ASPIRIN_NONEXISTENT_XYZ", limit=10)
        assert "results" in result
        assert "fallback_used" in result
        assert "total_fetched" in result

    def test_results_is_list(self):
        from data.openfda_client import fetch_faers_reports
        result = fetch_faers_reports("ASPIRIN_NONEXISTENT_XYZ", limit=10)
        assert isinstance(result["results"], list)

    def test_fallback_used_is_bool(self):
        from data.openfda_client import fetch_faers_reports
        result = fetch_faers_reports("ASPIRIN_NONEXISTENT_XYZ", limit=10)
        assert isinstance(result["fallback_used"], bool)

    def test_total_fetched_is_int(self):
        from data.openfda_client import fetch_faers_reports
        result = fetch_faers_reports("ASPIRIN_NONEXISTENT_XYZ", limit=10)
        assert isinstance(result["total_fetched"], int)

    def test_total_fetched_matches_results_length(self):
        from data.openfda_client import fetch_faers_reports
        result = fetch_faers_reports("ASPIRIN_NONEXISTENT_XYZ", limit=10)
        assert result["total_fetched"] == len(result["results"])


# ---------------------------------------------------------------------------
# Successful HTTP path
# ---------------------------------------------------------------------------

class TestFetchFaersReportsLivePath:
    def test_successful_response_parsed(self):
        from data.openfda_client import fetch_faers_reports

        mock_resp = _make_mock_response(200, FAKE_FDA_RESPONSE)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("data.openfda_client.httpx.Client", return_value=mock_client):
            result = fetch_faers_reports("ASPIRIN", limit=10)

        assert result["fallback_used"] is False
        assert result["results"] == FAKE_RESULTS
        assert result["total_fetched"] == 1

    def test_successful_response_no_fallback(self):
        from data.openfda_client import fetch_faers_reports

        mock_resp = _make_mock_response(200, FAKE_FDA_RESPONSE)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("data.openfda_client.httpx.Client", return_value=mock_client):
            result = fetch_faers_reports("ASPIRIN", limit=10)

        assert result["fallback_used"] is False

    def test_api_query_uses_uppercase_drug_name(self):
        from data.openfda_client import fetch_faers_reports

        mock_resp = _make_mock_response(200, FAKE_FDA_RESPONSE)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("data.openfda_client.httpx.Client", return_value=mock_client):
            fetch_faers_reports("aspirin", limit=10)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs[1].get("params") or call_kwargs[0][1]
        assert "ASPIRIN" in params["search"]


# ---------------------------------------------------------------------------
# Fallback triggers
# ---------------------------------------------------------------------------

class TestFetchFaersReportsFallback:
    def test_network_error_triggers_fallback(self):
        from data.openfda_client import fetch_faers_reports

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("Connection refused")

        with patch("data.openfda_client.httpx.Client", return_value=mock_client):
            result = fetch_faers_reports("ASPIRIN", limit=10)

        assert result["fallback_used"] is True
        assert isinstance(result["results"], list)

    def test_403_api_key_missing_triggers_fallback(self):
        from data.openfda_client import fetch_faers_reports

        error_body = {"error": {"code": "API_KEY_MISSING", "message": "An API key is required."}}
        mock_resp = _make_mock_response(403, error_body)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("data.openfda_client.httpx.Client", return_value=mock_client):
            result = fetch_faers_reports("ASPIRIN", limit=10)

        assert result["fallback_used"] is True

    def test_fallback_results_not_empty(self):
        """The bundled sample_faers.json must have at least one report."""
        from data.openfda_client import fetch_faers_reports

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("offline")

        with patch("data.openfda_client.httpx.Client", return_value=mock_client):
            result = fetch_faers_reports("ASPIRIN", limit=10)

        assert len(result["results"]) > 0

    def test_fallback_never_raises(self):
        """fetch_faers_reports must never raise — catches all exceptions."""
        from data.openfda_client import fetch_faers_reports

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = RuntimeError("Unexpected failure")

        with patch("data.openfda_client.httpx.Client", return_value=mock_client):
            result = fetch_faers_reports("ASPIRIN", limit=10)  # must not raise

        assert "results" in result


# ---------------------------------------------------------------------------
# _load_fallback directly
# ---------------------------------------------------------------------------

class TestLoadFallback:
    def test_fallback_file_exists_and_parses(self):
        from data.openfda_client import _load_fallback
        result = _load_fallback()
        assert result["fallback_used"] is True
        assert len(result["results"]) > 0

    def test_missing_fallback_file_returns_empty(self, tmp_path):
        """If sample_faers.json is missing, return empty results without crashing."""
        from data import openfda_client
        original = openfda_client.SAMPLE_PATH
        try:
            openfda_client.SAMPLE_PATH = tmp_path / "nonexistent.json"
            result = openfda_client._load_fallback()
            assert result["results"] == []
            assert result["fallback_used"] is True
        finally:
            openfda_client.SAMPLE_PATH = original

"""
test_api_readiness.py — Integration tests for POST /readiness

Uses FastAPI TestClient (in-process). The LLM generate() call returns the
built-in stub string when watsonx credentials are absent, which is the
expected behaviour in a CI / test environment.

Covers:
  - 200 response shape
  - overall_score range [0, 100]
  - modules list length == 5
  - per-module keys present
  - full outline scores 100%
  - empty-equivalent outline scores 0%
  - gap_report field present (may be "" or stub)
  - 422 on empty outline list
  - 400 on explicitly empty outline (caught at endpoint level — but Pydantic
    min_length catches it at 422 first; both behaviours are acceptable)
  - present + missing == required for every module
  - score matches present / required ratio
"""

import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post_readiness(client, outline: list[str]) -> dict:
    resp = client.post("/readiness", json={"outline": outline})
    resp.raise_for_status()
    return resp.json()


FULL_OUTLINE = [
    # Module 1
    "1.0 Cover letter",
    "1.1 Comprehensive table of contents",
    "1.2 Application form",
    "1.3 Prescribing information and labeling",
    "1.4 Information about the experts",
    "1.5 Environmental assessment or exclusion",
    "1.6 Patent certifications and financial disclosure",
    # Module 2
    "2.2 Introduction",
    "2.3 Quality overall summary",
    "2.4 Nonclinical overview",
    "2.5 Clinical overview",
    "2.6 Nonclinical written and tabulated summaries",
    "2.7 Clinical summary",
    # Module 3
    "3.2.S.1 Drug substance nomenclature and structure",
    "3.2.S.2 Drug substance manufacture",
    "3.2.S.3 Drug substance characterisation",
    "3.2.S.4 Drug substance control",
    "3.2.S.5 Drug substance reference standards",
    "3.2.S.6 Drug substance container closure system",
    "3.2.S.7 Drug substance stability",
    "3.2.P.1 Drug product description and composition",
    "3.2.P.2 Drug product pharmaceutical development",
    "3.2.P.3 Drug product manufacture",
    "3.2.P.4 Drug product control of excipients",
    "3.2.P.5 Drug product control",
    "3.2.P.7 Drug product stability",
    "3.2.P.8 Drug product container closure system",
    # Module 4
    "4.2.1.1 Primary pharmacodynamics",
    "4.2.1.2 Secondary pharmacodynamics",
    "4.2.1.3 Safety pharmacology studies",
    "4.2.2 Pharmacokinetics absorption distribution metabolism excretion",
    "4.2.3.1 Acute toxicity",
    "4.2.3.2 Repeat dose toxicity",
    "4.2.3.3 Genetic toxicity",
    "4.2.3.4 Carcinogenicity studies",
    "4.2.3.5 Reproductive and developmental toxicity",
    # Module 5
    "5.2 Tabular listing of all clinical studies",
    "5.3.1 Biopharmaceutic studies and bioavailability",
    "5.3.3 Intrinsic factor pharmacokinetic studies",
    "5.3.4 Pharmacodynamic studies",
    "5.3.5 Population pharmacokinetic study reports",
    "5.4 Reports of human biomaterials studies",
    "5.5.1 Phase 2 controlled clinical studies",
    "5.5.2 Phase 3 controlled and uncontrolled clinical studies",
    "5.5.3 Integrated safety summary",
]

PARTIAL_OUTLINE = [
    "1.0 Cover letter",
    "1.1 Comprehensive table of contents",
    "1.2 Application form",
    "1.3 Prescribing information and labeling",
    "1.4 Information about the experts",
    "1.5 Environmental assessment or exclusion",
    "1.6 Patent certifications and financial disclosure",
    "2.3 Quality overall summary",
]


# ---------------------------------------------------------------------------
# Response structure
# ---------------------------------------------------------------------------

class TestReadinessEndpointStructure:
    def test_returns_200(self, api_client):
        resp = api_client.post("/readiness", json={"outline": PARTIAL_OUTLINE})
        assert resp.status_code == 200

    def test_top_level_keys(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        assert "overall_score" in data
        assert "modules" in data
        assert "gap_report" in data

    def test_overall_score_is_float(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        assert isinstance(data["overall_score"], float)

    def test_overall_score_in_range(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        assert 0.0 <= data["overall_score"] <= 100.0

    def test_modules_list_length_is_5(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        assert len(data["modules"]) == 5

    def test_each_module_has_required_keys(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        required = {"module", "module_name", "score", "present", "required", "missing", "present_sections"}
        for mod in data["modules"]:
            assert required.issubset(mod.keys())

    def test_gap_report_is_string(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        assert isinstance(data["gap_report"], str)

    def test_content_type_json(self, api_client):
        resp = api_client.post("/readiness", json={"outline": PARTIAL_OUTLINE})
        assert "application/json" in resp.headers["content-type"]


# ---------------------------------------------------------------------------
# Score correctness
# ---------------------------------------------------------------------------

class TestReadinessEndpointScores:
    def test_full_outline_scores_100(self, api_client):
        data = _post_readiness(api_client, FULL_OUTLINE)
        assert data["overall_score"] == 100.0

    def test_full_outline_no_missing_sections(self, api_client):
        data = _post_readiness(api_client, FULL_OUTLINE)
        for mod in data["modules"]:
            assert mod["missing"] == [], f"{mod['module']} has unexpected missing"

    def test_partial_outline_score_less_than_100(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        assert data["overall_score"] < 100.0

    def test_partial_outline_module1_complete(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        m1 = next(m for m in data["modules"] if m["module"] == "Module 1")
        assert m1["score"] == 100.0

    def test_partial_outline_modules_3_4_5_incomplete(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        for mod_id in ("Module 3", "Module 4", "Module 5"):
            mod = next(m for m in data["modules"] if m["module"] == mod_id)
            assert mod["score"] < 100.0

    def test_present_plus_missing_equals_required_per_module(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        for mod in data["modules"]:
            assert mod["present"] + len(mod["missing"]) == mod["required"]

    def test_score_consistent_with_present_required(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        for mod in data["modules"]:
            if mod["required"] > 0:
                expected = round(mod["present"] / mod["required"] * 100, 1)
                assert mod["score"] == expected


# ---------------------------------------------------------------------------
# Gap report behaviour
# ---------------------------------------------------------------------------

class TestReadinessGapReport:
    def test_gap_report_generated_when_missing_sections(self, api_client):
        """With watsonx unconfigured, gap_report is the stub string (starts with '[')."""
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        # Either a real LLM response or the stub — both are non-None strings
        assert data["gap_report"] is not None

    def test_no_gap_report_for_complete_dossier(self, api_client):
        """No missing sections → gap_report should be empty string."""
        data = _post_readiness(api_client, FULL_OUTLINE)
        assert data["gap_report"] == ""

    def test_gap_report_is_string_type(self, api_client):
        data = _post_readiness(api_client, PARTIAL_OUTLINE)
        assert isinstance(data["gap_report"], str)

    def test_gap_report_called_with_llm_mock(self, api_client):
        """Confirm LLM is invoked and its output is forwarded as gap_report."""
        with patch("backend.main.generate", return_value="Mocked gap report content."):
            data = _post_readiness(api_client, PARTIAL_OUTLINE)
        assert data["gap_report"] == "Mocked gap report content."


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestReadinessEndpointInputValidation:
    def test_empty_outline_list_returns_422(self, api_client):
        resp = api_client.post("/readiness", json={"outline": []})
        assert resp.status_code == 422

    def test_missing_outline_key_returns_422(self, api_client):
        resp = api_client.post("/readiness", json={})
        assert resp.status_code == 422

    def test_missing_body_returns_422(self, api_client):
        resp = api_client.post("/readiness")
        assert resp.status_code == 422

    def test_single_section_accepted(self, api_client):
        resp = api_client.post("/readiness", json={"outline": ["1.0 Cover letter"]})
        assert resp.status_code == 200

    def test_non_matching_sections_score_zero(self, api_client):
        data = _post_readiness(api_client, ["This matches nothing at all ever"])
        assert data["overall_score"] == 0.0

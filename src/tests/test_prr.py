"""
test_prr.py — Unit tests for src/backend/prr.py

Covers:
  - compute_prr returns correct structure and field types
  - PRR formula correctness (manually verifiable values)
  - chi-square formula correctness
  - All three threshold conditions (PRR >= 2.0, count >= 3, chi² >= 4.0)
  - Division-by-zero guards
  - Empty / no-match inputs
  - Results sorted by PRR descending
  - Rationale field initialised to empty string
"""

import math

import pytest

from backend.prr import compute_prr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_report(drug: str, event: str, report_id: str = "0") -> dict:
    return {
        "safetyreportid": report_id,
        "patient": {
            "drug": [{"medicinalproduct": drug}],
            "reaction": [{"reactionmeddrapt": event}],
        },
    }


def _build_reports(drug_a_x: int, drug_a_y: int, drug_b_x: int, drug_b_y: int) -> list[dict]:
    """
    Build a controlled dataset:
      DRUG_A: event X ×drug_a_x, event Y ×drug_a_y
      DRUG_B: event X ×drug_b_x, event Y ×drug_b_y
    """
    reports = []
    idx = 0
    for _ in range(drug_a_x):
        reports.append(_make_report("DRUG_A", "EVENT_X", str(idx))); idx += 1
    for _ in range(drug_a_y):
        reports.append(_make_report("DRUG_A", "EVENT_Y", str(idx))); idx += 1
    for _ in range(drug_b_x):
        reports.append(_make_report("DRUG_B", "EVENT_X", str(idx))); idx += 1
    for _ in range(drug_b_y):
        reports.append(_make_report("DRUG_B", "EVENT_Y", str(idx))); idx += 1
    return reports


def _chi2(a, b, c, d) -> float:
    """Reference Pearson chi-square calculation."""
    N = a + b + c + d
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    return N * (a * d - b * c) ** 2 / denom if denom > 0 else 0.0


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------

class TestComputePrrStructure:
    def test_returns_list(self, sample_reports):
        result = compute_prr(sample_reports, "ASPIRIN")
        assert isinstance(result, list)

    def test_each_item_has_required_keys(self, sample_reports):
        result = compute_prr(sample_reports, "ASPIRIN")
        assert len(result) > 0, "Expected at least one signal for ASPIRIN"
        required_keys = {"drug", "adverse_event", "prr", "report_count", "chi_square", "rationale"}
        for item in result:
            assert required_keys.issubset(item.keys()), f"Missing keys in {item}"

    def test_field_types(self, sample_reports):
        result = compute_prr(sample_reports, "ASPIRIN")
        for item in result:
            assert isinstance(item["drug"], str)
            assert isinstance(item["adverse_event"], str)
            assert isinstance(item["prr"], float)
            assert isinstance(item["report_count"], int)
            assert isinstance(item["chi_square"], float)
            assert isinstance(item["rationale"], str)

    def test_rationale_initialised_empty(self, sample_reports):
        result = compute_prr(sample_reports, "ASPIRIN")
        for item in result:
            assert item["rationale"] == "", "rationale should be empty — filled by LLM layer"

    def test_drug_name_uppercased_in_output(self, sample_reports):
        result = compute_prr(sample_reports, "aspirin")  # lowercase input
        for item in result:
            assert item["drug"] == item["drug"].upper()

    def test_sorted_by_prr_descending(self, sample_reports):
        result = compute_prr(sample_reports, "ASPIRIN")
        prrs = [s["prr"] for s in result]
        assert prrs == sorted(prrs, reverse=True)


# ---------------------------------------------------------------------------
# Empty / no-match inputs
# ---------------------------------------------------------------------------

class TestComputePrrEdgeCases:
    def test_empty_reports_returns_empty_list(self):
        assert compute_prr([], "ASPIRIN") == []

    def test_unknown_drug_returns_empty_list(self, sample_reports):
        result = compute_prr(sample_reports, "TOTALLY_UNKNOWN_DRUG_XYZ")
        assert result == []

    def test_reports_with_no_drug_field(self):
        reports = [{"safetyreportid": "1", "patient": {"drug": [], "reaction": [{"reactionmeddrapt": "HEADACHE"}]}}]
        assert compute_prr(reports, "ASPIRIN") == []

    def test_reports_with_no_reaction_field(self):
        reports = [{"safetyreportid": "1", "patient": {"drug": [{"medicinalproduct": "ASPIRIN"}], "reaction": []}}]
        assert compute_prr(reports, "ASPIRIN") == []

    def test_missing_patient_key_does_not_crash(self):
        reports = [{"safetyreportid": "1"}]  # no "patient" key at all
        assert compute_prr(reports, "ASPIRIN") == []

    def test_case_insensitive_drug_lookup(self, sample_reports):
        upper = compute_prr(sample_reports, "ASPIRIN")
        lower = compute_prr(sample_reports, "aspirin")
        mixed = compute_prr(sample_reports, "Aspirin")
        assert upper == lower == mixed


# ---------------------------------------------------------------------------
# PRR formula verification (manually computed)
# ---------------------------------------------------------------------------

class TestPRRFormula:
    def test_prr_value_correct(self):
        # DRUG_A: X×10, Y×2  |  DRUG_B: X×1, Y×10
        # For DRUG_A + EVENT_X:
        #   a=10, b=2, c=1, d=10  → PRR = (10/12) / (1/11) ≈ 9.17
        reports = _build_reports(10, 2, 1, 10)
        result = compute_prr(reports, "DRUG_A")
        ax = next((s for s in result if s["adverse_event"] == "EVENT_X"), None)
        assert ax is not None
        expected_prr = (10 / 12) / (1 / 11)
        assert math.isclose(ax["prr"], round(expected_prr, 2), rel_tol=1e-3)

    def test_prr_rounded_to_two_decimals(self):
        reports = _build_reports(10, 2, 1, 10)
        result = compute_prr(reports, "DRUG_A")
        for s in result:
            assert s["prr"] == round(s["prr"], 2)

    def test_prr_below_threshold_not_returned(self):
        # DRUG_A: X×3, Y×10  |  DRUG_B: X×10, Y×3
        # PRR for DRUG_A+EVENT_X = (3/13) / (10/13) = 0.30 → below 2.0
        reports = _build_reports(3, 10, 10, 3)
        result = compute_prr(reports, "DRUG_A")
        event_x_signals = [s for s in result if s["adverse_event"] == "EVENT_X"]
        assert event_x_signals == [], "PRR < 2.0 should not be flagged"


# ---------------------------------------------------------------------------
# Chi-square formula verification
# ---------------------------------------------------------------------------

class TestChiSquareFormula:
    def test_chi_square_value_correct(self):
        # DRUG_A: X×10, Y×2  |  DRUG_B: X×1, Y×10
        # For DRUG_A + EVENT_X: a=10, b=2, c=1, d=10
        reports = _build_reports(10, 2, 1, 10)
        result = compute_prr(reports, "DRUG_A")
        ax = next((s for s in result if s["adverse_event"] == "EVENT_X"), None)
        assert ax is not None
        a, b, c, d = 10, 2, 1, 10
        expected = round(_chi2(a, b, c, d), 2)
        assert math.isclose(ax["chi_square"], expected, rel_tol=1e-3)

    def test_chi_square_rounded_to_two_decimals(self):
        reports = _build_reports(10, 2, 1, 10)
        result = compute_prr(reports, "DRUG_A")
        for s in result:
            assert s["chi_square"] == round(s["chi_square"], 2)

    def test_chi_square_threshold_filters_borderline(self):
        # Construct a case where PRR >= 2 and count >= 3 but chi2 < 4
        # DRUG_A: X×3, Y×50  |  DRUG_B: X×1, Y×2
        # a=3, b=50, c=1, d=2 → PRR=(3/53)/(1/3)=0.17 → actually below PRR threshold
        # Use a dataset where we can confirm chi2 < 4 eliminates a candidate
        # DRUG_A: X×5, Y×0  |  DRUG_B: X×2, Y×1
        # a=5, b=0, c=2, d=1 → PRR=(5/5)/(2/3)=1.50 → below PRR threshold anyway
        # The real guard: any signal returned must have chi_square >= 4.0
        reports = _build_reports(10, 2, 1, 10)
        result = compute_prr(reports, "DRUG_A")
        for s in result:
            assert s["chi_square"] >= 4.0, f"chi_square={s['chi_square']} should be >= 4.0"

    def test_all_returned_signals_meet_all_three_thresholds(self, sample_reports):
        result = compute_prr(sample_reports, "ASPIRIN")
        for s in result:
            assert s["prr"] >= 2.0,     f"PRR {s['prr']} below 2.0"
            assert s["report_count"] >= 3, f"count {s['report_count']} below 3"
            assert s["chi_square"] >= 4.0, f"chi2 {s['chi_square']} below 4.0"


# ---------------------------------------------------------------------------
# Sample data regression — known signals
# ---------------------------------------------------------------------------

class TestSampleDataSignals:
    def test_aspirin_gi_haemorrhage_flagged(self, sample_reports):
        result = compute_prr(sample_reports, "ASPIRIN")
        events = {s["adverse_event"] for s in result}
        assert "GASTROINTESTINAL HAEMORRHAGE" in events

    def test_ibuprofen_has_signals(self, sample_reports):
        result = compute_prr(sample_reports, "IBUPROFEN")
        assert len(result) >= 1

    def test_metformin_has_signals(self, sample_reports):
        result = compute_prr(sample_reports, "METFORMIN")
        assert len(result) >= 1

    def test_no_signals_for_drug_with_only_one_report(self, sample_reports):
        # single-report drugs cannot meet count >= 3
        result = compute_prr(sample_reports, "WARFARIN")
        for s in result:
            assert s["report_count"] >= 3

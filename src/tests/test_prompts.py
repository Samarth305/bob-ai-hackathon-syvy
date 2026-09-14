"""
test_prompts.py — Unit tests for src/llm/prompts.py

Covers:
  - build_signal_rationale_prompt output structure
  - All signal fields appear in the prompt body
  - Numbered list format (1. 2. 3. ...)
  - build_gap_report_prompt output structure
  - Missing sections appear in prompt
  - Empty inputs handled gracefully
"""

import pytest

from llm.prompts import build_gap_report_prompt, build_signal_rationale_prompt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_signals():
    return [
        {"drug": "ASPIRIN", "adverse_event": "GASTROINTESTINAL HAEMORRHAGE", "prr": 9.56, "report_count": 5, "chi_square": 15.60},
        {"drug": "ASPIRIN", "adverse_event": "TINNITUS", "prr": 4.12, "report_count": 6, "chi_square": 7.33},
        {"drug": "ASPIRIN", "adverse_event": "HYPERSENSITIVITY", "prr": 2.85, "report_count": 3, "chi_square": 4.20},
    ]


@pytest.fixture
def sample_missing_by_module():
    return {
        "Module 3 — Quality": [
            "3.2.S.2 — Drug substance — manufacture",
            "3.2.P.3 — Drug product — manufacture",
        ],
        "Module 5 — Clinical Study Reports": [
            "5.5.1 — Phase 2 controlled clinical studies",
        ],
    }


# ---------------------------------------------------------------------------
# build_signal_rationale_prompt
# ---------------------------------------------------------------------------

class TestBuildSignalRationalePrompt:
    def test_returns_string(self, sample_signals):
        prompt = build_signal_rationale_prompt(sample_signals)
        assert isinstance(prompt, str)

    def test_prompt_not_empty(self, sample_signals):
        prompt = build_signal_rationale_prompt(sample_signals)
        assert len(prompt) > 100

    def test_contains_numbered_entries(self, sample_signals):
        prompt = build_signal_rationale_prompt(sample_signals)
        for i in range(1, len(sample_signals) + 1):
            assert f"{i}." in prompt

    def test_all_drug_names_present(self, sample_signals):
        prompt = build_signal_rationale_prompt(sample_signals)
        for sig in sample_signals:
            assert sig["drug"] in prompt

    def test_all_adverse_events_present(self, sample_signals):
        prompt = build_signal_rationale_prompt(sample_signals)
        for sig in sample_signals:
            assert sig["adverse_event"] in prompt

    def test_prr_values_present(self, sample_signals):
        prompt = build_signal_rationale_prompt(sample_signals)
        for sig in sample_signals:
            assert f"{sig['prr']:.2f}" in prompt

    def test_report_counts_present(self, sample_signals):
        prompt = build_signal_rationale_prompt(sample_signals)
        for sig in sample_signals:
            assert str(sig["report_count"]) in prompt

    def test_single_signal_prompt(self):
        signals = [{"drug": "METFORMIN", "adverse_event": "DIARRHOEA", "prr": 7.42, "report_count": 3, "chi_square": 8.85}]
        prompt = build_signal_rationale_prompt(signals)
        assert "METFORMIN" in prompt
        assert "DIARRHOEA" in prompt
        assert "1." in prompt

    def test_empty_signals_list_does_not_crash(self):
        prompt = build_signal_rationale_prompt([])
        assert isinstance(prompt, str)
        # Prompt body is returned without the signal block (empty signal_block)
        assert "Flagged signals:" in prompt

    def test_prompt_contains_prr_instruction_text(self, sample_signals):
        prompt = build_signal_rationale_prompt(sample_signals)
        assert "PRR" in prompt
        assert "pharmacovigilance" in prompt.lower() or "Proportional Reporting" in prompt

    def test_numbered_list_order_matches_signal_order(self, sample_signals):
        prompt = build_signal_rationale_prompt(sample_signals)
        # First signal's drug should appear before second signal's drug
        # when each signal has a unique event
        pos1 = prompt.index(sample_signals[0]["adverse_event"])
        pos2 = prompt.index(sample_signals[1]["adverse_event"])
        pos3 = prompt.index(sample_signals[2]["adverse_event"])
        assert pos1 < pos2 < pos3


# ---------------------------------------------------------------------------
# build_gap_report_prompt
# ---------------------------------------------------------------------------

class TestBuildGapReportPrompt:
    def test_returns_string(self, sample_missing_by_module):
        prompt = build_gap_report_prompt(sample_missing_by_module)
        assert isinstance(prompt, str)

    def test_prompt_not_empty(self, sample_missing_by_module):
        prompt = build_gap_report_prompt(sample_missing_by_module)
        assert len(prompt) > 100

    def test_module_names_present(self, sample_missing_by_module):
        prompt = build_gap_report_prompt(sample_missing_by_module)
        for module_name in sample_missing_by_module:
            assert module_name in prompt

    def test_missing_section_ids_present(self, sample_missing_by_module):
        prompt = build_gap_report_prompt(sample_missing_by_module)
        assert "3.2.S.2" in prompt
        assert "3.2.P.3" in prompt
        assert "5.5.1" in prompt

    def test_contains_ich_m4_reference(self, sample_missing_by_module):
        prompt = build_gap_report_prompt(sample_missing_by_module)
        assert "ICH M4" in prompt or "CTD" in prompt

    def test_empty_missing_by_module_does_not_crash(self):
        prompt = build_gap_report_prompt({})
        assert isinstance(prompt, str)
        assert "none" in prompt.lower() or "(none)" in prompt

    def test_empty_section_lists_skipped(self):
        """Modules with empty missing lists should not produce spurious output."""
        missing = {
            "Module 3 — Quality": [],  # empty → skipped
            "Module 5 — Clinical": ["5.5.1 — Phase 2"],
        }
        prompt = build_gap_report_prompt(missing)
        assert "5.5.1" in prompt
        # "Module 3 — Quality" is skipped because its list is empty
        assert "Module 3 — Quality" not in prompt

    def test_prompt_ends_with_gap_report_label(self, sample_missing_by_module):
        prompt = build_gap_report_prompt(sample_missing_by_module)
        # The template ends with "Gap Report:" to prime the model
        assert prompt.strip().endswith("Gap Report:")

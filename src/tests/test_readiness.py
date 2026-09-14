"""
test_readiness.py — Unit tests for src/backend/readiness.py

Covers:
  - check_readiness returns correct top-level structure
  - full outline scores 100% overall
  - empty / no-match outline scores 0%
  - partial outline produces expected per-module scores
  - fuzzy matching accepts near-match section titles
  - section ID prefix matching works
  - missing sections listed correctly
  - present_sections populated correctly
  - module count matches CTD_CHECKLIST length (5 modules)
  - total required sections is the canonical 45
"""

import pytest

from backend.readiness import check_readiness
from data.ctd_checklist import CTD_CHECKLIST, get_all_sections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOTAL_MODULES = len(CTD_CHECKLIST)
TOTAL_SECTIONS = sum(len(m["sections"]) for m in CTD_CHECKLIST)


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

class TestCheckReadinessStructure:
    def test_returns_dict_with_required_keys(self, full_ctd_outline):
        result = check_readiness(full_ctd_outline)
        assert "overall_score" in result
        assert "modules" in result

    def test_modules_count_equals_ctd_checklist(self, full_ctd_outline):
        result = check_readiness(full_ctd_outline)
        assert len(result["modules"]) == TOTAL_MODULES

    def test_each_module_has_required_keys(self, full_ctd_outline):
        result = check_readiness(full_ctd_outline)
        required = {"module", "module_name", "score", "present", "required", "missing", "present_sections"}
        for mod in result["modules"]:
            assert required.issubset(mod.keys())

    def test_module_names_match_checklist(self, full_ctd_outline):
        result = check_readiness(full_ctd_outline)
        expected_modules = [m["module"] for m in CTD_CHECKLIST]
        actual_modules = [m["module"] for m in result["modules"]]
        assert actual_modules == expected_modules

    def test_total_required_sections(self, full_ctd_outline):
        result = check_readiness(full_ctd_outline)
        total_required = sum(m["required"] for m in result["modules"])
        assert total_required == TOTAL_SECTIONS


# ---------------------------------------------------------------------------
# Score correctness
# ---------------------------------------------------------------------------

class TestCheckReadinessScores:
    def test_full_outline_scores_100_percent(self, full_ctd_outline):
        result = check_readiness(full_ctd_outline)
        assert result["overall_score"] == 100.0

    def test_full_outline_all_modules_100_percent(self, full_ctd_outline):
        result = check_readiness(full_ctd_outline)
        for mod in result["modules"]:
            assert mod["score"] == 100.0, f"{mod['module']} not 100%: {mod['score']}"

    def test_full_outline_no_missing_sections(self, full_ctd_outline):
        result = check_readiness(full_ctd_outline)
        for mod in result["modules"]:
            assert mod["missing"] == [], f"{mod['module']} has unexpected missing: {mod['missing']}"

    def test_empty_outline_scores_zero(self, empty_ctd_outline):
        result = check_readiness(empty_ctd_outline)
        assert result["overall_score"] == 0.0

    def test_empty_outline_all_sections_missing(self, empty_ctd_outline):
        result = check_readiness(empty_ctd_outline)
        total_missing = sum(len(m["missing"]) for m in result["modules"])
        assert total_missing == TOTAL_SECTIONS

    def test_partial_outline_score_is_proportional(self, partial_ctd_outline):
        # Partial outline has all 7 Module-1 sections + 1 from Module-2 = 8 present
        result = check_readiness(partial_ctd_outline)
        expected_overall = round(8 / TOTAL_SECTIONS * 100, 1)
        assert result["overall_score"] == expected_overall

    def test_partial_outline_module1_complete(self, partial_ctd_outline):
        result = check_readiness(partial_ctd_outline)
        m1 = next(m for m in result["modules"] if m["module"] == "Module 1")
        assert m1["score"] == 100.0
        assert m1["present"] == m1["required"]

    def test_partial_outline_module5_zero(self, partial_ctd_outline):
        result = check_readiness(partial_ctd_outline)
        m5 = next(m for m in result["modules"] if m["module"] == "Module 5")
        assert m5["score"] == 0.0
        assert m5["present"] == 0

    def test_score_field_is_float(self, partial_ctd_outline):
        result = check_readiness(partial_ctd_outline)
        assert isinstance(result["overall_score"], float)
        for mod in result["modules"]:
            assert isinstance(mod["score"], float)


# ---------------------------------------------------------------------------
# Section matching behaviour
# ---------------------------------------------------------------------------

class TestSectionMatching:
    def test_section_id_prefix_match(self):
        """Bare section ID in the outline should match."""
        result = check_readiness(["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6"])
        m1 = next(m for m in result["modules"] if m["module"] == "Module 1")
        assert m1["score"] == 100.0

    def test_fuzzy_title_match(self):
        """Near-match title (different capitalisation / minor word swap) should match."""
        outline = ["Cover Letter"]  # vs "Cover letter" in checklist
        result = check_readiness(outline)
        m1 = next(m for m in result["modules"] if m["module"] == "Module 1")
        # "cover letter" fuzzy matches "1.0 Cover letter"
        assert m1["present"] >= 1

    def test_completely_wrong_text_does_not_match(self):
        result = check_readiness(["This text matches nothing in the CTD checklist ever"])
        assert result["overall_score"] == 0.0

    def test_extra_lines_in_outline_ignored(self, full_ctd_outline):
        outline_with_noise = full_ctd_outline + [
            "Internal review notes",
            "Draft v3 — confidential",
            "TODO: update author list",
        ]
        result = check_readiness(outline_with_noise)
        assert result["overall_score"] == 100.0

    def test_blank_lines_in_outline_ignored(self, full_ctd_outline):
        outline_with_blanks = ["", "  ", "\t"] + full_ctd_outline
        result = check_readiness(outline_with_blanks)
        assert result["overall_score"] == 100.0


# ---------------------------------------------------------------------------
# present_sections / missing lists
# ---------------------------------------------------------------------------

class TestPresentAndMissingLists:
    def test_present_sections_contains_matched_titles(self, partial_ctd_outline):
        result = check_readiness(partial_ctd_outline)
        m1 = next(m for m in result["modules"] if m["module"] == "Module 1")
        assert "Cover letter" in m1["present_sections"]

    def test_missing_contains_id_and_title(self, partial_ctd_outline):
        result = check_readiness(partial_ctd_outline)
        m3 = next(m for m in result["modules"] if m["module"] == "Module 3")
        assert len(m3["missing"]) > 0
        # Each missing entry should be formatted as "ID — title"
        for entry in m3["missing"]:
            assert " — " in entry

    def test_present_plus_missing_equals_required(self, partial_ctd_outline):
        result = check_readiness(partial_ctd_outline)
        for mod in result["modules"]:
            assert mod["present"] + len(mod["missing"]) == mod["required"]

    def test_present_count_matches_present_sections_length(self, partial_ctd_outline):
        result = check_readiness(partial_ctd_outline)
        for mod in result["modules"]:
            assert mod["present"] == len(mod["present_sections"])


# ---------------------------------------------------------------------------
# CTD checklist data integrity
# ---------------------------------------------------------------------------

class TestCTDChecklistIntegrity:
    def test_all_five_modules_present(self):
        modules = [m["module"] for m in CTD_CHECKLIST]
        for i in range(1, 6):
            assert f"Module {i}" in modules

    def test_total_sections_is_45(self):
        assert TOTAL_SECTIONS == 45

    def test_get_all_sections_returns_flat_list(self):
        sections = get_all_sections()
        assert len(sections) == TOTAL_SECTIONS
        for sec in sections:
            assert "id" in sec and "title" in sec and "module" in sec

    def test_all_section_ids_unique(self):
        sections = get_all_sections()
        ids = [s["id"] for s in sections]
        assert len(ids) == len(set(ids)), "Duplicate section IDs found in checklist"

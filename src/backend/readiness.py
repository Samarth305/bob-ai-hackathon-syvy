"""
readiness.py — CTD submission readiness checker.

Diffs a user-provided dossier outline against the ICH M4 CTD checklist,
computes per-module and overall completeness scores.
"""

import sys
from pathlib import Path

from thefuzz import fuzz

# Add parent to path so data module is importable when running standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.ctd_checklist import CTD_CHECKLIST

FUZZY_THRESHOLD = 72  # minimum token_sort_ratio to count as a match


def _normalise(text: str) -> str:
    return text.lower().strip()


def check_readiness(outline: list[str]) -> dict:
    """
    Compare *outline* (list of section title strings) against CTD_CHECKLIST.

    Returns:
    {
        "overall_score": float,
        "modules": [
            {
                "module": "Module 1",
                "module_name": "Administrative Information",
                "score": float,
                "present": int,
                "required": int,
                "missing": ["section title", ...],
                "present_sections": ["section title", ...],
            },
            ...
        ]
    }
    """
    norm_outline = [_normalise(s) for s in outline if s.strip()]

    module_results = []
    total_present = 0
    total_required = 0

    for mod in CTD_CHECKLIST:
        present = []
        missing = []
        for sec in mod["sections"]:
            sec_title = _normalise(sec["title"])
            sec_id    = _normalise(sec["id"])

            matched = False
            for user_line in norm_outline:
                # Match by section ID prefix OR fuzzy title match
                if sec_id in user_line or fuzz.token_sort_ratio(sec_title, user_line) >= FUZZY_THRESHOLD:
                    matched = True
                    break

            if matched:
                present.append(sec["title"])
            else:
                missing.append(f"{sec['id']} — {sec['title']}")

        n_present  = len(present)
        n_required = len(mod["sections"])
        score = round(n_present / n_required * 100, 1) if n_required > 0 else 0.0

        total_present  += n_present
        total_required += n_required

        module_results.append({
            "module":           mod["module"],
            "module_name":      mod["name"],
            "score":            score,
            "present":          n_present,
            "required":         n_required,
            "missing":          missing,
            "present_sections": present,
        })

    overall = round(total_present / total_required * 100, 1) if total_required > 0 else 0.0

    return {
        "overall_score": overall,
        "modules":       module_results,
    }


# ---------------------------------------------------------------------------
# CLI self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_outline = [
        "1.0 Cover letter",
        "2.3 Quality Overall Summary",
        "2.5 Clinical Overview",
        "3.2.S.1 Drug Substance nomenclature",
        "3.2.P.1 Drug Product description",
        "4.2.1.1 Primary Pharmacodynamics",
        "5.5.2 Phase 3 clinical studies",
    ]

    result = check_readiness(sample_outline)
    print(f"Overall score: {result['overall_score']}%\n")
    for m in result["modules"]:
        bar = "█" * int(m["score"] / 10) + "░" * (10 - int(m["score"] / 10))
        print(f"  {m['module']} {bar} {m['score']:5.1f}%  ({m['present']}/{m['required']})")
        if m["missing"]:
            for sec in m["missing"][:3]:
                print(f"      ✗ {sec}")
    print("\n✅ Readiness checker OK")

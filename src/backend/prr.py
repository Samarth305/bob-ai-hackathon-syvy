"""
prr.py — Proportional Reporting Ratio computation for FAERS adverse event data.

Formula (WHO-UMC standard):
    PRR = (a / (a + b)) / (c / (c + d))

    a = reports of adverse_event Y for drug X
    b = reports of other events for drug X
    c = reports of adverse_event Y for all other drugs
    d = reports of other events for all other drugs

Chi-square (Pearson):
    χ² = N * (a*d - b*c)² / ((a+b)*(c+d)*(a+c)*(b+d))

Signal threshold: PRR >= 2.0 AND a >= 3 AND χ² >= 4.0
"""

import sys
from pathlib import Path

import pandas as pd


def compute_prr(reports: list[dict], drug_name: str) -> list[dict]:
    """
    Compute PRR for all drug-event pairs in *reports*, focused on *drug_name*.

    Returns a list of dicts sorted by PRR descending, filtered to
    PRR >= 2.0 AND report_count >= 3.
    """
    rows = []
    for report in reports:
        patient = report.get("patient", {})
        drugs = patient.get("drug", [])
        reactions = patient.get("reaction", [])

        drug_names_in_report = [
            (d.get("medicinalproduct") or d.get("openfda", {}).get("generic_name", [""])[0] or "").upper().strip()
            for d in drugs
        ]
        event_terms = [
            (r.get("reactionmeddrapt") or "").upper().strip()
            for r in reactions
        ]

        for drug in drug_names_in_report:
            for event in event_terms:
                if drug and event:
                    rows.append({"drug": drug, "event": event})

    if not rows:
        return []

    df = pd.DataFrame(rows)
    target_drug = drug_name.upper().strip()

    # Total counts per (drug, event) pair
    pair_counts = df.groupby(["drug", "event"]).size().reset_index(name="count")

    # Grand totals
    total_all = len(df)
    total_per_drug = df.groupby("drug").size().rename("drug_total")
    total_per_event = df.groupby("event").size().rename("event_total")

    pair_counts = pair_counts.join(total_per_drug, on="drug")
    pair_counts = pair_counts.join(total_per_event, on="event")

    # Filter to target drug
    target_rows = pair_counts[pair_counts["drug"] == target_drug].copy()
    if target_rows.empty:
        return []

    results = []
    for _, row in target_rows.iterrows():
        a = row["count"]           # this drug, this event
        drug_total = row["drug_total"]
        event_total = row["event_total"]

        b = drug_total - a         # this drug, other events
        c = event_total - a        # other drugs, this event
        d = total_all - a - b - c  # other drugs, other events

        # Avoid division by zero
        if (a + b) == 0 or (c + d) == 0:
            continue
        denom_a = c / (c + d) if (c + d) > 0 else 0
        if denom_a == 0:
            continue

        prr = (a / (a + b)) / denom_a

        # Pearson chi-square: N*(ad - bc)^2 / ((a+b)(c+d)(a+c)(b+d))
        N = a + b + c + d
        denom_chi = (a + b) * (c + d) * (a + c) * (b + d)
        chi_square = (N * (a * d - b * c) ** 2 / denom_chi) if denom_chi > 0 else 0.0

        if prr >= 2.0 and a >= 3 and chi_square >= 4.0:
            results.append({
                "drug": row["drug"],
                "adverse_event": row["event"],
                "prr": round(float(prr), 2),
                "report_count": int(a),
                "chi_square": round(float(chi_square), 2),
                "a": int(a), "b": int(b), "c": int(c), "d": int(d),
                "rationale": "",  # filled in by LLM layer
            })

    results.sort(key=lambda x: x["prr"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# CLI self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    sample_path = Path(__file__).resolve().parent.parent / "data" / "sample_faers.json"
    if not sample_path.exists():
        print("sample_faers.json not found — run from src/ directory")
        sys.exit(1)

    with open(sample_path) as f:
        raw = json.load(f)
    reports = raw if isinstance(raw, list) else raw.get("results", [])

    drug = sys.argv[1] if len(sys.argv) > 1 else "ASPIRIN"
    signals = compute_prr(reports, drug)
    print(f"Drug: {drug}  |  Signals flagged (PRR>=2, count>=3): {len(signals)}\n")
    for s in signals[:5]:
        print(f"  PRR={s['prr']:6.2f}  χ²={s['chi_square']:7.2f}  count={s['report_count']:4d}  event={s['adverse_event']}")
    print("\n✅ PRR calculator OK")

"""
prompts.py — Prompt templates for IBM watsonx.ai Granite model.
"""


def build_signal_rationale_prompt(signals: list[dict]) -> str:
    """Build a prompt asking Granite to explain each flagged PRR signal."""
    lines = []
    for i, s in enumerate(signals, 1):
        lines.append(
            f"{i}. Drug: {s['drug']} | Adverse Event: {s['adverse_event']} "
            f"| PRR: {s['prr']:.2f} | Reports: {s['report_count']}"
        )
    signal_block = "\n".join(lines)

    return f"""You are a pharmacovigilance expert reviewing drug safety signals flagged from the FDA FAERS adverse event database.

The following drug-adverse event pairs have been flagged as potential safety signals using the Proportional Reporting Ratio (PRR >= 2.0, minimum 3 reports). PRR measures how much more frequently an adverse event is reported for this drug compared to all other drugs.

Flagged signals:
{signal_block}

For each signal above, write 1-2 sentences explaining:
- Why this drug-event combination may be clinically meaningful
- What biological mechanism or known drug property could explain it
- What a safety reviewer should investigate first

Format your response as a numbered list matching the signal numbers above. Be concise and clinically accurate. Do not add disclaimers.

Response:"""


def build_gap_report_prompt(missing_by_module: dict) -> str:
    """Build a prompt asking Granite to generate a regulatory gap report."""
    lines = []
    for module_name, missing_sections in missing_by_module.items():
        if missing_sections:
            lines.append(f"\n{module_name}:")
            for sec in missing_sections:
                lines.append(f"  - {sec}")
    missing_block = "\n".join(lines) if lines else "  (none)"

    return f"""You are a regulatory affairs expert reviewing a pharmaceutical CTD (Common Technical Document) submission against the ICH M4 standard.

The following required sections are MISSING from the submitted dossier outline:
{missing_block}

Write a concise regulatory gap report (3-5 paragraphs) that:
1. Summarises which modules have the most critical gaps
2. Explains why the most important missing sections are required by ICH M4 and what regulatory consequence their absence causes (e.g. Refuse to File, Major Objection)
3. Recommends a prioritised remediation plan — what the team should complete first and why

Write in professional regulatory language suitable for a senior regulatory affairs director. Be specific about section IDs where relevant.

Gap Report:"""

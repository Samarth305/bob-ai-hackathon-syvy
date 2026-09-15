"""
app.py — Streamlit two-tab frontend.

Tab 1: Signal Detection  — enter drug name → PRR signals + LLM rationale
Tab 2: Submission Readiness — paste/upload CTD outline → scores + gap report
"""

import os
import sys
from pathlib import Path

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 60.0


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Drug Safety & Submission Readiness",
    page_icon="💊",
    layout="wide",
)

st.title("💊 Drug Safety Signal Detector & Submission Readiness Checker")
st.caption("Powered by IBM watsonx.ai (Granite) · FDA FAERS data · ICH M4 CTD standard")

tab1, tab2 = st.tabs(["🔬 Signal Detection", "📋 Submission Readiness"])


# ---------------------------------------------------------------------------
# Tab 1 — Signal Detection
# ---------------------------------------------------------------------------
with tab1:
    st.header("Drug Safety Signal Detection")
    st.markdown(
        "Enter a drug name to fetch FDA FAERS adverse event reports, "
        "compute **Proportional Reporting Ratios (PRR)**, and get AI-generated "
        "clinical rationale for flagged signals."
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        drug_name = st.text_input(
            "Drug name",
            placeholder="e.g. aspirin, ibuprofen, atorvastatin, metformin",
            key="drug_input",
        )
    with col2:
        limit = st.number_input("Max reports", min_value=10, max_value=1_000_000, value=1000, step=1000)

    run_btn = st.button("🔍 Run Signal Analysis", type="primary", key="run_signals")

    if run_btn:
        if not drug_name.strip():
            st.warning("Please enter a drug name.")
        else:
            with st.spinner(f"Fetching FAERS reports for **{drug_name}** and computing PRR..."):
                try:
                    resp = httpx.post(
                        f"{BACKEND_URL}/signals",
                        json={"drug_name": drug_name.strip(), "limit": limit},
                        timeout=TIMEOUT,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.ConnectError:
                    st.error(
                        "❌ Cannot connect to backend API at `http://localhost:8000`.\n\n"
                        "Make sure the backend is running:  `cd src && uvicorn backend.main:app --reload --port 8000`"
                    )
                    st.stop()
                except Exception as e:
                    st.error(f"❌ Request failed: {e}")
                    st.stop()

            if data.get("fallback_used"):
                st.info("📦 Using **offline fallback dataset** (openFDA API unreachable). Results are from the bundled sample.")

            total = data.get("total_reports", 0)
            signals = data.get("signals", [])

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Reports fetched", total)
            col_b.metric("Signals flagged", len(signals))
            col_c.metric("Threshold", "PRR ≥ 2.0 · n ≥ 3 · χ² ≥ 4.0")

            if not signals:
                st.warning(
                    f"No signals meeting threshold (PRR ≥ 2.0, n ≥ 3, χ² ≥ 4.0) found for **{drug_name}**. "
                    "Try a more common drug name or increase the report limit."
                )
            else:
                st.success(f"**{len(signals)} signal(s)** flagged for **{drug_name}**")
                st.markdown("---")

                for i, sig in enumerate(signals):
                    prr = sig["prr"]
                    chi2 = sig.get("chi_square", 0.0)
                    colour = "🔴" if prr >= 5 else "🟡" if prr >= 3 else "🟢"
                    with st.expander(
                        f"{colour} **{sig['adverse_event']}** — PRR: {prr:.2f} | χ²: {chi2:.2f} | Reports: {sig['report_count']}",
                        expanded=(i < 3),
                    ):
                        col_x, col_y, col_z, col_w = st.columns(4)
                        col_x.metric("PRR", f"{prr:.2f}")
                        col_y.metric("χ² (chi-sq)", f"{chi2:.2f}")
                        col_z.metric("Report count", sig["report_count"])
                        col_w.metric("Drug", sig["drug"])

                        rationale = sig.get("rationale", "")
                        if rationale and not rationale.startswith("["):
                            st.markdown("**🤖 AI Rationale (watsonx.ai Granite)**")
                            st.info(rationale)
                        elif rationale.startswith("["):
                            st.caption(f"ℹ {rationale}")


# ---------------------------------------------------------------------------
# Tab 2 — Submission Readiness
# ---------------------------------------------------------------------------
with tab2:
    st.header("CTD Submission Readiness Checker")
    st.markdown(
        "Paste or upload your dossier outline (one section per line) to check it against "
        "the **ICH M4 CTD standard** (5 modules, 45 required sections). "
        "Get per-module completeness scores and an AI-generated gap report."
    )

    st.markdown("**Enter your dossier outline** — paste section titles, one per line:")
    outline_text = st.text_area(
        "Dossier outline",
        height=220,
        placeholder=(
            "1.0 Cover letter\n"
            "2.3 Quality Overall Summary\n"
            "2.5 Clinical Overview\n"
            "3.2.S.1 Drug substance nomenclature\n"
            "3.2.P.1 Drug product description\n"
            "4.2.1.1 Primary pharmacodynamics\n"
            "5.5.2 Phase 3 clinical studies\n"
            "..."
        ),
        key="outline_input",
        label_visibility="collapsed",
    )

    uploaded = st.file_uploader(
        "Or upload a .txt file (one section per line)",
        type=["txt", "yaml", "yml"],
        key="outline_file",
    )

    if uploaded is not None:
        outline_text = uploaded.read().decode("utf-8", errors="replace")
        st.caption(f"Loaded {len(outline_text.splitlines())} lines from {uploaded.name}")

    check_btn = st.button("✅ Check Readiness", type="primary", key="run_readiness")

    if check_btn:
        lines = [l.strip() for l in outline_text.splitlines() if l.strip()]
        if not lines:
            st.warning("Please paste or upload a dossier outline first.")
        else:
            with st.spinner("Checking completeness against ICH M4 CTD checklist..."):
                try:
                    resp = httpx.post(
                        f"{BACKEND_URL}/readiness",
                        json={"outline": lines},
                        timeout=TIMEOUT,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.ConnectError:
                    st.error(
                        "❌ Cannot connect to backend API at `http://localhost:8000`.\n\n"
                        "Make sure the backend is running:  `cd src && uvicorn backend.main:app --reload --port 8000`"
                    )
                    st.stop()
                except Exception as e:
                    st.error(f"❌ Request failed: {e}")
                    st.stop()

            overall = data.get("overall_score", 0)
            modules = data.get("modules", [])
            gap_report = data.get("gap_report", "")

            # Overall score
            if overall >= 80:
                st.success(f"### Overall Readiness: {overall:.1f}% ✅")
            elif overall >= 50:
                st.warning(f"### Overall Readiness: {overall:.1f}% ⚠️")
            else:
                st.error(f"### Overall Readiness: {overall:.1f}% ❌")

            st.progress(int(overall))
            st.markdown("---")

            # Per-module scores
            st.subheader("📊 Module Completeness")
            for mod in modules:
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    colour = "🟢" if mod["score"] >= 80 else "🟡" if mod["score"] >= 40 else "🔴"
                    st.markdown(f"**{colour} {mod['module']} — {mod['module_name']}**")
                    st.progress(int(mod["score"]))
                with col_b:
                    st.metric("Score", f"{mod['score']:.0f}%", f"{mod['present']}/{mod['required']}")

                if mod["missing"]:
                    with st.expander(f"  ✗ {len(mod['missing'])} missing section(s)"):
                        for sec in mod["missing"]:
                            st.markdown(f"- {sec}")

            # LLM gap report
            st.markdown("---")
            st.subheader("🤖 AI Regulatory Gap Report (watsonx.ai Granite)")
            if gap_report and not gap_report.startswith("["):
                st.markdown(gap_report)
            elif gap_report.startswith("["):
                st.caption(f"ℹ {gap_report}")
                st.info(
                    "No AI gap report generated. Configure `WATSONX_API_KEY` in `src/.env` "
                    "to enable IBM watsonx.ai-powered gap analysis."
                )
            else:
                st.success("🎉 No missing sections detected — dossier appears complete!")

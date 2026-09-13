# Solution Overview

## What We Built

**Drug Safety Signal Detector & Submission Readiness Checker** is a two-mode AI platform that applies IBM watsonx.ai (Granite model) to the two most expensive data bottlenecks in the pharmaceutical regulatory lifecycle: detecting emerging drug safety signals from adverse event data, and verifying that a regulatory submission dossier is complete before it reaches the FDA or EMA.

Both modes are accessible through a Streamlit web interface, backed by a FastAPI REST API, and share a common IBM watsonx.ai integration layer that generates plain-language, human-readable analysis from structured data inputs. The system requires no enterprise database — all computation is in-memory — and includes an offline fallback dataset so it remains fully demoable without internet access.

---

## How It Works

### Mode 1 — Signal Detection

1. **User enters a drug name** in the Signal Detection tab (e.g., "ibuprofen", "metformin", "atorvastatin")
2. **The backend fetches live adverse event reports** from the public openFDA FAERS API (`https://api.fda.gov/drug/event.json`), filtering by drug name and pulling the most recent 1,000 reports (no API key required for low-volume queries). If the API is unreachable, a bundled local fallback dataset is used transparently.
3. **Reports are grouped by drug–adverse-event pair** (drug name × event preferred term). Each unique pair is counted and aggregated.
4. **PRR (Proportional Reporting Ratio) is computed** for each pair using the WHO-UMC standard formula:

   ```
   PRR = [a / (a + b)] / [c / (c + d)]
   a = reports of this event for this drug
   b = reports of other events for this drug
   c = reports of this event for all other drugs
   d = reports of other events for all other drugs
   ```

   Pairs meeting both **PRR ≥ 2** and **report count ≥ 3** are flagged as signal candidates — the standard pharmacovigilance threshold recommended by WHO-UMC.

5. **The top flagged signals are passed to IBM watsonx.ai** (Granite model via the `ibm-watsonx-ai` Python SDK). The prompt asks the model to produce a plain-language clinical rationale for each signal — why this drug–event combination is potentially meaningful, what the biological mechanism might be, and what a safety reviewer should investigate first.
6. **Results are displayed** as a ranked table: drug name, adverse event, PRR value, report count, and LLM-generated rationale — sortable by PRR or count.

---

### Mode 2 — Submission Readiness

1. **User provides their dossier outline** — either by pasting a text list of section titles or uploading a simple `.txt` or `.yaml` file listing sections present in their CTD
2. **The backend loads the built-in ICH M4 CTD checklist** — a hardcoded structured representation of all five CTD modules and their required sections (see below), derived from the public ICH M4 guideline (ICH M4: Organisation of the CTD, 2016)
3. **A section-by-section diff is performed** per module: each required section is matched against the user's outline (fuzzy matching to handle minor naming variations)
4. **Completeness scores are computed** per module (e.g., "Module 3 Quality: 14/18 sections present = 78%") and an overall score is reported
5. **Missing sections per module are passed to IBM watsonx.ai** with the prompt asking the model to generate a regulatory gap report: what is missing, why each missing section is required by ICH M4, what the consequence of omission is likely to be (e.g., RTF, major objection), and suggested next steps
6. **Results are displayed** as: a completeness dashboard (module-level progress bars + overall score), a table of missing sections with regulatory context, and the LLM-generated gap report in prose

---

## Architecture Diagram

> See [`architecture.md`](architecture.md) for the detailed Mermaid diagram and component table.

```
[User Browser]
      │
      ▼
[Streamlit Frontend]  ←── Two tabs: Signal Detection | Submission Readiness
      │  REST calls
      ▼
[FastAPI Backend]
      │
      ├──► [openFDA FAERS API]  ←── live data or local fallback cache
      │
      ├──► [PRR Calculator]  ←── in-memory pandas computation
      │
      ├──► [ICH M4 CTD Checklist]  ←── hardcoded structured data
      │
      └──► [watsonx.ai LLM Client]  ←── ibm-watsonx-ai SDK, Granite model
                  │
                  ▼
         [IBM watsonx.ai API]
```

---

## ICH M4 CTD Checklist (Mode 2 Reference Data)

The full ICH M4 standard is hardcoded as structured data in `src/data/ctd_checklist.yaml`. The five modules and their key required sections are:

| Module | Name | Key Required Sections |
|---|---|---|
| **Module 1** | Administrative Information | Cover letter, Application form, Prescribing information/labeling, Patent certifications, Financial disclosure, Environmental assessment |
| **Module 2** | CTD Summaries & Overviews | Quality Overall Summary (2.3), Nonclinical Overview (2.4), Nonclinical Written & Tabulated Summaries (2.6), Clinical Overview (2.5), Clinical Summary (2.7) |
| **Module 3** | Quality | Drug Substance (3.2.S: nomenclature, structure, synthesis, characterization, specifications, analytical methods, stability), Drug Product (3.2.P: composition, development, manufacturing, specifications, stability, container closure) |
| **Module 4** | Nonclinical Study Reports | Pharmacology (4.2.1: primary, secondary, safety pharmacology), Pharmacokinetics (4.2.2: ADME, protein binding, metabolism, drug-drug interactions), Toxicology (4.2.3: acute, repeat-dose, genetic, carcinogenicity, reproductive) |
| **Module 5** | Clinical Study Reports | Biopharmaceutic studies (5.2), PK/PD studies (5.3), Efficacy studies — Phase 2 & 3 (5.5), Safety studies — integrated safety summary (5.5), Individual patient data appendices |

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **openFDA FAERS API as data source (no API key required)** | Enables a fully runnable demo without any account setup. FDA's public endpoint provides real, current adverse event data sufficient to demonstrate PRR computation meaningfully. |
| **Hardcoded ICH M4 checklist as structured YAML** | The ICH M4 standard is a stable, publicly documented specification. Hardcoding it eliminates the need for a database and makes the checklist trivially auditable and updateable. |
| **PRR as the signal detection statistic** | PRR (Proportional Reporting Ratio) is the WHO-UMC recommended standard for disproportionality analysis, widely used by FDA, EMA, and WHO VigiBase. Using it demonstrates regulatory literacy and produces industry-recognizable output. |
| **LLM integration behind a thin wrapper (`src/llm/client.py`)** | Isolating the watsonx.ai call behind a single interface means the model, endpoint, and credentials can be swapped (e.g., local Ollama for offline demos) without touching business logic. |
| **FastAPI + Streamlit, no database** | For a hackathon MVP, in-memory computation is sufficient. FastAPI provides a clean REST API that can be demoed independently via Swagger `/docs`. Streamlit eliminates frontend build complexity. |
| **Offline fallback dataset bundled in `src/data/`** | FAERS API may be unreachable during live demos. A bundled sample ensures the demo never shows a blank error screen — a hard requirement from the problem prompt. |

---

## IBM Technologies Used

- **IBM watsonx.ai (Granite model):**
  - **Mode 1 (Signal Detection):** The top PRR-flagged drug–event pairs are passed to the Granite model with a structured prompt requesting a plain-language clinical rationale per signal. The model explains the biological plausibility of the association, suggests what type of confounding or true causality might be at play, and recommends immediate investigative steps. This is a real, load-bearing inference call — the rationale column in the results table is entirely LLM-generated and directly changes the output.
  - **Mode 2 (Submission Readiness):** The list of missing CTD sections per module is passed to the Granite model with context about ICH M4 requirements and a prompt requesting a regulatory gap report in prose. The model explains why each missing section is required, what regulatory consequence its absence is likely to cause (e.g., RTF, major objection), and suggests a prioritized remediation plan.
  - **Integration**: Python `ibm-watsonx-ai` SDK; model `ibm/granite-13b-instruct-v2`; credentials via environment variables (`WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`)

- **IBM Bob:**
  - Used as the AI coding assistant throughout development — architecture planning, code scaffolding, documentation generation, and submission preparation

---

## UX Walkthrough

### Signal Detection Flow

```
1. Open app → "Signal Detection" tab is active by default
2. Type a drug name (e.g., "ibuprofen") in the search box
3. Click "Run Signal Analysis"
4. Loading spinner while backend:
   a. Calls openFDA API (or loads fallback)
   b. Computes PRR for all drug-event pairs
   c. Filters to PRR ≥ 2.0 AND count ≥ 3
   d. Sends top signals to watsonx.ai Granite
5. Results table renders with columns:
   Drug | Adverse Event | PRR | Report Count | AI Rationale
6. Table is sortable; rows highlighted by severity (PRR ≥ 5 = red, 2–5 = yellow)
7. Export button downloads results as CSV
```

### Submission Readiness Flow

```
1. Click "Submission Readiness" tab
2. Paste or upload dossier outline (text list of section titles present)
3. Click "Check Readiness"
4. Loading spinner while backend:
   a. Loads ICH M4 CTD checklist
   b. Fuzzy-matches user sections against checklist
   c. Computes per-module completeness scores
   d. Sends missing sections to watsonx.ai Granite
5. Dashboard renders:
   a. Overall readiness score (0–100%) with color-coded status
   b. Per-module progress bars (Module 1–5)
   c. Table: Required Section | Status | Module
   d. LLM-generated gap report (prose)
6. Export button downloads gap report as PDF/text
```

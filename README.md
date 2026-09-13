# 🚀 Drug Safety Signal Detector & Submission Readiness Checker

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | Team Syvy |
| **Track** | AI |
| **Team Lead** | Samarth Kachhadiya — 23ce050@charusat.edu.in |
| **Members** | Vraj Mevawala, Yug Thummar, Yug Moradiya |

---

## 🎯 Problem Statement

FDA's FAERS database contains 20M+ adverse event reports — far too many for manual review, leading to delayed safety signal detection that has caused real harm (e.g., Vioxx). Simultaneously, regulatory drug-approval dossiers (CTD) span 100,000+ pages across 5 modules; a single missing section triggers rejection, costing 6–12 months and $50–100M. Both problems share the same root cause: too much complex data for human review alone.

---

## 💡 Solution

We built a two-mode AI-powered platform: **Signal Detection** ingests live FDA FAERS adverse event data, computes Proportional Reporting Ratios (PRR) to flag emerging drug-safety signals, and uses IBM watsonx.ai (Granite) to generate plain-language rationale for each flagged signal. **Submission Readiness** checks a user-uploaded dossier outline against the ICH M4 CTD standard, scores completeness per module, and uses the same LLM to produce a judge-readable gap report with actionable next steps.

---

## ✨ Key Features

- **Real-time FAERS Signal Detection:** Queries the public openFDA API by drug name, clusters adverse-event reports, and computes PRR statistics to flag signals meeting standard pharmacovigilance thresholds (PRR ≥ 2, report count ≥ 3).
- **LLM-Powered Signal Rationale:** Passes the top flagged drug–event pairs to IBM watsonx.ai (Granite model) to generate plain-language explanations of why each signal is clinically noteworthy.
- **CTD Submission Readiness Checker:** Validates a user-provided dossier outline against the hardcoded ICH M4 CTD 5-module checklist, scoring completeness per module and overall.
- **AI-Generated Gap Report:** Uses IBM watsonx.ai to produce a prose gap report — what sections are missing, why they matter, and suggested next steps — ready to hand to a regulatory reviewer.
- **Offline Fallback:** Bundles a cached FAERS sample dataset so both modes remain fully demoable when the openFDA API is unreachable.

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python |
| **Frameworks** | FastAPI, Streamlit |
| **IBM Technologies** | watsonx.ai (Granite model), IBM Bob |
| **Databases** | In-memory / JSON (no persistent DB required) |
| **Other** | openFDA FAERS API, GitHub Actions |

---

## 📁 Repository Structure

```
├── src/                        # All source code
│   ├── backend/                # FastAPI backend (main.py, prr.py, readiness.py, models.py)
│   ├── llm/                    # watsonx.ai client wrapper (client.py, prompts.py)
│   ├── data/                   # Cached FAERS fallback + CTD checklist + Drugs@FDA loader
│   ├── frontend/               # Streamlit UI (two tabs: Signal Detection, Submission Readiness)
│   ├── .env.example            # All required environment variables
│   └── README.md
├── docs/
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md         # Includes Mermaid diagram
│   └── setup-guide.md
├── demo/
│   ├── screenshots/            # 01-signal-detection.png, 02-readiness-checker.png, 03-gap-report.png
│   ├── demo-video-link.txt
│   └── live-demo-url.txt
├── presentation/               # slides.pdf
├── run.py                      # Single-command launcher (auto-venv, starts both servers)
└── submission.yaml
```

---

## ⚡ How to Run

> See full instructions in [`docs/setup-guide.md`](docs/setup-guide.md)

```bash
# 1. Clone the repo
git clone https://github.com/syvyai/bob-ai-hackathon-syvy.git
cd bob-ai-hackathon-syvy

# 2. Configure environment
cp src/.env.example src/.env
# Edit src/.env — add WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL

# 3. Launch everything (auto-creates venv, installs deps, starts both servers)
python run.py
# Windows shortcut: run.bat
# macOS/Linux:      ./run.sh
```

> The launcher opens your browser automatically. Backend runs on port 8000, Streamlit on port 8501.
> Press **Ctrl+C** once to stop both servers.
> See [`docs/setup-guide.md`](docs/setup-guide.md) for full per-OS instructions.

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/slides.pdf](presentation/) |

---

## ⚠️ Known Limitations

- PRR thresholds (PRR ≥ 2, report count ≥ 3) are simplified pharmacovigilance heuristics and have not been clinically validated — they serve as a demo-grade signal flag, not a medical recommendation.
- The CTD checklist covers section titles and presence/absence only, not the depth or quality of regulatory content within each section.
- openFDA API calls are rate-limited to low volume; the bundled fallback cache is a small static sample and does not reflect the full FAERS database.
- watsonx.ai LLM summaries are generative and should be reviewed by a qualified pharmacovigilance or regulatory professional before acting on them.

---

## 🏅 What We're Most Proud Of

The end-to-end integration between real FDA public data and IBM watsonx.ai reasoning: a user types a drug name, live adverse-event reports are fetched, PRR statistics surface signals that would otherwise take days to compute manually, and the Granite model instantly explains each signal in plain language a non-statistician can act on. The same LLM integration then pivots to regulatory compliance — two genuinely different use-cases, one coherent AI platform.

---

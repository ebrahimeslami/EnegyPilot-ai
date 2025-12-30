# 📘 PUCT Energy Efficiency Community Portal  
**A RAG-based, community-facing regulatory chatbot for Texas energy efficiency rules**

---

## Overview

This repository provides a **Python-based, Retrieval-Augmented Generation (RAG) portal** designed to help community members, advocates, policymakers, and practitioners **understand Texas Public Utility Commission (PUCT) energy efficiency regulations**, with a focus on:

- **16 TAC §25.181 – Energy Efficiency Goal**
- **16 TAC §25.182 – Energy Efficiency Cost Recovery Factor**
- **16 TAC §25.183 – Reporting and Evaluation of Energy Efficiency Programs**

The portal combines:

- **Authoritative regulatory text** (official PUCT rule PDFs),
- **Local utility program context** (CenterPoint Energy public program pages), and
- **A community-friendly chat interface** (Streamlit),

while enforcing **strict regulatory guardrails** to ensure transparency, traceability, and accuracy.

---

## Motivation

PUCT energy efficiency rules are highly technical and difficult for non-specialists to interpret.  
This tool was developed to:

- Improve **public access** to regulatory information,
- Reduce **misinterpretation of energy efficiency requirements**, and
- Demonstrate how **RAG-based AI systems** can be safely applied to regulatory and policy contexts.

The project emphasizes **regulation-first design**, ensuring that explanations remain grounded in official rule text rather than model inference.

---

## Key Design Principles

### 1. Regulation-First (Authoritative Source of Truth)
PUCT rules are treated as the **sole authoritative regulatory source**.  
All regulatory claims must be explicitly supported by retrieved rule text.

### 2. Separation of Regulatory Text and Program Context
The system uses **two independent vector indexes**:

- **PUCT Rules Index**  
  - §§25.181, 25.182, 25.183 (PDFs from the PUCT)  
  - Used for all regulatory explanations and compliance-related statements

- **CenterPoint Program Context Index**  
  - Public utility program pages  
  - Used only for explanatory, non-regulatory context

This separation ensures users can clearly distinguish:  
**What the rule requires** vs **how programs are implemented locally**

### 3. Community-Facing by Design
The portal is designed for non-technical users and includes:

- Plain-language explanations
- Automatic glossary support
- English / Spanish output toggle
- Transparent citations with page references

---

## Features

### 🔍 Retrieval-Augmented Regulatory Chatbot
- Answers questions using retrieved rule text only
- Provides page-level citations for every regulatory claim
- Refuses to speculate when supporting text is not found

### ⚖️ Regulatory-Only Mode Enforcement
When users select **“PUCT Rules only”**:
- Program logistics questions (rebates, sign-up, eligibility) trigger a warning
- Users are prompted to explicitly enable CenterPoint context if desired

### 🧾 Citation Quality Check
If an answer includes regulatory language (e.g., “must,” “required,” “PUCT rule”) but lacks a valid PUCT citation:
- The response is rejected
- The user is asked to rephrase or increase retrieval depth

### 📚 Built-In Glossary
A curated glossary explains common energy efficiency terms, including:
- kW vs kWh
- EM&V
- EECRF
- Standard Offer Program (SOP)
- Peak demand

Glossary entries appear automatically when relevant.

### 🌐 Bilingual Output
- English and Spanish responses supported
- Citations remain anchored to English regulatory text (authoritative source)

---

## Repository Structure

```
EnergyPilot_puct-ee-portal/
│
├── app.py                     # Streamlit application (GUI + chat)
├── ingest_build_indexes.py    # PDF + HTML ingestion and indexing
├── rag.py                     # Vector index abstraction
├── requirements.txt
├── README.md
│
└── data/
    ├── glossary.json
    ├── raw_pdfs/              # Downloaded PUCT rule PDFs
    ├── raw_html/              # Cached CenterPoint pages
    ├── index/                 # FAISS indexes + metadata
    └── feedback.jsonl         # Optional user feedback log
```

---

## Installation

### 1. Create and activate a virtual environment (Windows example)

```powershell
cd D:\Business\EnergyPilot\EnergyPilot_puct-ee-portal
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

---

## Build the Indexes

This step:
- Downloads official PUCT PDFs,
- Fetches CenterPoint program pages,
- Chunks, embeds, and indexes content into **separate FAISS indexes**.

```powershell
python ingest_build_indexes.py
```

### SSL / Certificate Note

Some environments (e.g., corporate networks) may block TLS verification when downloading from `ftp.puc.texas.gov`.  
The ingestion script includes a **controlled SSL fallback mechanism** using `certifi`.

As a last resort, users may explicitly allow insecure SSL by setting:

```powershell
set PUCT_ALLOW_INSECURE_SSL=1
```

This behavior is **opt-in** and clearly documented in the code.

---

## Run the Portal

```powershell
streamlit run app.py
```

Open the local URL shown in the terminal (typically `http://localhost:8501`).

---

## Intended Use Cases

- Community education and outreach
- Energy justice and equity initiatives
- Local government and NGO support tools
- Academic research and reproducibility
- Policy transparency and trust-building

---

## 📖 Cite This Tool

If you use this repository, portal, or methodology in academic work, policy analysis, community engagement, or derivative tools, please cite it as follows.

### Recommended Citation

**Eslami, E.** (2025). *PUCT Energy Efficiency Community Portal: A Retrieval-Augmented Generation (RAG) Tool for Interpreting Texas Energy Efficiency Regulations (16 TAC §§25.181–25.183).* GitHub repository.  
`https://github.com/<your-username>/<your-repo-name>`

### BibTeX

```bibtex
@software{Eslami_PUCT_EE_Portal_2025,
  author  = {Eslami, Ebrahim},
  title   = {PUCT Energy Efficiency Community Portal: A Retrieval-Augmented Generation (RAG) Tool for Interpreting Texas Energy Efficiency Regulations (16 TAC §§25.181--25.183)},
  year    = {2025},
  url     = {https://github.com/<your-username>/<your-repo-name>},
  note    = {Python-based RAG system using authoritative PUCT rule text and separate utility program context}
}
```

### When to Cite
Please cite this tool if you:
- Use it to interpret or explain PUCT energy efficiency rules
- Reference its RAG architecture or regulatory guardrail design
- Use screenshots, outputs, or methodological components

---

## Disclaimer

This tool is **informational only**.  
It does **not** constitute legal advice, regulatory approval, or official interpretation by the Texas Public Utility Commission or any utility provider.

The project is **independent** and **not affiliated with or endorsed by** the PUCT or CenterPoint Energy.

---


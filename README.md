# EnegyPilot-ai
A RAG-based, community-facing regulatory chatbot for Public Utility Commission of Texas (PUCT) Energy Efficiency Chapter


Overview
This repository provides a Python-based, Retrieval-Augmented Generation (RAG) portal designed to help community members, advocates, and practitioners understand Texas Public Utility Commission (PUCT) energy efficiency regulations, with a focus on:
  + 16 TAC §25.181 – Energy Efficiency Goal
  + 16 TAC §25.182 – Energy Efficiency Cost Recovery Factor
  + 16 TAC §25.183 – Reporting and Evaluation of Energy Efficiency Programs

The tool combines:
  + Authoritative regulatory text (PUCT PDFs)
  + Local utility program context (CenterPoint Energy program pages)
  + A community-friendly chat interface (Streamlit)

while maintaining strict regulatory guardrails to prevent hallucinations or misrepresentation of rules.


Key Design Principles:
1. Regulation-First (Authoritative)
PUCT rules are treated as the sole source of regulatory truth.
All regulatory claims must be supported by retrieved rule text.

2. Separate Context Layers
The system uses two independent vector indexes:
  + PUCT Rules Index – authoritative legal text
  + CenterPoint Program Context Index – non-regulatory, explanatory program information

This separation ensures users can clearly distinguish:
  “What the rule requires” vs “How programs are implemented locally.”

3. Community-Facing by Design
The portal is designed for non-technical users, featuring:
  + Plain-language explanations
  + Built-in glossary
  + English / Spanish toggle
  + Transparent citations with page references


Features:
  + RAG-Based Regulatory Chatbot
  + Answers questions using only retrieved rule text
  + Provides page-level citations for every regulatory statement
  + Refuses to answer if no supporting rule text is found

Regulatory-Only Mode Enforcement
If users ask program logistics questions (e.g., rebates, sign-up, eligibility) while in PUCT Rules Only mode, the system:
Warns the user, and Suggests enabling CenterPoint context explicitly

Citation Quality Check
If a response contains regulatory language but no valid PUCT citation, the system:
  + Rejects the answer
  + Prompts the user to rephrase or increase retrieval depth

Glossary Layer
A curated glossary explains common energy efficiency terms:
  + kW vs kWh
  + EM&V
  + EECRF
  + Standard Offer Program
  + Peak demand

Glossary entries appear automatically when relevant.

Bilingual Output
  + English and Spanish responses
  + Citations remain anchored to English regulatory text (authoritative source)

Repository Structure
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

Installation
1. Create and activate a virtual environment (Windows)
cd D:\Business\EnergyPilot\EnergyPilot_puct-ee-portal
python -m venv .venv
.venv\Scripts\activate

2. Install dependencies
pip install -r requirements.txt

3. Build the Indexes (One-Time or When Sources Change)
This step:
  + Downloads official PUCT PDFs
  + Fetches CenterPoint program pages
  + Chunks, embeds, and indexes content into separate FAISS indexes

python ingest_build_indexes.py

SSL note:
If you are behind SSL inspection or corporate proxies, the ingestion script supports a safe fallback mechanism using certifi. **(See inline documentation in ingest_build_indexes.py.)**

4. Run the Portal
streamlit run app.py

Then open the local URL shown in the terminal (usually http://localhost:8501).


Intended Use Cases:
  + Community education and outreach
  + Energy justice and equity initiatives
  + Local government and NGO support tools
  + Academic research and reproducibility
  + Policy transparency and trust-building

Important Disclaimer"
This tool is informational only. It does not constitute legal advice, regulatory approval, or official interpretation by the Texas Public Utility Commission or any utility provider.

Roadmap (Optional Extensions)
  + Add additional PUCT Chapter 25 rules
  + Expand to other Texas TDUs
  + Add official Spanish program materials
  + Deploy as a hosted public portal
  + Add audit logging for regulatory traceability

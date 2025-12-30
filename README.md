# PUCT Energy Efficiency Portal (RAG-first, Python)

This project builds a community-facing Streamlit portal focused on Texas PUCT energy efficiency rules:
- 16 TAC §25.181
- 16 TAC §25.182
- 16 TAC §25.183

It uses **RAG** with **separate indexes**:
1) PUCT Rules (authoritative)
2) CenterPoint Program Context (non-regulatory context)

## 1) Setup (Windows example)

Working directory example:
`D:\Business\EnergyPilot\puct-ee-portal`

### Create venv
```bash
cd D:\Business\EnergyPilot
mkdir puct-ee-portal
# copy project files here (or unzip)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Configure OpenAI (optional)
Set environment variable:
```bash
setx OPENAI_API_KEY "YOUR_KEY_HERE"
```
Restart terminal after setx.

If you prefer a different LLM backend, edit `llm_answer()` inside `app.py`.

## 2) Build indexes (downloads PDFs + fetches CenterPoint pages)

```bash
python ingest_build_indexes.py
```

Outputs:
- `data/index/puct_rules.*`
- `data/index/centerpoint_context.*`

## 3) Run the portal

```bash
streamlit run app.py
```

## 4) Key safety/quality features

### A) Regulatory-only mode enforcement
If the user asks a clearly "program logistics" question while in **PUCT Rules only** mode,
the app will warn them and recommend turning on CenterPoint context.

### B) Citation quality check
If the assistant response includes regulatory statements, the app requires at least one
PUCT Rules citation. If none, it will return a safe message rather than speculate.

## 5) Notes
- PUCT Rules are treated as authoritative.
- CenterPoint pages are used only as program context and are labeled as such.
- Informational only; not legal advice.

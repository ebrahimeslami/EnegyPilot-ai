\
import json
import re
import streamlit as st

from rag import VectorIndex, format_citations


# -----------------------------
# Heuristics for "program logistics" questions
# -----------------------------
PROGRAM_LOGISTICS_PATTERNS = [
    r"\brebate\b", r"\bincentive\b", r"\bsign\s*up\b", r"\benroll\b", r"\bapply\b",
    r"\bapplication\b", r"\bhow do i\b", r"\bwhere do i\b", r"\bcontractor\b",
    r"\bparticipat(e|ion)\b", r"\beligib(le|ility)\b", r"\bfree\b", r"\bdiscount\b",
    r"\bform\b", r"\bwebsite\b", r"\bphone\b", r"\bemail\b"
]

def looks_like_program_logistics(question: str) -> bool:
    q = question.lower()
    return any(re.search(p, q) for p in PROGRAM_LOGISTICS_PATTERNS)


# -----------------------------
# LLM hook (swap as needed)
# -----------------------------
def llm_answer(system_msg: str, user_msg: str) -> str:
    """
    Default: OpenAI. Replace if you prefer another backend.
    """
    try:
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return (
            "(LLM not configured)\n"
            f"{e}\n\n"
            "Configure OPENAI_API_KEY and `pip install openai`, or replace llm_answer() with your preferred backend."
        )


def build_prompt(lang: str, question: str, rule_ctx: list, cp_ctx: list) -> tuple[str, str]:
    # Context blocks
    def ctx_block(chunks, header):
        parts = []
        for i, c in enumerate(chunks):
            if c.get("rule_id"):
                parts.append(
                    f"[{header} {i+1}] §{c['rule_id']} {c['title']} (pp. {c['page_start']}-{c['page_end']}):\n{c['text']}"
                )
            else:
                parts.append(
                    f"[{header} {i+1}] {c['title']} (CenterPoint Program Context):\n{c['text']}"
                )
        return "\n\n".join(parts)

    rules_text = ctx_block(rule_ctx, "PUCT")
    cp_text = ctx_block(cp_ctx, "CP") if cp_ctx else ""

    # System message enforces: rules are authoritative; CP is context only.
    if lang == "Español":
        system_msg = (
            "Eres un asistente comunitario que explica reglas de eficiencia energética de la PUCT de Texas. "
            "Responde en español usando SOLO el texto de contexto proporcionado. "
            "Las reglas de la PUCT son la autoridad principal. "
            "El contenido de CenterPoint es contexto del programa (no texto regulatorio). "
            "No inventes requisitos ni referencias. Si no está en el contexto, di: "
            "\"No pude localizar eso en el texto indexado.\""
        )
        where_rules = "Dónde aparece (Reglas PUCT)"
        where_cp = "Información relacionada (CenterPoint, contexto del programa)"
    else:
        system_msg = (
            "You are a community-facing assistant explaining Texas PUCT energy efficiency rules. "
            "Answer in plain language using ONLY the provided context. "
            "PUCT rules are authoritative. CenterPoint text is program context (not regulatory). "
            "Do not invent requirements or citations. If not supported by context, say: "
            "\"I could not locate that in the indexed text.\""
        )
        where_rules = "Where this appears (PUCT Rules)"
        where_cp = "Related info (CenterPoint program context)"

    user_msg = f"""
Question:
{question}

Requirements:
- Provide a plain-language answer (bullets preferred).
- Separate regulatory statements from program-context statements.
- Include a citations section with two headings:
  1) {where_rules}
  2) {where_cp} (only if CenterPoint context was used)
- Do not include any regulatory claim unless it is supported by the PUCT Rules context.

PUCT Rules Context:
{rules_text}

CenterPoint Program Context:
{cp_text}
""".strip()

    return system_msg, user_msg


def load_glossary(path="data/glossary.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def requires_rule_citation(answer: str) -> bool:
    """
    If the assistant made regulatory statements, we require at least one PUCT citation line.
    Heuristic: if it mentions 'PUCT' or '§25.' or 'rule' or 'shall/must/required' then treat as regulatory.
    """
    a = answer.lower()
    regulatory_markers = ["§25.", "puct", "rule", "shall", "must", "required", "compliance", "tariff"]
    return any(m in a for m in regulatory_markers)


def has_puct_citations(citations_text: str) -> bool:
    return bool(re.search(r"PUCT:\s*§25\.\d+", citations_text))


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="PUCT Energy Efficiency Portal", layout="wide")
st.title("PUCT Energy Efficiency Portal")
st.caption("Corpus: 16 TAC §25.181, §25.182, §25.183 (PUCT rules) + CenterPoint program context. Informational only; not legal advice.")

with st.sidebar:
    st.header("Controls")
    lang = st.selectbox("Language / Idioma", ["English", "Español"])
    source_mode = st.radio("Sources", ["PUCT Rules only", "PUCT Rules + CenterPoint context"])
    k_rules = st.slider("PUCT retrieved passages (k)", 3, 10, 6)
    k_cp = st.slider("CenterPoint retrieved passages (k)", 0, 8, 3)
    st.markdown("---")
    st.markdown("**Policy:** PUCT rules are authoritative. CenterPoint text is program context only.")

@st.cache_resource
def load_indexes():
    return {
        "rules": VectorIndex("puct_rules"),
        "cp": VectorIndex("centerpoint_context"),
    }

indexes = load_indexes()
glossary = load_glossary()

tab_ask, tab_browse, tab_cp, tab_gloss, tab_feedback = st.tabs(
    ["Ask", "Browse Rules", "CenterPoint Context", "Glossary", "Feedback"]
)

# -----------------------------
# Ask (Chat)
# -----------------------------
with tab_ask:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    q = st.chat_input("Ask about PUCT EE goals, reporting, evaluation, or cost recovery...")
    if q:
        # Feature 1: Regulatory-only mode enforcement
        if source_mode == "PUCT Rules only" and looks_like_program_logistics(q):
            if lang == "Español":
                warn = (
                    "Parece que tu pregunta es sobre **cómo participar / registrarse / incentivos** (logística del programa). "
                    "En este momento estás en **solo Reglas PUCT**. Para respuestas sobre programas locales (CenterPoint), "
                    "cambia a **PUCT Rules + CenterPoint context** en la barra lateral."
                )
            else:
                warn = (
                    "Your question looks like **program logistics** (sign-up, incentives, rebates, eligibility). "
                    "You are currently in **PUCT Rules only** mode. For local program details (CenterPoint), "
                    "switch to **PUCT Rules + CenterPoint context** in the sidebar."
                )
            st.warning(warn)

        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)

        # Quick glossary assist
        glossary_hits = [g for g in glossary if g["term"].lower() in q.lower()]
        glossary_box = ""
        if glossary_hits:
            if lang == "Español":
                glossary_box = "Glosario (referencia rápida):\n" + "\n".join([f"- **{g['term']}**: {g['definition']}" for g in glossary_hits])
            else:
                glossary_box = "Glossary (quick reference):\n" + "\n".join([f"- **{g['term']}**: {g['definition']}" for g in glossary_hits])

        # Retrieve
        rule_ctx = indexes["rules"].retrieve(q, k=k_rules)

        cp_ctx = []
        if source_mode == "PUCT Rules + CenterPoint context" and k_cp > 0:
            cp_ctx = indexes["cp"].retrieve(q, k=k_cp)

        rules_cites = format_citations(rule_ctx, label="PUCT")
        cp_cites = format_citations(cp_ctx, label="CenterPoint") if cp_ctx else ""

        # Build prompt + call LLM
        system_msg, user_msg = build_prompt(lang, q, rule_ctx, cp_ctx)
        ans = llm_answer(system_msg, user_msg)

        # Append glossary box if present
        if glossary_box:
            ans = glossary_box + "\n\n---\n\n" + ans

        # Add citations if the model didn't include them
        if "Where this appears" not in ans and "Dónde aparece" not in ans:
            if lang == "Español":
                ans += f"\n\n**Dónde aparece (Reglas PUCT)**\n{rules_cites}"
                if cp_cites:
                    ans += f"\n\n**Información relacionada (CenterPoint, contexto del programa)**\n{cp_cites}"
            else:
                ans += f"\n\n**Where this appears (PUCT Rules)**\n{rules_cites}"
                if cp_cites:
                    ans += f"\n\n**Related info (CenterPoint program context)**\n{cp_cites}"

        # Feature 2: Citation quality check
        # If answer appears regulatory, require at least one PUCT citation.
        combined_cites = rules_cites
        if requires_rule_citation(ans) and not has_puct_citations(combined_cites):
            if lang == "Español":
                ans = (
                    "No pude proporcionar una respuesta confiable porque no encontré una cita sólida en las "
                    "Reglas PUCT indexadas para respaldar una afirmación regulatoria.\n\n"
                    "Intenta reformular tu pregunta (por ejemplo, menciona §25.181, §25.182 o §25.183) "
                    "o aumenta el valor de 'PUCT retrieved passages (k)'."
                )
            else:
                ans = (
                    "I couldn’t provide a reliable answer because I did not find a strong supporting passage in the "
                    "indexed PUCT rules to back a regulatory statement.\n\n"
                    "Try rephrasing your question (e.g., reference §25.181, §25.182, or §25.183) "
                    "or increase 'PUCT retrieved passages (k)'."
                )

        with st.chat_message("assistant"):
            st.markdown(ans)

            with st.expander("Show retrieved passages"):
                st.subheader("PUCT Rules")
                for c in rule_ctx:
                    st.markdown(f"**§{c['rule_id']} {c['title']} (pp. {c['page_start']}-{c['page_end']})**  \nScore: {c['score']:.3f}")
                    st.text(c["text"][:3500] + ("..." if len(c["text"]) > 3500 else ""))

                if cp_ctx:
                    st.subheader("CenterPoint Program Context")
                    for c in cp_ctx:
                        st.markdown(f"**{c['title']}**  \nScore: {c['score']:.3f}")
                        st.text(c["text"][:3500] + ("..." if len(c["text"]) > 3500 else ""))

        st.session_state.messages.append({"role": "assistant", "content": ans})


# -----------------------------
# Browse Rules
# -----------------------------
with tab_browse:
    st.markdown("### Browse indexed PUCT rules (extracted chunks)")
    rule = st.selectbox("Select rule", ["25.181", "25.182", "25.183"])
    query = st.text_input("Search within indexed rule text (keyword)")

    all_chunks = indexes["rules"].chunks
    filt = [c for c in all_chunks if c.get("rule_id") == rule]
    if query:
        ql = query.lower()
        filt = [c for c in filt if ql in (c.get("text", "").lower())]

    st.write(f"Chunks: {len(filt)}")
    for c in filt[:50]:
        st.markdown(f"**§{c['rule_id']} {c['title']} (pp. {c['page_start']}-{c['page_end']})**")
        st.text(c["text"][:2000] + ("..." if len(c["text"]) > 2000 else ""))
        st.divider()


# -----------------------------
# CenterPoint Context
# -----------------------------
with tab_cp:
    st.markdown("### CenterPoint program context (non-regulatory)")
    st.markdown("This content helps residents understand program options and participation. It is not regulatory text.")
    search = st.text_input("Search CenterPoint context (keyword)")
    cp_chunks = indexes["cp"].chunks
    filt = cp_chunks
    if search:
        sl = search.lower()
        filt = [c for c in cp_chunks if sl in (c.get("text", "").lower())]
    st.write(f"Chunks: {len(filt)}")
    for c in filt[:50]:
        st.markdown(f"**{c['title']}**")
        st.caption(c.get("source_url", ""))
        st.text(c["text"][:2000] + ("..." if len(c["text"]) > 2000 else ""))
        st.divider()


# -----------------------------
# Glossary
# -----------------------------
with tab_gloss:
    st.markdown("### Glossary")
    s = st.text_input("Search terms")
    items = glossary
    if s:
        sl = s.lower()
        items = [g for g in glossary if sl in g["term"].lower() or sl in g["definition"].lower()]
    for g in items:
        st.markdown(f"**{g['term']}**")
        st.write(g["definition"])
        st.divider()


# -----------------------------
# Feedback
# -----------------------------
with tab_feedback:
    st.markdown("### Feedback")
    st.markdown("Log quick feedback locally (JSONL) so you can improve prompts, glossary, and sources.")
    col1, col2 = st.columns(2)
    with col1:
        thumbs = st.selectbox("Was the answer helpful?", ["", "Yes", "No"])
    with col2:
        comment = st.text_input("Comment (optional)")
    if st.button("Save feedback"):
        rec = {"helpful": thumbs, "comment": comment}
        with open("data/feedback.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        st.success("Saved.")

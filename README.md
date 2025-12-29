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

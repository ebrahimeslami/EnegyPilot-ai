\
import os
import re
import json
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional

import requests
import fitz  # PyMuPDF
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import trafilatura


# -----------------------------
# Sources
# -----------------------------
PUCT_PDFS = [
    {
        "doc_id": "puct_25_181",
        "rule_id": "25.181",
        "title": "Energy Efficiency Goal",
        "url": "https://ftp.puc.texas.gov/public/puct-info/agency/rulesnlaws/subrules/electric/25.181/25.181.pdf",
        "source_type": "puct_rule",
    },
    {
        "doc_id": "puct_25_182",
        "rule_id": "25.182",
        "title": "Energy Efficiency Cost Recovery Factor",
        "url": "https://ftp.puc.texas.gov/public/puct-info/agency/rulesnlaws/subrules/electric/25.182/25.182.pdf",
        "source_type": "puct_rule",
    },
    {
        "doc_id": "puct_25_183",
        "rule_id": "25.183",
        "title": "Reporting and Evaluation of Energy Efficiency Programs",
        "url": "https://ftp.puc.texas.gov/public/puct-info/agency/rulesnlaws/subrules/electric/25.183/25.183.pdf",
        "source_type": "puct_rule",
    },
]

# Curated CenterPoint program context (non-regulatory)
CENTERPOINT_PAGES = [
    {
        "doc_id": "cp_res_ee",
        "title": "CenterPoint Residential Electric Efficiency Programs",
        "url": "https://www.centerpointenergy.com/en-us/residential/save-energy-money/electric-efficiency-programs/residential-electric-efficiency",
        "source_type": "centerpoint_context",
    },
    {
        "doc_id": "cp_res_sop",
        "title": "CenterPoint Residential Standard Offer Program",
        "url": "https://www.centerpointenergy.com/en-us/SaveEnergyandMoney/Pages/residential-standard-offer-program.aspx",
        "source_type": "centerpoint_context",
    },
    {
        "doc_id": "cp_ci_sop",
        "title": "CenterPoint Commercial & Industrial Standard Offer Program",
        "url": "https://www.centerpointenergy.com/en-us/SaveEnergyandMoney/Pages/commercial-industrial-standard-offer-program.aspx",
        "source_type": "centerpoint_context",
    },
    {
        "doc_id": "cp_bus_ee",
        "title": "CenterPoint Business Efficiency Programs",
        "url": "https://www.centerpointenergy.com/en-us/business/save-energy-money/electric-efficiency-programs/business-efficiency-programs",
        "source_type": "centerpoint_context",
    },
]


# -----------------------------
# Paths
# -----------------------------
DATA_DIR = "data"
RAW_PDF_DIR = os.path.join(DATA_DIR, "raw_pdfs")
RAW_HTML_DIR = os.path.join(DATA_DIR, "raw_html")
INDEX_DIR = os.path.join(DATA_DIR, "index")

os.makedirs(RAW_PDF_DIR, exist_ok=True)
os.makedirs(RAW_HTML_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source_type: str
    rule_id: Optional[str]
    title: str
    source_url: str
    page_start: Optional[int]
    page_end: Optional[int]
    text: str


def _sha_id(*parts: str) -> str:
    h = hashlib.sha1()
    h.update("|".join(parts).encode("utf-8"))
    return h.hexdigest()[:16]


def download_pdf(url: str, out_path: str) -> None:
    import certifi
    import requests

    # 1) normal download
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)
        return
    except requests.exceptions.SSLError:
        pass

    # 2) retry using certifi bundle explicitly
    try:
        r = requests.get(url, timeout=60, verify=certifi.where())
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)
        return
    except requests.exceptions.SSLError:
        pass

    # 3) LAST RESORT: allow verify=False only if user explicitly opts-in
    allow_insecure = os.getenv("PUCT_ALLOW_INSECURE_SSL", "").strip() == "1"
    if not allow_insecure:
        raise RuntimeError(
            "SSL verification failed downloading PUCT PDF.\n"
            "Try setting REQUESTS_CA_BUNDLE to certifi.where(), or if you are behind SSL inspection and accept the risk, "
            "set env var PUCT_ALLOW_INSECURE_SSL=1 and rerun."
        )

    r = requests.get(url, timeout=60, verify=False)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)



def extract_pages(pdf_path: str) -> List[Tuple[int, str]]:
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(len(doc)):
        text = doc[i].get_text("text") or ""
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            pages.append((i + 1, text))
    return pages


SECTION_HINT_RE = re.compile(r"^\(\w+\)\s+", re.MULTILINE)

def chunk_rule_pdf(rule: Dict[str, Any], pages: List[Tuple[int, str]],
                   max_chars: int = 2400, overlap_chars: int = 250) -> List[Chunk]:
    segments: List[Dict[str, Any]] = []
    for pno, text in pages:
        starts = [m.start() for m in SECTION_HINT_RE.finditer(text)]
        if not starts:
            segments.append({"pno": pno, "seg": text})
            continue
        starts.append(len(text))
        for si in range(len(starts) - 1):
            seg = text[starts[si]:starts[si + 1]].strip()
            if seg:
                segments.append({"pno": pno, "seg": seg})

    chunks: List[Chunk] = []
    buf = ""
    buf_pages: List[int] = []

    def flush():
        nonlocal buf, buf_pages
        if not buf.strip():
            buf, buf_pages[:] = "", []
            return
        ps, pe = min(buf_pages), max(buf_pages)
        cid = _sha_id(rule["doc_id"], str(ps), buf[:200])
        chunks.append(
            Chunk(
                chunk_id=cid,
                doc_id=rule["doc_id"],
                source_type=rule["source_type"],
                rule_id=rule["rule_id"],
                title=rule["title"],
                source_url=rule["url"],
                page_start=ps,
                page_end=pe,
                text=buf.strip(),
            )
        )
        buf, buf_pages[:] = "", []

    for seg in segments:
        seg_text, pno = seg["seg"], seg["pno"]
        if len(buf) + len(seg_text) + 2 <= max_chars:
            buf = (buf + "\n\n" + seg_text).strip()
            buf_pages.append(pno)
        else:
            flush()
            if len(seg_text) > max_chars:
                start = 0
                while start < len(seg_text):
                    end = min(start + max_chars, len(seg_text))
                    part = seg_text[start:end].strip()
                    if part:
                        buf = part
                        buf_pages = [pno]
                        flush()
                    start = max(0, end - overlap_chars)
                    if start == end:
                        break
            else:
                buf = seg_text
                buf_pages = [pno]

    flush()
    return chunks


def fetch_html_text(url: str) -> str:
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(downloaded, include_tables=True, include_comments=False) or ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def chunk_html_page(doc: Dict[str, Any], text: str, max_chars: int = 2400, overlap_chars: int = 250) -> List[Chunk]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[Chunk] = []
    buf = ""

    def flush():
        nonlocal buf
        if not buf.strip():
            buf = ""
            return
        cid = _sha_id(doc["doc_id"], buf[:200])
        chunks.append(
            Chunk(
                chunk_id=cid,
                doc_id=doc["doc_id"],
                source_type=doc["source_type"],
                rule_id=None,
                title=doc["title"],
                source_url=doc["url"],
                page_start=None,
                page_end=None,
                text=buf.strip(),
            )
        )
        buf = ""

    for p in parts:
        if len(buf) + len(p) + 2 <= max_chars:
            buf = (buf + "\n\n" + p).strip()
        else:
            flush()
            if len(p) > max_chars:
                start = 0
                while start < len(p):
                    end = min(start + max_chars, len(p))
                    buf = p[start:end].strip()
                    flush()
                    start = max(0, end - overlap_chars)
                    if start == end:
                        break
            else:
                buf = p

    flush()
    return chunks


def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    faiss.normalize_L2(embeddings)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def save_index(index: faiss.Index, chunks: List[Chunk], index_name: str, embed_model_name: str) -> None:
    out_faiss = os.path.join(INDEX_DIR, f"{index_name}.faiss")
    out_chunks = os.path.join(INDEX_DIR, f"{index_name}_chunks.json")
    out_meta = os.path.join(INDEX_DIR, f"{index_name}_meta.json")

    faiss.write_index(index, out_faiss)
    with open(out_chunks, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in chunks], f, ensure_ascii=False, indent=2)
    with open(out_meta, "w", encoding="utf-8") as f:
        json.dump({"embedding_model": embed_model_name}, f, indent=2)

    print(f"[saved] {index_name}: {len(chunks)} chunks -> {out_faiss}")


def main():
    embed_model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embedder = SentenceTransformer(embed_model_name)

    # A) PUCT rules index
    puct_chunks: List[Chunk] = []
    for rule in PUCT_PDFS:
        pdf_path = os.path.join(RAW_PDF_DIR, f"{rule['rule_id'].replace('.', '_')}.pdf")
        if not os.path.exists(pdf_path):
            print(f"[download pdf] {rule['rule_id']}")
            download_pdf(rule["url"], pdf_path)
        else:
            print(f"[skip pdf] {rule['rule_id']} exists")

        pages = extract_pages(pdf_path)
        rule_chunks = chunk_rule_pdf(rule, pages)
        print(f"[chunk pdf] {rule['rule_id']}: {len(rule_chunks)} chunks")
        puct_chunks.extend(rule_chunks)

    puct_emb = embedder.encode([c.text for c in puct_chunks], batch_size=32, show_progress_bar=True, convert_to_numpy=True)
    puct_index = build_faiss_index(puct_emb)
    save_index(puct_index, puct_chunks, index_name="puct_rules", embed_model_name=embed_model_name)

    # B) CenterPoint program context index
    cp_chunks: List[Chunk] = []
    for doc in CENTERPOINT_PAGES:
        out_path = os.path.join(RAW_HTML_DIR, f"{doc['doc_id']}.txt")
        if not os.path.exists(out_path):
            print(f"[fetch html] {doc['doc_id']}")
            text = fetch_html_text(doc["url"])
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
        else:
            print(f"[skip html] {doc['doc_id']} exists")
            with open(out_path, "r", encoding="utf-8") as f:
                text = f.read()

        page_chunks = chunk_html_page(doc, text)
        print(f"[chunk html] {doc['doc_id']}: {len(page_chunks)} chunks")
        cp_chunks.extend(page_chunks)

    cp_emb = embedder.encode([c.text for c in cp_chunks], batch_size=32, show_progress_bar=True, convert_to_numpy=True)
    cp_index = build_faiss_index(cp_emb)
    save_index(cp_index, cp_chunks, index_name="centerpoint_context", embed_model_name=embed_model_name)

    print("[done] built separate indexes in data/index/")


if __name__ == "__main__":
    main()

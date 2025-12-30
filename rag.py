\
import json
from typing import List, Dict, Any
import faiss
from sentence_transformers import SentenceTransformer


class VectorIndex:
    def __init__(self, index_prefix: str, index_dir: str = "data/index"):
        self.index_prefix = index_prefix
        self.index = faiss.read_index(f"{index_dir}/{index_prefix}.faiss")
        with open(f"{index_dir}/{index_prefix}_chunks.json", "r", encoding="utf-8") as f:
            self.chunks: List[Dict[str, Any]] = json.load(f)
        with open(f"{index_dir}/{index_prefix}_meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.embedder = SentenceTransformer(meta["embedding_model"])

    def retrieve(self, query: str, k: int = 6) -> List[Dict[str, Any]]:
        import numpy as np
        q_emb = self.embedder.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(q_emb)
        scores, idxs = self.index.search(q_emb, k)
        out = []
        for score, idx in zip(scores[0].tolist(), idxs[0].tolist()):
            if idx < 0:
                continue
            ch = dict(self.chunks[idx])
            ch["score"] = float(score)
            out.append(ch)
        return out


def format_citations(chunks: List[Dict[str, Any]], label: str) -> str:
    lines = []
    for c in chunks:
        if c.get("rule_id"):
            ps, pe = c.get("page_start"), c.get("page_end")
            if ps is not None and pe is not None:
                pg = f"p. {ps}" if ps == pe else f"pp. {ps}-{pe}"
            else:
                pg = "page n/a"
            lines.append(f"- {label}: §{c['rule_id']} ({c['title']}), {pg}")
        else:
            lines.append(f"- {label}: {c['title']}")
    # dedupe preserve order
    seen = set()
    deduped = []
    for l in lines:
        if l not in seen:
            seen.add(l)
            deduped.append(l)
    return "\n".join(deduped)

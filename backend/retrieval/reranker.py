"""Cross-encoder reranker (ms-marco-MiniLM)."""
"""Cross-encoder reranker. Re-scores (query, chunk) pairs directly for final ordering.

Uses transformers (no sentence-transformers dep). The model scores each pair; higher =
more relevant. Model + tokenizer load lazily (heavy) and warm via load_reranker().

The model call (_score_pairs) is separated from the ordering (rerank) so the ordering
logic is testable without downloading the model.
"""
import os

# Force the PyTorch backend: some environments ship a TensorFlow build that conflicts with
# NumPy 2.x and crashes on import. We only need torch, so tell transformers to skip TF/Flax.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from config import settings
from retrieval.dense_index import Retrieved

_tok = None
_model = None
_BATCH = 32


def load_reranker():
    global _tok, _model
    if _model is None:
        _tok = AutoTokenizer.from_pretrained(settings.RERANKER_MODEL)
        _model = AutoModelForSequenceClassification.from_pretrained(settings.RERANKER_MODEL)
        _model.eval()
    return _model


def _score_pairs(query: str, texts: list[str]) -> list[float]:
    load_reranker()
    scores: list[float] = []
    with torch.no_grad():
        for i in range(0, len(texts), _BATCH):
            batch = texts[i:i + _BATCH]
            enc = _tok([query] * len(batch), batch, padding=True, truncation=True,
                       max_length=512, return_tensors="pt")
            logits = _model(**enc).logits.squeeze(-1)
            scores.extend(logits.tolist() if logits.dim() else [logits.item()])
    return scores


def rerank(query: str, candidates: list[Retrieved], top_k: int | None = None) -> list[Retrieved]:
    top_k = top_k or settings.RERANK_TOP_K
    if not candidates:
        return []
    scores = _score_pairs(query, [c.content for c in candidates])
    for c, s in zip(candidates, scores):
        c.score = float(s)
    return sorted(candidates, key=lambda c: c.score, reverse=True)[:top_k]
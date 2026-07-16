"""RAG over the Saudi-context knowledge base: LangChain + ChromaDB.

Embeddings degrade gracefully through three tiers so the app always starts:

  1. OpenAI `text-embedding-3-small`  - if OPENAI_API_KEY is set (best quality)
  2. HuggingFace all-MiniLM-L6-v2     - local, no API key, if the package is installed
  3. HashingEmbeddings                - pure Python, zero dependencies, always works

Tier 3 exists because a hackathon demo must never die on a missing model download. It is
a genuine bag-of-words vector space - crude next to a transformer, but over seven topical
documents it retrieves the right file, which is all this pipeline is asked to do.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from functools import lru_cache
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    HF_EMBED_MODEL,
    OPENAI_API_KEY,
    OPENAI_EMBED_MODEL,
    RETRIEVER_TOP_K,
)

log = logging.getLogger(__name__)

EMBED_DIM = 384  # matches all-MiniLM-L6-v2, so the tiers are interchangeable


class HashingEmbeddings(Embeddings):
    """Deterministic bag-of-words embeddings with no model and no network.

    Each word (and each adjacent word pair, which captures phrases like "emergency fund")
    is hashed into a fixed-width vector with a sub-linear term-frequency weight. Vectors
    are L2-normalised so that cosine distance is meaningful.
    """

    def __init__(self, dim: int = EMBED_DIM) -> None:
        self.dim = dim

    def _tokens(self, text: str) -> list[str]:
        words = re.findall(r"[a-z0-9]+", text.lower())
        bigrams = [f"{a}_{b}" for a, b in zip(words, words[1:])]
        return words + bigrams

    def _vector(self, text: str) -> list[float]:
        counts: dict[int, float] = {}
        for token in self._tokens(text):
            digest = hashlib.md5(token.encode()).digest()
            index = int.from_bytes(digest[:4], "little") % self.dim
            # A sign bit spreads collisions instead of always compounding them.
            sign = 1.0 if digest[4] & 1 else -1.0
            counts[index] = counts.get(index, 0.0) + sign

        vector = [0.0] * self.dim
        for index, value in counts.items():
            # Opposite-signed collisions can cancel exactly; log(0) is undefined, and a
            # zero weight is the right answer anyway.
            if value == 0:
                continue
            # Sub-linear scaling: a word said ten times is not ten times as relevant.
            vector[index] = math.copysign(1 + math.log(abs(value)), value)

        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@lru_cache(maxsize=1)
def get_embeddings() -> tuple[Embeddings, str]:
    """Return the best embedding backend available, and its name (for logging/UI)."""
    if OPENAI_API_KEY:
        try:
            from langchain_openai import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings(
                model=OPENAI_EMBED_MODEL, api_key=OPENAI_API_KEY
            )
            embeddings.embed_query("healthcheck")  # fail fast on a bad key
            log.info("Embeddings: OpenAI %s", OPENAI_EMBED_MODEL)
            return embeddings, f"openai:{OPENAI_EMBED_MODEL}"
        except Exception as exc:  # noqa: BLE001 - any failure must fall through
            log.warning("OpenAI embeddings unavailable (%s); falling back.", exc)

    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model_name=HF_EMBED_MODEL)
        log.info("Embeddings: local HuggingFace %s", HF_EMBED_MODEL)
        return embeddings, f"huggingface:{HF_EMBED_MODEL}"
    except Exception as exc:  # noqa: BLE001
        log.warning("HuggingFace embeddings unavailable (%s); falling back.", exc)

    log.warning("Embeddings: built-in hashing fallback (no model). Retrieval still works.")
    return HashingEmbeddings(), "hashing-fallback"


@lru_cache(maxsize=1)
def get_vectorstore():
    """Open the persisted Chroma collection. Read-only at serve time - the server never
    re-embeds, which is what keeps startup fast."""
    from langchain_chroma import Chroma

    embeddings, _ = get_embeddings()
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
        # Cosine space: our vectors are normalised, so distance in [0, 2] and
        # relevance = 1 - distance reads as a similarity score.
        collection_metadata={"hnsw:space": "cosine"},
    )


def is_ingested() -> bool:
    """Has ingest.py been run? Used for a friendly error instead of an empty answer."""
    try:
        return get_vectorstore()._collection.count() > 0
    except Exception:  # noqa: BLE001
        return False


def retrieve(query: str, k: int = RETRIEVER_TOP_K) -> list[dict[str, Any]]:
    """Top-k knowledge-base passages with similarity scores.

    Returns [] rather than raising: a missing knowledge base should degrade the answer,
    not break the request.
    """
    try:
        store = get_vectorstore()
        hits: list[tuple[Document, float]] = store.similarity_search_with_score(query, k=k)
    except Exception as exc:  # noqa: BLE001
        log.warning("Retrieval failed: %s", exc)
        return []

    passages = []
    for doc, distance in hits:
        passages.append(
            {
                "content": doc.page_content.strip(),
                "source": doc.metadata.get("source", "knowledge base"),
                "title": doc.metadata.get("title", ""),
                # Cosine distance -> similarity. Clamped because approximate indexes can
                # return marginally out-of-range values.
                "score": round(max(0.0, min(1.0, 1.0 - distance)), 3),
            }
        )
    return passages


def format_context(passages: list[dict[str, Any]]) -> str:
    """Render retrieved passages for the LLM prompt, with filenames so it can cite them."""
    if not passages:
        return "(no knowledge-base passages retrieved)"
    blocks = []
    for i, p in enumerate(passages, 1):
        blocks.append(
            f"[{i}] source: {p['source']} (relevance {p['score']})\n{p['content']}"
        )
    return "\n\n".join(blocks)

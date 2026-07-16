"""One-time ingest: knowledge/*.md -> chunks -> embeddings -> persistent ChromaDB.

Run once before starting the server:

    python backend/ingest.py

The Flask app only *reads* the persisted store, so startup stays fast and no embedding
work happens on the request path.
"""

from __future__ import annotations

import logging

import sys

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHROMA_DIR,
    COLLECTION_NAME,
    KNOWLEDGE_DIR,
)
from rag import get_embeddings

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("ingest")


def load_documents() -> list[Document]:
    """Read every Markdown file in knowledge/ and tag it with its filename."""
    paths = sorted(KNOWLEDGE_DIR.glob("*.md"))
    if not paths:
        raise SystemExit(f"No markdown files found in {KNOWLEDGE_DIR}")

    documents = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        # The first heading makes a far better citation label than the raw filename.
        title = next(
            (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")),
            path.stem.replace("_", " ").title(),
        )
        documents.append(
            Document(
                page_content=text,
                metadata={"source": path.name, "title": title},
            )
        )
        log.info("  loaded %-24s %5d chars", path.name, len(text))
    return documents


def main() -> None:
    log.info("Twin knowledge ingest")
    log.info("=" * 52)

    documents = load_documents()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    log.info("")
    log.info("Split %d documents into %d chunks (%d chars, %d overlap)",
             len(documents), len(chunks), CHUNK_SIZE, CHUNK_OVERLAP)

    embeddings, backend = get_embeddings()
    log.info("Embedding backend: %s", backend)

    # Rebuild from scratch so re-running ingest is idempotent rather than duplicating
    # chunks. We drop the *collection* through Chroma's own client rather than deleting
    # the directory: on Windows an editor or a still-running server can hold a handle on
    # chroma.sqlite3, and rmtree would fail where this succeeds.
    import chromadb

    if CHROMA_DIR.exists():
        try:
            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            client.delete_collection(COLLECTION_NAME)
            log.info("Cleared the previous '%s' collection", COLLECTION_NAME)
        except Exception as exc:  # noqa: BLE001 - a missing collection is the happy path
            log.info("No previous collection to clear (%s)", type(exc).__name__)

    from langchain_chroma import Chroma

    log.info("Embedding and persisting... (first run may download the local model)")
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )

    log.info("")
    log.info("Done. %d chunks persisted to %s", len(chunks), CHROMA_DIR)

    # Smoke-test the retriever so a broken store is caught here, not during the demo.
    from rag import retrieve

    probe = "How much should I keep in my emergency fund?"
    hits = retrieve(probe)
    log.info("")
    log.info("Smoke test: %r", probe)
    for hit in hits:
        log.info("  %.3f  %s", hit["score"], hit["source"])
    if not hits:
        log.error("Retrieval returned nothing - the store did not persist correctly.")
        sys.exit(1)


if __name__ == "__main__":
    main()

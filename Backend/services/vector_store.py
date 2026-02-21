"""Vector store - FAISS for semantic search over metadata."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Lazy imports to avoid heavy deps at startup
_faiss = None
_sentence_transformers = None


def _get_embedding_model():
    global _sentence_transformers
    if _sentence_transformers is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_transformers = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning("SentenceTransformer not available: %s", e)
    return _sentence_transformers


def _get_faiss():
    global _faiss
    if _faiss is None:
        import faiss
        _faiss = faiss
    return _faiss


class VectorStore:
    """FAISS-based vector store for metadata embeddings."""

    def __init__(self, index_path: str | Path | None = None) -> None:
        self._index_path = Path(index_path or "data/faiss_index")
        self._index_path.mkdir(parents=True, exist_ok=True)
        self._index = None
        self._id_to_doc: list[dict[str, Any]] = []
        self._model = _get_embedding_model()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        if not self._model:
            # Try to initialize again just in case (e.g. if it failed once on connection issue)
            self._model = _get_embedding_model()
            if not self._model:
                logger.warning("Embedding model still not available. Using dummy embeddings.")
                return [[0.0] * 384 for _ in texts] # Fallback to dummy 384-dim vector

        try:
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return [[0.0] * 384 for _ in texts]

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        """Add documents with 'content' field for embedding."""
        if not documents or not self._model:
            return
        contents = [d.get("content", str(d)) for d in documents]
        vectors = self._embed_batch(contents)
        faiss_mod = _get_faiss()
        import numpy as np
        vectors_np = np.array(vectors, dtype="float32")
        dim = vectors_np.shape[1]
        if self._index is None:
            self._index = faiss_mod.IndexFlatL2(dim)
        self._index.add(vectors_np)
        self._id_to_doc.extend(documents)

    def _embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed in batches."""
        all_embs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embs = self.embed(batch)
            all_embs.extend(embs)
        return all_embs

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search for relevant documents."""
        if self._model is None or self._index is None or not self._id_to_doc:
            return []
        qvec = self.embed([query])[0]
        import numpy as np
        q = np.array([qvec], dtype="float32")
        D, I = self._index.search(q, min(top_k, len(self._id_to_doc)))
        results = []
        for idx in I[0]:
            if 0 <= idx < len(self._id_to_doc):
                doc = dict(self._id_to_doc[idx])
                results.append(doc)
        return results

    def clear(self) -> None:
        """Clear index."""
        self._index = None
        self._id_to_doc = []

    def save(self) -> None:
        """Persist index to disk."""
        if self._index is None:
            return
        faiss_mod = _get_faiss()
        faiss_mod.write_index(self._index, str(self._index_path / "index.faiss"))
        meta_path = self._index_path / "meta.json"
        meta_path.write_text(json.dumps(self._id_to_doc, indent=2, default=str))

    def load(self) -> bool:
        """Load index from disk."""
        idx_file = self._index_path / "index.faiss"
        meta_file = self._index_path / "meta.json"
        if not idx_file.exists() or not meta_file.exists():
            return False
        try:
            self._index = _get_faiss().read_index(str(idx_file))
            self._id_to_doc = json.loads(meta_file.read_text())
            return True
        except Exception as e:
            logger.warning("Failed to load FAISS index: %s", e)
            return False


# Global store instance
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get or create global vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        _vector_store.load()
    return _vector_store

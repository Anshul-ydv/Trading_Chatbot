from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List

import numpy as np

try:  # pragma: no cover - optional heavy dependency
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError:  # pragma: no cover
    SentenceTransformer = None

from .config import Settings, get_settings
from .utils import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class Document:
    text: str
    source: str


class _EmbeddingBackend:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = None
        if SentenceTransformer:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed loading SentenceTransformer %s: %s", model_name, exc)

    def encode(self, texts: List[str]) -> np.ndarray:
        if self.model:
            return np.array(self.model.encode(texts, show_progress_bar=False))
        return self._tfidf(texts)

    def _tfidf(self, texts: List[str]) -> np.ndarray:
        vocab: dict[str, int] = {}
        rows: List[np.ndarray] = []
        for text in texts:
            tokens = [token.lower() for token in text.split()]
            vector = np.zeros(len(vocab) or 1)
            for token in tokens:
                if token not in vocab:
                    vocab[token] = len(vocab)
                    vector = np.pad(vector, (0, 1))
                vector[vocab[token]] += 1
            rows.append(vector)
        max_len = max(len(row) for row in rows)
        normalized = []
        for row in rows:
            if len(row) < max_len:
                row = np.pad(row, (0, max_len - len(row)))
            norm = np.linalg.norm(row) or 1
            normalized.append(row / norm)
        return np.vstack(normalized)


class LocalRAGIndex:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.backend = _EmbeddingBackend(self.settings.embeddings_model)
        self.documents: List[Document] = []
        self.embeddings: np.ndarray | None = None
        self._load_if_available()

    def add_documents(self, docs: Iterable[Document]) -> None:
        self.documents.extend(docs)
        self._recompute_embeddings()
        self._persist()

    def query(self, text: str, top_k: int = 3) -> List[Document]:
        if not self.documents:
            return []
        query_vec = self.backend.encode([text])[0]
        if self.embeddings is None:
            self._recompute_embeddings()
        assert self.embeddings is not None
        sims = self.embeddings @ query_vec / (np.linalg.norm(query_vec) or 1)
        idx = np.argsort(sims)[::-1][:top_k]
        return [self.documents[i] for i in idx if sims[i] > 0.1]

    def _recompute_embeddings(self) -> None:
        if not self.documents:
            self.embeddings = None
            return
        texts = [doc.text for doc in self.documents]
        self.embeddings = self.backend.encode(texts)

    def _persist(self) -> None:
        payload = {
            "documents": [asdict(doc) for doc in self.documents],
            "embeddings": self.embeddings.tolist() if self.embeddings is not None else None,
        }
        Path(self.settings.rag_store).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_if_available(self) -> None:
        store = Path(self.settings.rag_store)
        if not store.exists():
            return
        payload = json.loads(store.read_text(encoding="utf-8"))
        self.documents = [Document(**doc) for doc in payload.get("documents", [])]
        emb = payload.get("embeddings")
        if emb:
            self.embeddings = np.array(emb)
        else:
            self.embeddings = None


def bootstrap_default_corpus(index: LocalRAGIndex) -> None:
    if index.documents:
        return
    default_docs = [
        Document(
            text="Breakout strategy prefers strong volume expansion and positive RSI divergence.",
            source="strategies.md",
        ),
        Document(
            text="Keep leverage low (<1x) and focus on ROE>18% for swing trades.",
            source="fa_guidelines.md",
        ),
    ]
    index.add_documents(default_docs)

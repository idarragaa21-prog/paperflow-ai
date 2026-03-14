from __future__ import annotations

import asyncio
import hashlib
import math
from collections import Counter
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logger import logger
from app.models.document import PaperChunk
from app.models.paper import Paper

HASH_EMBED_DIM = 64


def _hash_embed(text: str, *, dims: int = HASH_EMBED_DIM) -> list[float]:
    tokens = [token.lower() for token in text.split() if token.strip()]
    counts = Counter(tokens)
    vector = [0.0] * dims
    for token, count in counts.items():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = digest[0] % dims
        sign = 1.0 if digest[1] % 2 == 0 else -1.0
        vector[bucket] += count * sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in text.split() if len(token.strip()) > 2]


def _lexical_score(*, query_terms: set[str], text: str) -> float:
    lowered = text.lower()
    overlap = sum(lowered.count(term) for term in query_terms)
    if overlap <= 0:
        return 0.0
    phrase_bonus = 0.25 if " ".join(sorted(query_terms)).strip() and " ".join(sorted(query_terms)) in lowered else 0.0
    return float(overlap) + phrase_bonus


def _reciprocal_rank_fusion(rankings: list[list[dict[str, Any]]], *, k: int = 60) -> dict[str, dict[str, Any]]:
    fused: dict[str, dict[str, Any]] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            key = str(item["paper_chunk_id"])
            current = fused.setdefault(
                key,
                {
                    **item,
                    "retrieval_trace": {"dense_rank": None, "lexical_rank": None, "dense_score": 0.0, "lexical_score": 0.0},
                    "fused_score": 0.0,
                },
            )
            current["fused_score"] += 1.0 / (k + rank)
            if item.get("retrieval_source") == "dense":
                current["retrieval_trace"]["dense_rank"] = rank
                current["retrieval_trace"]["dense_score"] = float(item.get("score") or 0.0)
            if item.get("retrieval_source") == "lexical":
                current["retrieval_trace"]["lexical_rank"] = rank
                current["retrieval_trace"]["lexical_score"] = float(item.get("score") or 0.0)
    return fused


class VectorIndex:
    def __init__(self) -> None:
        self.collection_name = f"{settings.QDRANT_COLLECTION_PREFIX}_paper_chunks"
        self._client = None
        self._embed_dim: int | None = None
        self._embedding_strategy: tuple[str, str] | None = None
        self._embedding_warning_emitted = False

    @staticmethod
    def _qdrant_modules():
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qm

        return QdrantClient, qm

    def _client_or_none(self):
        if self._client is not None:
            return self._client
        try:
            QdrantClient, _qm = self._qdrant_modules()
            self._client = QdrantClient(url=settings.QDRANT_URL, timeout=3.0)
            self._client.get_collections()
            return self._client
        except Exception as exc:
            logger.warning(f"Qdrant unavailable, using DB fallback: {exc}")
            self._client = None
            return None

    @staticmethod
    def _extract_embeddings(payload: dict[str, Any]) -> list[list[float]]:
        embeddings = payload.get("embeddings") or []
        if embeddings and isinstance(embeddings[0], list):
            return [[float(value) for value in vector] for vector in embeddings if isinstance(vector, list) and vector]

        vector = payload.get("embedding")
        if isinstance(vector, list) and vector and not isinstance(vector[0], list):
            return [[float(value) for value in vector]]
        if isinstance(vector, list) and vector and isinstance(vector[0], list):
            return [[float(value) for value in nested] for nested in vector if isinstance(nested, list) and nested]
        return []

    @staticmethod
    def _embedding_attempts(text_or_texts: str | list[str], *, model: str) -> list[tuple[str, dict[str, Any]]]:
        attempts = [("/api/embed", {"model": model, "input": text_or_texts})]
        if isinstance(text_or_texts, str):
            attempts.append(("/api/embeddings", {"model": model, "prompt": text_or_texts}))
        return attempts

    def _candidate_embedding_models(self) -> list[str]:
        candidates = [settings.PAPERFLOW_EMBEDDING_MODEL, settings.PAPERFLOW_CHAT_MODEL]
        unique: list[str] = []
        for model in candidates:
            if model and model not in unique:
                unique.append(model)
        return unique

    def _emit_embedding_warning(self, message: str) -> None:
        if self._embedding_warning_emitted:
            return
        logger.warning(message)
        self._embedding_warning_emitted = True

    @staticmethod
    def _collection_vector_size(collection_info: Any) -> int | None:
        vectors = getattr(getattr(getattr(collection_info, "config", None), "params", None), "vectors", None)
        if vectors is None:
            return None
        size = getattr(vectors, "size", None)
        return int(size) if isinstance(size, int) else None

    def _recreate_collection(self, *, dims: int, qm) -> None:
        client = self._client_or_none()
        if client is None:
            return
        client.delete_collection(collection_name=self.collection_name)
        client.create_collection(
            collection_name=self.collection_name,
            vectors_config=qm.VectorParams(size=dims, distance=qm.Distance.COSINE),
        )
        logger.warning(
            f"Recreated Qdrant collection '{self.collection_name}' with vector size {dims} to match the active embedding model"
        )

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        attempts: list[tuple[str, str, dict[str, Any]]] = []

        payload_input: str | list[str] = texts[0] if len(texts) == 1 else texts
        if self._embedding_strategy is not None:
            endpoint, model = self._embedding_strategy
            if len(texts) > 1 and endpoint != "/api/embed":
                attempts.append(("/api/embed", model, {"model": model, "input": payload_input}))
            if endpoint == "/api/embed" or len(texts) == 1:
                attempts.append(
                    (
                        endpoint,
                        model,
                        {"model": model, "input": payload_input}
                        if endpoint == "/api/embed"
                        else {"model": model, "prompt": texts[0]},
                    )
                )
        else:
            for model in self._candidate_embedding_models():
                for endpoint, payload in self._embedding_attempts(payload_input, model=model):
                    attempts.append((endpoint, model, payload))

        errors: list[str] = []
        for endpoint, model, payload in attempts:
            try:
                response = httpx.post(
                    f"{base_url}{endpoint}",
                    json=payload,
                    timeout=settings.PAPERFLOW_EMBEDDING_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                payload_json = response.json()
                vectors = self._extract_embeddings(payload_json)
                if vectors and len(vectors) == len(texts):
                    self._embed_dim = len(vectors[0])
                    self._embedding_strategy = (endpoint, model)
                    if model != settings.PAPERFLOW_EMBEDDING_MODEL:
                        self._emit_embedding_warning(
                            f"Configured embedding model '{settings.PAPERFLOW_EMBEDDING_MODEL}' unavailable in Ollama; using '{model}' via {endpoint}"
                        )
                    elif endpoint != "/api/embed":
                        self._emit_embedding_warning(
                            f"Ollama /api/embed unavailable; using legacy embeddings endpoint {endpoint} for model '{model}'"
                        )
                    return vectors
            except Exception as exc:
                errors.append(f"{model}@{endpoint}: {exc}")

        if len(texts) > 1:
            return [self._embed_text(text) for text in texts]
        if errors:
            self._emit_embedding_warning(
                "Ollama embeddings unavailable, using hashed embeddings: " + " | ".join(errors[:4])
            )
        vector = _hash_embed(texts[0])
        self._embed_dim = len(vector)
        return [vector]

    def _embed_text(self, text: str) -> list[float]:
        return self._embed_texts([text])[0]

    def _ensure_collection(self) -> None:
        client = self._client_or_none()
        if client is None:
            return
        _QdrantClient, qm = self._qdrant_modules()
        dims = self._embed_dim or len(_hash_embed("paperflow"))
        try:
            existing = {item.name for item in client.get_collections().collections}
            if self.collection_name not in existing:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qm.VectorParams(size=dims, distance=qm.Distance.COSINE),
                )
                return
            collection_info = client.get_collection(self.collection_name)
            current_dims = self._collection_vector_size(collection_info)
            if current_dims is not None and current_dims != dims:
                self._recreate_collection(dims=dims, qm=qm)
        except Exception as exc:
            logger.warning(f"Failed to ensure Qdrant collection: {exc}")

    async def index_paper(self, db: AsyncSession, *, paper_id: UUID) -> None:
        client = self._client_or_none()
        if client is None:
            return

        paper = await db.get(Paper, paper_id)
        if not paper:
            return
        chunks_q = await db.execute(select(PaperChunk).where(PaperChunk.paper_id == paper_id).order_by(PaperChunk.page_number, PaperChunk.chunk_index))
        chunks = chunks_q.scalars().all()
        if not chunks:
            return

        _QdrantClient, qm = self._qdrant_modules()
        points: list[qm.PointStruct] = []
        batch_size = max(1, int(settings.PAPERFLOW_EMBED_BATCH_SIZE))
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start : batch_start + batch_size]
            vectors = await asyncio.to_thread(self._embed_texts, [chunk.text for chunk in batch])
            for chunk, vector in zip(batch, vectors, strict=True):
                points.append(
                    qm.PointStruct(
                        id=str(chunk.id),
                        vector=vector,
                        payload={
                            "chunk_id": str(chunk.id),
                            "paper_id": str(chunk.paper_id),
                            "project_id": str(paper.project_id),
                            "page_number": chunk.page_number,
                            "locator": chunk.locator,
                            "text": chunk.text[:1500],
                            "source_type": chunk.source_type,
                        },
                    )
                )
        self._ensure_collection()
        try:
            await asyncio.to_thread(client.upsert, collection_name=self.collection_name, points=points, wait=False)
        except Exception as exc:
            logger.warning(f"Failed to upsert chunk vectors: {exc}")

    async def _dense_retrieve(
        self,
        *,
        query: str,
        project_id: UUID,
        paper_id: UUID | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        client = self._client_or_none()
        if client is None:
            return []
        try:
            _QdrantClient, qm = self._qdrant_modules()
            filters = [qm.FieldCondition(key="project_id", match=qm.MatchValue(value=str(project_id)))]
            if paper_id is not None:
                filters.append(qm.FieldCondition(key="paper_id", match=qm.MatchValue(value=str(paper_id))))
            query_vector = await asyncio.to_thread(self._embed_text, query)
            self._ensure_collection()
            hits = await asyncio.to_thread(
                client.search,
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=qm.Filter(must=filters),
            )
            return [
                {
                    "paper_id": UUID(hit.payload["paper_id"]),
                    "paper_chunk_id": UUID(hit.payload["chunk_id"]),
                    "page_number": hit.payload.get("page_number"),
                    "locator": hit.payload.get("locator"),
                    "quoted_text": hit.payload.get("text", ""),
                    "score": float(hit.score),
                    "retrieval_source": "dense",
                }
                for hit in hits
            ]
        except Exception as exc:
            logger.warning(f"Qdrant search failed, falling back to lexical-only retrieval: {exc}")
            return []

    async def _lexical_retrieve(
        self,
        db: AsyncSession,
        *,
        query: str,
        project_id: UUID,
        paper_id: UUID | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        query_terms = set(_tokenize(query))
        if not query_terms:
            return []

        stmt = select(PaperChunk, Paper.project_id).join(Paper, Paper.id == PaperChunk.paper_id).where(Paper.project_id == project_id)
        if paper_id is not None:
            stmt = stmt.where(PaperChunk.paper_id == paper_id)
        limited_terms = sorted(query_terms)[:6]
        if limited_terms:
            stmt = stmt.where(or_(*[PaperChunk.text.ilike(f"%{term}%") for term in limited_terms]))
        rows = await db.execute(stmt)
        ranked: list[dict[str, Any]] = []
        for chunk, _project_id in rows.all():
            score = _lexical_score(query_terms=query_terms, text=chunk.text)
            if score <= 0:
                continue
            ranked.append(
                {
                    "paper_id": chunk.paper_id,
                    "paper_chunk_id": chunk.id,
                    "page_number": chunk.page_number,
                    "locator": chunk.locator,
                    "quoted_text": chunk.text[:1500],
                    "score": score,
                    "retrieval_source": "lexical",
                }
            )
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:limit]

    async def retrieve(
        self,
        db: AsyncSession,
        *,
        query: str,
        project_id: UUID,
        paper_id: UUID | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        dense = await self._dense_retrieve(query=query, project_id=project_id, paper_id=paper_id, limit=limit * 3)
        lexical = await self._lexical_retrieve(db, query=query, project_id=project_id, paper_id=paper_id, limit=limit * 3)

        fused = list(_reciprocal_rank_fusion([dense, lexical]).values())
        query_terms = set(_tokenize(query))
        for item in fused:
            rerank = _lexical_score(query_terms=query_terms, text=str(item.get("quoted_text") or ""))
            item["rerank_score"] = rerank
            item["final_score"] = item["fused_score"] + (0.2 * rerank)

        fused.sort(key=lambda item: (item["final_score"], item["retrieval_trace"]["dense_score"], item["retrieval_trace"]["lexical_score"]), reverse=True)
        results = fused[:limit]
        for rank, item in enumerate(results, start=1):
            item["rank"] = rank
        return results


vector_index = VectorIndex()

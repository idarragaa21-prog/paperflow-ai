from __future__ import annotations

import hashlib
import math
from collections import Counter
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
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
    phrase_bonus = (
        0.25
        if " ".join(sorted(query_terms)).strip()
        and " ".join(sorted(query_terms)) in lowered
        else 0.0
    )
    return float(overlap) + phrase_bonus


def _reciprocal_rank_fusion(
    rankings: list[list[dict[str, Any]]], *, k: int = 60
) -> dict[str, dict[str, Any]]:
    fused: dict[str, dict[str, Any]] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            key = str(item["paper_chunk_id"])
            current = fused.setdefault(
                key,
                {
                    **item,
                    "retrieval_trace": {
                        "dense_rank": None,
                        "lexical_rank": None,
                        "dense_score": 0.0,
                        "lexical_score": 0.0,
                    },
                    "fused_score": 0.0,
                },
            )
            current["fused_score"] += 1.0 / (k + rank)
            if item.get("retrieval_source") == "dense":
                current["retrieval_trace"]["dense_rank"] = rank
                current["retrieval_trace"]["dense_score"] = float(
                    item.get("score") or 0.0
                )
            if item.get("retrieval_source") == "lexical":
                current["retrieval_trace"]["lexical_rank"] = rank
                current["retrieval_trace"]["lexical_score"] = float(
                    item.get("score") or 0.0
                )
    return fused


class VectorIndex:
    def __init__(self) -> None:
        self.collection_name = f"{settings.QDRANT_COLLECTION_PREFIX}_paper_chunks"
        self._client = None
        self._embed_dim: int | None = None

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

    def _embed_text(self, text: str) -> list[float]:
        try:
            response = httpx.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embed",
                json={"model": settings.PAPERFLOW_EMBEDDING_MODEL, "input": text},
                timeout=10.0,
            )
            response.raise_for_status()
            payload = response.json()
            embeddings = payload.get("embeddings") or []
            if embeddings and isinstance(embeddings[0], list):
                vector = embeddings[0]
            else:
                vector = payload.get("embedding")
            if isinstance(vector, list) and vector:
                self._embed_dim = len(vector)
                return [float(value) for value in vector]
        except Exception as exc:
            logger.debug(f"Ollama /api/embed unavailable: {exc}")
        for model in [
            settings.PAPERFLOW_EMBEDDING_MODEL,
            settings.PAPERFLOW_CHAT_MODEL,
        ]:
            try:
                response = httpx.post(
                    f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings",
                    json={"model": model, "prompt": text},
                    timeout=10.0,
                )
                response.raise_for_status()
                payload = response.json()
                vector = payload.get("embedding")
                if isinstance(vector, list) and vector:
                    self._embed_dim = len(vector)
                    return [float(value) for value in vector]
            except Exception as exc:
                logger.debug(f"Ollama embeddings unavailable for model {model}: {exc}")
        vector = _hash_embed(text)
        self._embed_dim = len(vector)
        return vector

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = httpx.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embed",
                json={"model": settings.PAPERFLOW_EMBEDDING_MODEL, "input": texts},
                timeout=10.0,
            )
            response.raise_for_status()
            payload = response.json()
            embeddings = payload.get("embeddings") or []
            if embeddings and isinstance(embeddings[0], list):
                self._embed_dim = len(embeddings[0])
                return [[float(value) for value in vector] for vector in embeddings]
        except Exception as exc:
            logger.debug(
                f"Ollama batch embeddings unavailable, using per-text fallback: {exc}"
            )
        return [self._embed_text(text) for text in texts]

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
                    vectors_config=qm.VectorParams(
                        size=dims, distance=qm.Distance.COSINE
                    ),
                )
                return
            collection = client.get_collection(self.collection_name)
            existing_size = getattr(
                getattr(getattr(collection, "config", None), "params", None),
                "vectors",
                None,
            )
            size = getattr(existing_size, "size", None)
            if isinstance(size, int) and size != dims:
                client.delete_collection(self.collection_name)
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qm.VectorParams(
                        size=dims, distance=qm.Distance.COSINE
                    ),
                )
        except Exception as exc:
            logger.warning(f"Failed to ensure Qdrant collection: {exc}")

    async def index_paper(self, db: AsyncSession, *, paper_id: UUID) -> None:
        client = self._client_or_none()
        if client is None:
            return

        paper = await db.get(Paper, paper_id)
        if not paper:
            return
        chunks_q = await db.execute(
            select(PaperChunk)
            .where(PaperChunk.paper_id == paper_id)
            .order_by(PaperChunk.page_number, PaperChunk.chunk_index)
        )
        chunks = chunks_q.scalars().all()
        if not chunks:
            return

        _QdrantClient, qm = self._qdrant_modules()
        points: list[qm.PointStruct] = []

        # ⚡ Bolt: Fix N+1 embedding bottleneck by replacing sequential API calls
        # with a single batch request, reducing latency from O(n) to O(1) requests
        vectors = self._embed_texts([chunk.text for chunk in chunks])

        for chunk, vector in zip(chunks, vectors):
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
            client.upsert(
                collection_name=self.collection_name, points=points, wait=False
            )
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

        _QdrantClient, qm = self._qdrant_modules()
        self._ensure_collection()
        try:
            filters = [
                qm.FieldCondition(
                    key="project_id", match=qm.MatchValue(value=str(project_id))
                )
            ]
            if paper_id is not None:
                filters.append(
                    qm.FieldCondition(
                        key="paper_id", match=qm.MatchValue(value=str(paper_id))
                    )
                )
            hits = client.search(
                collection_name=self.collection_name,
                query_vector=self._embed_text(query),
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
            logger.warning(
                f"Qdrant search failed, falling back to lexical-only retrieval: {exc}"
            )
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

        stmt = (
            select(PaperChunk, Paper.project_id)
            .join(Paper, Paper.id == PaperChunk.paper_id)
            .where(Paper.project_id == project_id)
        )
        if paper_id is not None:
            stmt = stmt.where(PaperChunk.paper_id == paper_id)
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
        dense = await self._dense_retrieve(
            query=query, project_id=project_id, paper_id=paper_id, limit=limit * 3
        )
        lexical = await self._lexical_retrieve(
            db, query=query, project_id=project_id, paper_id=paper_id, limit=limit * 3
        )

        fused = list(_reciprocal_rank_fusion([dense, lexical]).values())
        query_terms = set(_tokenize(query))
        for item in fused:
            rerank = _lexical_score(
                query_terms=query_terms, text=str(item.get("quoted_text") or "")
            )
            item["rerank_score"] = rerank
            item["final_score"] = item["fused_score"] + (0.2 * rerank)

        fused.sort(
            key=lambda item: (
                item["final_score"],
                item["retrieval_trace"]["dense_score"],
                item["retrieval_trace"]["lexical_score"],
            ),
            reverse=True,
        )
        results = fused[:limit]
        for rank, item in enumerate(results, start=1):
            item["rank"] = rank
        return results


vector_index = VectorIndex()

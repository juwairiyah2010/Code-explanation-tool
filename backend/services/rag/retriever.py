"""Vector similarity retrieval service using NumPy and SQLite."""

import json
import numpy as np
from sqlalchemy.orm import Session

from backend.core.logging import logger
from backend.repositories.rag_repo import RAGRepository
from backend.schemas.rag import RAGRetrievalResponse, RAGSourceCitation
from backend.services.rag.embeddings import BaseEmbeddingService, get_embedding_service


class RAGRetriever:
    """Semantic vector search over SQLite knowledge chunks using cosine similarity."""

    def __init__(
        self,
        db: Session,
        embedding_service: BaseEmbeddingService | None = None,
        default_threshold: float = 0.35,
    ):
        self.db = db
        self.repo = RAGRepository(db)
        self.embedding_service = embedding_service or get_embedding_service()
        self.default_threshold = default_threshold

    def retrieve(
        self,
        query: str,
        language: str = "auto",
        top_k: int = 3,
        similarity_threshold: float | None = None,
    ) -> RAGRetrievalResponse:
        """Search knowledge base for chunks most relevant to query."""
        threshold = similarity_threshold if similarity_threshold is not None else self.default_threshold

        clean_query = query.strip()
        if not clean_query:
            return RAGRetrievalResponse(
                query=query,
                results=[],
                insufficient_context=True,
                total_candidates=0,
            )

        # 1. Fetch candidate chunks from SQLite (filtered by language/general)
        candidates = self.repo.get_candidate_chunks(language=language)
        if not candidates:
            # Fallback to all chunks if language-specific query returned 0 candidates
            candidates = self.repo.get_candidate_chunks(language=None)

        if not candidates:
            logger.warning("RAG retriever: No candidate chunks in database.")
            return RAGRetrievalResponse(
                query=query,
                results=[],
                insufficient_context=True,
                total_candidates=0,
            )

        try:
            # 2. Embed the query string
            query_embedding = np.array(
                self.embedding_service.embed_text(clean_query), dtype=np.float32
            )
            query_norm = np.linalg.norm(query_embedding)
            if query_norm == 0:
                query_norm = 1.0
            query_embedding = query_embedding / query_norm

            # 3. Stack candidate chunk embeddings
            chunk_vectors = []
            valid_candidates = []
            for c in candidates:
                try:
                    vec = np.array(json.loads(c.embedding), dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    chunk_vectors.append(vec)
                    valid_candidates.append(c)
                except Exception as parse_err:
                    logger.warning(f"Error parsing embedding for chunk {c.chunk_id}: {parse_err}")

            if not valid_candidates:
                return RAGRetrievalResponse(
                    query=query,
                    results=[],
                    insufficient_context=True,
                    total_candidates=0,
                )

            matrix = np.vstack(chunk_vectors)  # Shape: (N, D)

            # 4. Dot product with normalized vectors gives cosine similarity
            similarities = np.dot(matrix, query_embedding)

            # 5. Filter and rank
            ranked_indices = np.argsort(similarities)[::-1]

            results = []
            for idx in ranked_indices:
                score = float(similarities[idx])
                if score < threshold:
                    break
                candidate = valid_candidates[idx]

                # Create concise snippet
                snippet = candidate.content.strip()
                if len(snippet) > 280:
                    snippet = snippet[:280] + "..."

                results.append(
                    RAGSourceCitation(
                        source=candidate.source,
                        title=candidate.title,
                        chunk_id=candidate.chunk_id,
                        similarity_score=round(score, 4),
                        snippet=snippet,
                        language=candidate.language,
                        topic=candidate.topic,
                    )
                )

                if len(results) >= top_k:
                    break

            insufficient = len(results) == 0
            return RAGRetrievalResponse(
                query=query,
                results=results,
                insufficient_context=insufficient,
                total_candidates=len(valid_candidates),
            )

        except Exception as e:
            logger.error(f"Error during RAG vector retrieval: {e}")
            return RAGRetrievalResponse(
                query=query,
                results=[],
                insufficient_context=True,
                total_candidates=len(candidates),
            )

"""Vector similarity and hybrid keyword retrieval service using NumPy, BM25, and SQLite."""

import json
import math
import re
from typing import Any
import numpy as np
from sqlalchemy.orm import Session

from backend.core.logging import logger
from backend.models.persistence import KnowledgeChunk
from backend.repositories.rag_repo import RAGRepository
from backend.schemas.rag import RAGRetrievalResponse, RAGSourceCitation
from backend.services.rag.embeddings import BaseEmbeddingService, get_embedding_service


class BM25Scorer:
    """Offline BM25 keyword relevance calculator for sparse retrieval."""

    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        self.doc_lens = [len(doc) for doc in self.tokenized_corpus]
        self.avg_doc_len = sum(self.doc_lens) / (self.corpus_size or 1.0)
        self.doc_freqs: dict[str, int] = {}
        for doc in self.tokenized_corpus:
            for term in set(doc):
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [t.lower() for t in re.findall(r"[a-zA-Z0-9_]+", text)]

    def score(self, query: str) -> list[float]:
        query_terms = self._tokenize(query)
        scores = [0.0] * self.corpus_size
        if not query_terms or self.corpus_size == 0:
            return scores

        for term in query_terms:
            if term not in self.doc_freqs:
                continue
            df = self.doc_freqs[term]
            # Robertson-Jones IDF
            idf = math.log((self.corpus_size - df + 0.5) / (df + 0.5) + 1.0)

            for i, doc in enumerate(self.tokenized_corpus):
                tf = doc.count(term)
                if tf > 0:
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (self.doc_lens[i] / (self.avg_doc_len or 1.0)))
                    scores[i] += idf * (numerator / denominator)

        max_score = max(scores) if scores else 0.0
        if max_score > 0:
            return [s / max_score for s in scores]
        return scores


class RAGRetriever:
    """Hybrid semantic vector and keyword search over SQLite knowledge chunks."""

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
        min_relevance_threshold: float | None = None,
        hybrid: bool = True,
        alpha: float = 0.65,
        max_context_chars: int = 3500,
    ) -> RAGRetrievalResponse:
        """Search knowledge base for chunks most relevant to query using hybrid scoring."""
        threshold = (
            min_relevance_threshold
            if min_relevance_threshold is not None
            else (similarity_threshold if similarity_threshold is not None else self.default_threshold)
        )

        clean_query = query.strip()
        if not clean_query:
            return RAGRetrievalResponse(
                query=query,
                results=[],
                insufficient_context=True,
                total_candidates=0,
                formatted_context="",
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
                formatted_context="",
            )

        try:
            # 2. Semantic Dense Vector Retrieval
            query_embedding = np.array(
                self.embedding_service.embed_text(clean_query), dtype=np.float32
            )
            query_norm = np.linalg.norm(query_embedding)
            if query_norm == 0:
                query_norm = 1.0
            query_embedding = query_embedding / query_norm

            chunk_vectors = []
            valid_candidates: list[KnowledgeChunk] = []
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
                    formatted_context="",
                )

            matrix = np.vstack(chunk_vectors)  # Shape: (N, D)
            semantic_scores = np.dot(matrix, query_embedding)

            # 3. Keyword Sparse Retrieval (BM25)
            if hybrid:
                corpus_texts = [f"{c.title} {c.section or ''} {c.content}" for c in valid_candidates]
                bm25_scorer = BM25Scorer(corpus_texts)
                keyword_scores = bm25_scorer.score(clean_query)
            else:
                keyword_scores = [0.0] * len(valid_candidates)

            # 4. Hybrid Ranking
            hybrid_scores = []
            for sem_s, kw_s in zip(semantic_scores, keyword_scores):
                if hybrid and max(keyword_scores) > 0:
                    combined = (alpha * float(sem_s)) + ((1.0 - alpha) * float(kw_s))
                else:
                    combined = float(sem_s)
                hybrid_scores.append(combined)

            ranked_indices = np.argsort(hybrid_scores)[::-1]

            # 5. Extract structured candidate list
            raw_results: list[dict[str, Any]] = []
            for idx in ranked_indices:
                score = float(hybrid_scores[idx])
                if score < threshold:
                    break
                cand = valid_candidates[idx]
                raw_results.append({
                    "chunk_id": cand.chunk_id,
                    "score": round(score, 4),
                    "source": cand.source,
                    "title": cand.title,
                    "section": getattr(cand, "section", "") or cand.title,
                    "text": cand.content.strip(),
                    "language": cand.language,
                    "topic": cand.topic,
                })

            # 6. Context Deduplication (remove near-identical chunks)
            deduped = self._deduplicate_chunks(raw_results, similarity_threshold=0.82)

            # 7. Convert to RAGSourceCitation
            citations: list[RAGSourceCitation] = []
            for item in deduped:
                snippet = item["text"][:280] + ("..." if len(item["text"]) > 280 else "")
                citations.append(
                    RAGSourceCitation(
                        chunk_id=item["chunk_id"],
                        score=item["score"],
                        similarity_score=item["score"],
                        source=item["source"],
                        title=item["title"],
                        section=item["section"],
                        text=item["text"],
                        snippet=snippet,
                        language=item["language"],
                        topic=item["topic"],
                    )
                )
                if len(citations) >= top_k:
                    break

            # 8. Context Size Control (character budget)
            budgeted_citations = self._apply_context_size_control(citations, max_chars=max_context_chars)

            # 9. Format prompt context for LLM
            formatted_context = self.build_llm_prompt_context(budgeted_citations)

            insufficient = len(budgeted_citations) == 0
            return RAGRetrievalResponse(
                query=query,
                results=budgeted_citations,
                insufficient_context=insufficient,
                total_candidates=len(valid_candidates),
                formatted_context=formatted_context,
            )

        except Exception as e:
            logger.error(f"Error during RAG hybrid retrieval: {e}")
            return RAGRetrievalResponse(
                query=query,
                results=[],
                insufficient_context=True,
                total_candidates=len(candidates),
                formatted_context="",
            )

    def _deduplicate_chunks(self, items: list[dict[str, Any]], similarity_threshold: float = 0.82) -> list[dict[str, Any]]:
        """Remove overlapping or near-duplicate chunks based on Jaccard word set similarity."""
        unique: list[dict[str, Any]] = []
        seen_token_sets: list[set[str]] = []

        for item in items:
            tokens = set(re.findall(r"\w+", item["text"].lower()))
            is_dup = False
            for existing in seen_token_sets:
                intersection = len(tokens & existing)
                union = len(tokens | existing)
                if union > 0 and (intersection / union) > similarity_threshold:
                    is_dup = True
                    break
            if not is_dup:
                seen_token_sets.append(tokens)
                unique.append(item)

        return unique

    def _apply_context_size_control(self, items: list[RAGSourceCitation], max_chars: int) -> list[RAGSourceCitation]:
        """Truncate candidate list cleanly at chunk boundaries to satisfy the character budget."""
        total_chars = 0
        budgeted = []
        for item in items:
            item_chars = len(item.text)
            if total_chars + item_chars <= max_chars or not budgeted:
                budgeted.append(item)
                total_chars += item_chars
            else:
                break
        return budgeted

    def build_llm_prompt_context(self, citations: list[RAGSourceCitation]) -> str:
        """Format retrieved, deduplicated citations into an attributed prompt block for the LLM."""
        if not citations:
            return ""

        context_blocks = [
            "=== RETRIEVED GROUND TRUTH DOCUMENTATION (USE FOR EXPLANATIONS) ===",
        ]
        for idx, c in enumerate(citations, 1):
            sec_header = f" | Section: {c.section}" if c.section else ""
            context_blocks.append(
                f"[{idx}] Source: {c.source} | Title: {c.title}{sec_header} (Relevance Score: {c.score:.2f})\n"
                f"{c.text.strip()}"
            )
        context_blocks.append("=== END OF DOCUMENTATION CONTEXT ===")
        return "\n\n".join(context_blocks)

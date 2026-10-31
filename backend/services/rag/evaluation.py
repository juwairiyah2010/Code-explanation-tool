"""Evaluation script measuring offline RAG retrieval quality against a curated benchmark dataset."""

import argparse
import time
from pathlib import Path
from typing import Any
from sqlalchemy.orm import Session

from backend.core.database import SessionLocal, init_db
from backend.repositories.rag_repo import RAGRepository
from backend.services.rag.ingestion import KnowledgeIngestionPipeline
from backend.services.rag.retriever import RAGRetriever

# Curated benchmark dataset of queries with ground-truth expected documents and keywords
BENCHMARK_DATASET = [
    {
        "id": "q1_python_generators",
        "query": "How do Python generators and the yield keyword optimize memory usage?",
        "language": "python",
        "expected_doc": "python_core",
        "expected_keywords": ["generator", "yield", "iterator", "lazy"],
    },
    {
        "id": "q2_python_legb_scope",
        "query": "What is the LEGB rule for variable resolution in Python?",
        "language": "python",
        "expected_doc": "python_core",
        "expected_keywords": ["legb", "scope", "local", "enclosing"],
    },
    {
        "id": "q3_python_mutable_defaults",
        "query": "Why should I avoid using a mutable default argument like def f(items=[])?",
        "language": "python",
        "expected_doc": "python_core",
        "expected_keywords": ["mutable", "default", "argument", "parameter"],
    },
    {
        "id": "q4_js_closures",
        "query": "How does a closure preserve outer lexical scope variables in JavaScript?",
        "language": "javascript",
        "expected_doc": "javascript_core",
        "expected_keywords": ["closure", "lexical", "scope", "function"],
    },
    {
        "id": "q5_js_event_loop",
        "query": "What is the difference between the microtask queue and macrotask queue in JavaScript?",
        "language": "javascript",
        "expected_doc": "javascript_core",
        "expected_keywords": ["event loop", "microtask", "promise", "macrotask"],
    },
    {
        "id": "q6_algo_complexity",
        "query": "What are Big-O time and space complexity classes and how are they ordered?",
        "language": "general",
        "expected_doc": "algorithms_and_complexity",
        "expected_keywords": ["big-o", "complexity", "asymptotic", "time"],
    },
    {
        "id": "q7_common_errors",
        "query": "What causes an IndexError or TypeError and how do you handle it?",
        "language": "general",
        "expected_doc": "common_errors",
        "expected_keywords": ["indexerror", "typeerror", "exception", "error"],
    },
]


from backend.services.rag.embeddings import BaseEmbeddingService


class RAGEvaluator:
    """Measures Hit@K, MRR, and latency across hybrid and semantic retrieval."""

    def __init__(self, db: Session, embedding_service: BaseEmbeddingService | None = None):
        self.db = db
        self.retriever = RAGRetriever(db, embedding_service=embedding_service)

    def evaluate(self, top_k: int = 3, hybrid: bool = True) -> dict[str, Any]:
        """Run evaluation benchmark across all queries."""
        start_time = time.time()
        hits_at_1 = 0
        hits_at_k = 0
        reciprocal_ranks = []
        details = []

        for item in BENCHMARK_DATASET:
            t0 = time.perf_counter()
            resp = self.retriever.retrieve(
                query=item["query"],
                language=item["language"],
                top_k=top_k,
                hybrid=hybrid,
                similarity_threshold=0.30,
            )
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            expected_doc = item["expected_doc"].lower()
            expected_kw = [k.lower() for k in item["expected_keywords"]]

            # Check ranking of relevant result
            rank = None
            matched_chunk = None

            for r_idx, res in enumerate(resp.results, start=1):
                chunk_id_lower = res.chunk_id.lower()
                title_lower = res.title.lower()
                text_lower = res.text.lower()

                doc_match = expected_doc in chunk_id_lower or expected_doc in title_lower
                kw_match = any(k in text_lower or k in title_lower for k in expected_kw)

                if doc_match or kw_match:
                    rank = r_idx
                    matched_chunk = res.chunk_id
                    break

            if rank == 1:
                hits_at_1 += 1
            if rank is not None and rank <= top_k:
                hits_at_k += 1
                reciprocal_ranks.append(1.0 / rank)
            else:
                reciprocal_ranks.append(0.0)

            details.append({
                "query_id": item["id"],
                "query": item["query"],
                "rank": rank,
                "hit": rank is not None and rank <= top_k,
                "matched_chunk": matched_chunk,
                "latency_ms": latency_ms,
                "candidates_retrieved": len(resp.results),
            })

        total_queries = len(BENCHMARK_DATASET)
        hit_at_1_rate = round(hits_at_1 / total_queries, 4) if total_queries else 0.0
        hit_at_k_rate = round(hits_at_k / total_queries, 4) if total_queries else 0.0
        mrr = round(sum(reciprocal_ranks) / total_queries, 4) if total_queries else 0.0
        avg_latency = round(sum(d["latency_ms"] for d in details) / total_queries, 2) if total_queries else 0.0

        return {
            "total_queries": total_queries,
            "top_k": top_k,
            "hybrid_enabled": hybrid,
            "hit_at_1": hit_at_1_rate,
            "hit_at_k": hit_at_k_rate,
            "mrr": mrr,
            "avg_latency_ms": avg_latency,
            "total_duration_s": round(time.time() - start_time, 3),
            "details": details,
        }


def run_evaluation_cli() -> dict[str, Any]:
    """CLI runner executing benchmark evaluation report."""
    parser = argparse.ArgumentParser(description="Evaluate Code Lore RAG Retrieval Quality")
    parser.add_argument("--top-k", type=int, default=3, help="Top-K evaluation cutoff")
    parser.add_argument("--no-hybrid", action="store_true", help="Disable BM25 hybrid ranking")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        repo = RAGRepository(db)
        stats = repo.get_stats()
        if stats["chunks"] == 0:
            print("Knowledge base is empty. Running ingestion first...")
            pipeline = KnowledgeIngestionPipeline(db)
            pipeline.ingest_directory(Path("data/knowledge_base"))

        evaluator = RAGEvaluator(db)
        results = evaluator.evaluate(top_k=args.top_k, hybrid=not args.no_hybrid)

        print("=" * 60)
        print(" CODE LORE RAG RETRIEVAL QUALITY EVALUATION REPORT")
        print("=" * 60)
        print(f"Total Benchmark Queries: {results['total_queries']}")
        print(f"Mode: {'Hybrid (Dense + BM25)' if results['hybrid_enabled'] else 'Dense Only'}")
        print(f"Top-K Cutoff:           {results['top_k']}")
        print(f"Hit@1 Rate:             {results['hit_at_1'] * 100:.1f}%")
        print(f"Hit@{results['top_k']} Rate:             {results['hit_at_k'] * 100:.1f}%")
        print(f"Mean Reciprocal Rank:   {results['mrr']:.4f}")
        print(f"Avg Retrieval Latency:  {results['avg_latency_ms']} ms")
        print("-" * 60)
        for d in results["details"]:
            status_icon = "✓" if d["hit"] else "✗"
            print(f"[{status_icon}] {d['query_id']} (Rank: {d['rank']}, Latency: {d['latency_ms']}ms)")
        print("=" * 60)
        return results
    finally:
        db.close()


if __name__ == "__main__":
    run_evaluation_cli()

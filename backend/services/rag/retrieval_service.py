"""RetrievalService dedicated to extracting contextual queries and retrieving offline RAG documentation."""

from sqlalchemy.orm import Session
from backend.core.logging import logger
from backend.schemas.explanation import CodeAnalysisResponse
from backend.schemas.rag import RAGRetrievalResponse
from backend.services.rag.retriever import RAGRetriever



class RetrievalService:
    """Service that coordinates hybrid semantic + keyword retrieval for code explanations."""

    def __init__(self, db: Session | None = None, retriever: RAGRetriever | None = None):
        self.db = db
        self.retriever = retriever or (RAGRetriever(db) if db is not None else None)

    def extract_search_query(self, code: str, ast_result: CodeAnalysisResponse | None = None) -> str:
        """Derive an optimal hybrid search query from code content and AST construct tokens."""
        query_parts: list[str] = []
        if ast_result:
            if hasattr(ast_result, "constructs") and ast_result.constructs:
                func_names = [f.name for f in ast_result.constructs.functions]
                class_names = [c.name for c in ast_result.constructs.classes]
                if func_names:
                    query_parts.append(f"functions: {', '.join(func_names)}")
                if class_names:
                    query_parts.append(f"classes: {', '.join(class_names)}")
                if ast_result.constructs.loops:
                    query_parts.append("loops iteration traversal")
                if ast_result.constructs.conditions:
                    query_parts.append("conditional branching")
            
            # Incorporate top static findings or rules
            if hasattr(ast_result, "findings") and ast_result.findings:
                rule_titles = [f.title for f in ast_result.findings[:2]]
                query_parts.append(" ".join(rule_titles))

        code_lines = [line.strip() for line in code.splitlines() if line.strip() and not line.strip().startswith(("#", "//"))]
        code_head = " ".join(code_lines[:3])
        return f"{' '.join(query_parts)} {code_head}".strip() or code[:200]

    def retrieve(
        self,
        code: str,
        language: str = "general",
        ast_result: CodeAnalysisResponse | None = None,
        top_k: int = 3,
        min_relevance_threshold: float = 0.35,
        hybrid: bool = True,
        alpha: float = 0.65,
        max_context_chars: int = 4000,
    ) -> RAGRetrievalResponse:
        """Retrieve relevant documentation chunks using hybrid dense + sparse search."""
        if not self.retriever:
            return RAGRetrievalResponse(
                query="",
                results=[],
                total_candidates=0,
                retrieval_mode="none",
                formatted_context="",
            )

        query = self.extract_search_query(code, ast_result=ast_result)
        res = self.retriever.retrieve(
            query=query,
            language=language,
            top_k=top_k,
            similarity_threshold=min_relevance_threshold,
            min_relevance_threshold=min_relevance_threshold,
            hybrid=hybrid,
            alpha=alpha,
            max_context_chars=max_context_chars,
        )
        logger.info(f"RetrievalService retrieved {len(res.results)} chunks for language '{language}'.")
        return res

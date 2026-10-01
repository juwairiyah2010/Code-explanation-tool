"""Repository for Knowledge Documents and Chunks in SQLite."""

import json
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func
from backend.models.persistence import KnowledgeDocument, KnowledgeChunk


class RAGRepository:
    """Handles CRUD persistence operations for RAG documents and chunks."""

    def __init__(self, db: Session):
        self.db = db

    def upsert_document(
        self,
        doc_id: str,
        title: str,
        source: str,
        language: str,
        topic: str,
    ) -> KnowledgeDocument:
        """Insert or update a knowledge base document header."""
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.doc_id == doc_id)
        doc = self.db.execute(stmt).scalars().first()

        if doc:
            doc.title = title
            doc.source = source
            doc.language = language
            doc.topic = topic
        else:
            doc = KnowledgeDocument(
                doc_id=doc_id,
                title=title,
                source=source,
                language=language,
                topic=topic,
            )
            self.db.add(doc)

        self.db.flush()
        return doc

    def save_chunk(
        self,
        document_id: int,
        chunk_id: str,
        title: str,
        source: str,
        language: str,
        topic: str,
        content: str,
        token_count: int,
        embedding: list[float],
    ) -> KnowledgeChunk:
        """Insert or replace a knowledge chunk with its embedding."""
        stmt = select(KnowledgeChunk).where(KnowledgeChunk.chunk_id == chunk_id)
        chunk = self.db.execute(stmt).scalars().first()

        embedding_json = json.dumps(embedding)

        if chunk:
            chunk.document_id = document_id
            chunk.title = title
            chunk.source = source
            chunk.language = language
            chunk.topic = topic
            chunk.content = content
            chunk.token_count = token_count
            chunk.embedding = embedding_json
        else:
            chunk = KnowledgeChunk(
                document_id=document_id,
                chunk_id=chunk_id,
                title=title,
                source=source,
                language=language,
                topic=topic,
                content=content,
                token_count=token_count,
                embedding=embedding_json,
            )
            self.db.add(chunk)

        self.db.flush()
        return chunk

    def get_candidate_chunks(
        self,
        language: str | None = None,
        topic: str | None = None,
    ) -> list[KnowledgeChunk]:
        """Fetch candidate chunks, optionally filtered by language or general programming concepts."""
        stmt = select(KnowledgeChunk)
        conditions = []

        if language and language not in ("auto", "unknown", "all"):
            # Include language-specific chunks AND general programming concepts
            conditions.append(KnowledgeChunk.language.in_([language.lower(), "general"]))

        if topic and topic != "all":
            conditions.append(KnowledgeChunk.topic == topic)

        if conditions:
            stmt = stmt.where(*conditions)

        return list(self.db.execute(stmt).scalars().all())

    def get_stats(self) -> dict[str, int]:
        """Return total document count and total chunk count."""
        doc_count = self.db.execute(select(func.count(KnowledgeDocument.id))).scalar_one() or 0
        chunk_count = self.db.execute(select(func.count(KnowledgeChunk.id))).scalar_one() or 0
        return {"documents": doc_count, "chunks": chunk_count}

    def clear_all(self) -> None:
        """Clear all knowledge documents and cascaded chunks."""
        self.db.execute(delete(KnowledgeDocument))
        self.db.commit()

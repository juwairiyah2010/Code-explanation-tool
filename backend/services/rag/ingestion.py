"""Ingestion pipeline for parsing, chunking, embedding, and storing knowledge documentation."""

import os
import re
import time
from pathlib import Path
from sqlalchemy.orm import Session

from backend.core.database import SessionLocal, init_db
from backend.core.logging import logger
from backend.repositories.rag_repo import RAGRepository
from backend.schemas.rag import RAGIngestResponse
from backend.services.rag.embeddings import BaseEmbeddingService, get_embedding_service


class KnowledgeIngestionPipeline:
    """Extracts, cleans, chunks, embeds, and stores documentation into SQLite."""

    def __init__(self, db: Session, embedding_service: BaseEmbeddingService | None = None):
        self.db = db
        self.repo = RAGRepository(db)
        self.embedding_service = embedding_service or get_embedding_service()

    def parse_markdown_document(self, file_path: Path) -> dict:
        """Parse markdown file with headers, extracting metadata and semantic sections."""
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()

        title = file_path.stem.replace("_", " ").title()
        source = "Internal Documentation"
        language = "general"
        topic = "programming"

        body_lines = []
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith("# "):
                title = line_strip[2:].strip()
            elif line_strip.lower().startswith("source:"):
                source = line_strip[7:].strip()
            elif line_strip.lower().startswith("language:"):
                language = line_strip[9:].strip().lower()
            elif line_strip.lower().startswith("topic:"):
                topic = line_strip[6:].strip().lower()
            else:
                body_lines.append(line)

        body_text = "\n".join(body_lines).strip()

        # Split into sections based on '## ' headers
        section_pattern = re.compile(r"(^##\s+.+$)", re.MULTILINE)
        parts = section_pattern.split(body_text)

        sections = []
        current_header = title

        # parts alternating between header and content
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            if not part:
                i += 1
                continue

            if part.startswith("## "):
                current_header = part[3:].strip()
                if i + 1 < len(parts):
                    content = parts[i + 1].strip()
                    i += 1
                else:
                    content = ""
            else:
                content = part

            if content:
                sections.append({"title": current_header, "content": content})
            i += 1

        return {
            "doc_id": file_path.stem,
            "title": title,
            "source": source,
            "language": language,
            "topic": topic,
            "sections": sections,
        }

    def chunk_section(self, section: dict, max_words: int = 300, overlap: int = 50) -> list[str]:
        """Split a long section into sliding window chunks if needed, or return single chunk."""
        content = section["content"]
        words = content.split()
        if len(words) <= max_words:
            return [content]

        chunks = []
        step = max_words - overlap
        for start_idx in range(0, len(words), step):
            chunk_words = words[start_idx : start_idx + max_words]
            chunks.append(" ".join(chunk_words))
            if start_idx + max_words >= len(words):
                break
        return chunks

    def ingest_directory(self, directory_path: Path) -> RAGIngestResponse:
        """Run ingestion pipeline on all .md files in the specified directory."""
        start_time = time.time()
        md_files = sorted(list(directory_path.glob("*.md")))

        if not md_files:
            return RAGIngestResponse(
                documents_ingested=0,
                chunks_created=0,
                duration_seconds=0.0,
                message=f"No markdown documents found in {directory_path}",
            )

        total_chunks = []
        parsed_docs = []

        for md_file in md_files:
            doc_data = self.parse_markdown_document(md_file)
            parsed_docs.append(doc_data)

            doc_record = self.repo.upsert_document(
                doc_id=doc_data["doc_id"],
                title=doc_data["title"],
                source=doc_data["source"],
                language=doc_data["language"],
                topic=doc_data["topic"],
            )

            for s_idx, sec in enumerate(doc_data["sections"]):
                sub_chunks = self.chunk_section(sec)
                for c_idx, chunk_text in enumerate(sub_chunks):
                    chunk_id = f"{doc_data['doc_id']}_s{s_idx + 1}_c{c_idx + 1}"
                    # Contextual chunk prefix to improve semantic embedding quality
                    embedding_text = f"Title: {sec['title']}\nLanguage: {doc_data['language']}\nTopic: {doc_data['topic']}\n\n{chunk_text}"
                    total_chunks.append({
                        "document_id": doc_record.id,
                        "chunk_id": chunk_id,
                        "title": sec["title"],
                        "source": doc_data["source"],
                        "language": doc_data["language"],
                        "topic": doc_data["topic"],
                        "content": chunk_text,
                        "token_count": len(chunk_text.split()),
                        "embedding_input": embedding_text,
                    })

        # Batch embed all chunks
        logger.info(f"Computing embeddings for {len(total_chunks)} chunks...")
        inputs = [c["embedding_input"] for c in total_chunks]
        embeddings = self.embedding_service.embed_texts(inputs)

        # Save to SQLite
        for chunk_data, emb in zip(total_chunks, embeddings):
            self.repo.save_chunk(
                document_id=chunk_data["document_id"],
                chunk_id=chunk_data["chunk_id"],
                title=chunk_data["title"],
                source=chunk_data["source"],
                language=chunk_data["language"],
                topic=chunk_data["topic"],
                content=chunk_data["content"],
                token_count=chunk_data["token_count"],
                embedding=emb,
            )

        self.db.commit()
        duration = round(time.time() - start_time, 3)
        logger.info(f"RAG ingestion complete: {len(parsed_docs)} docs, {len(total_chunks)} chunks in {duration}s.")

        return RAGIngestResponse(
            documents_ingested=len(parsed_docs),
            chunks_created=len(total_chunks),
            duration_seconds=duration,
            message="Knowledge base successfully ingested and embedded.",
        )


def run_ingestion_cli(knowledge_dir: str = "data/knowledge_base"):
    """CLI helper to trigger ingestion manually."""
    init_db()
    db = SessionLocal()
    try:
        pipeline = KnowledgeIngestionPipeline(db)
        path = Path(knowledge_dir)
        if not path.is_absolute():
            path = Path(os.getcwd()) / path
        res = pipeline.ingest_directory(path)
        print(f"Ingestion result: {res.message} ({res.documents_ingested} docs, {res.chunks_created} chunks in {res.duration_seconds}s)")
        return res
    finally:
        db.close()


if __name__ == "__main__":
    run_ingestion_cli()

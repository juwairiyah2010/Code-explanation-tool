from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.core.database import Base
from datetime import datetime, timezone
import json

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(Text, nullable=False)
    language = Column(String(50), nullable=False, index=True)
    level = Column(String(50), nullable=False)
    ast_summary = Column(Text, nullable=True) # JSON encoded string
    created_at = Column(DateTime, default=utc_now, nullable=False)

    explanation = relationship("Explanation", back_populates="submission", uselist=False, cascade="all, delete-orphan")
    blocks = relationship("Block", back_populates="submission", cascade="all, delete-orphan")
    concepts = relationship("Concept", back_populates="submission", cascade="all, delete-orphan")
    quiz_items = relationship("QuizItem", back_populates="submission", cascade="all, delete-orphan")

class Explanation(Base):
    __tablename__ = "explanations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, nullable=False)
    summary = Column(Text, nullable=False)
    algorithm_steps = Column(Text, nullable=True) # JSON encoded list
    complexity = Column(Text, nullable=True) # JSON encoded dict
    hints = Column(Text, nullable=True) # JSON encoded list
    created_at = Column(DateTime, default=utc_now, nullable=False)

    submission = relationship("Submission", back_populates="explanation")

class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=False)
    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=False)

    submission = relationship("Submission", back_populates="blocks")

class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    definition = Column(Text, nullable=False)

    submission = relationship("Submission", back_populates="concepts")

class QuizItem(Base):
    __tablename__ = "quiz_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    options = Column(Text, nullable=False) # JSON encoded list
    correct_option_id = Column(String(50), nullable=False)
    explanation = Column(Text, nullable=False)
    line_reference = Column(String(50), nullable=True)

    submission = relationship("Submission", back_populates="quiz_items")

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doc_id = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    language = Column(String(50), index=True, nullable=False)
    topic = Column(String(100), index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(150), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    language = Column(String(50), index=True, nullable=False)
    topic = Column(String(100), index=True, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    embedding = Column(Text, nullable=False)  # JSON-encoded float array
    created_at = Column(DateTime, default=utc_now, nullable=False)

    document = relationship("KnowledgeDocument", back_populates="chunks")


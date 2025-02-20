from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Float,
    ForeignKey,
    Table,
    Boolean,
)
from sqlalchemy.orm import relationship, backref
from datetime import datetime
from database import Base


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True)
    subject = Column(String)
    sender = Column(String)
    recipient = Column(String)
    content = Column(Text)
    html_content = Column(Text, nullable=True)
    received_date = Column(DateTime, default=datetime.utcnow)
    thread_id = Column(String, ForeignKey("email_threads.thread_id"), index=True)
    embedding_id = Column(String, unique=True)

    # Metadata
    importance_score = Column(Float, default=0.0)
    is_processed = Column(Boolean, default=False)
    category = Column(String, nullable=True)

    # Relations
    parent_id = Column(Integer, ForeignKey("emails.id"), nullable=True)
    replies = relationship(
        "Email",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
    )


class EmailThread(Base):
    __tablename__ = "email_threads"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, unique=True, index=True)
    subject = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)
    participant_count = Column(Integer, default=1)
    email_count = Column(Integer, default=1)

    # Relations
    emails = relationship("Email", backref="thread", lazy="dynamic")


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    company = Column(String)
    description = Column(Text)
    requirements = Column(Text)
    location = Column(String)
    salary_range = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active")  # active, filled, expired
    embedding_id = Column(String, unique=True)
    source_email_id = Column(Integer, ForeignKey("emails.id"), nullable=True)

    # Relations
    source_email = relationship("Email", backref="job_postings")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True)
    resume_text = Column(Text)
    skills = Column(Text)
    experience = Column(Text)
    preferred_location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    embedding_id = Column(String, unique=True)


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"))
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    match_score = Column(Float)
    ai_analysis = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  # pending, accepted, rejected

    # Relations
    job = relationship("JobPosting", backref="matches")
    candidate = relationship("Candidate", backref="matches")

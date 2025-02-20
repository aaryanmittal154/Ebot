from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional


class EmailBase(BaseModel):
    subject: str
    sender: EmailStr
    recipient: EmailStr
    content: str
    html_content: Optional[str] = None
    thread_id: Optional[str] = None


class EmailCreate(EmailBase):
    message_id: str
    received_date: datetime


class EmailResponse(EmailBase):
    id: int
    message_id: str
    received_date: datetime
    embedding_id: str
    importance_score: float
    is_processed: bool
    category: Optional[str] = None

    class Config:
        from_attributes = True


class SimilarEmail(BaseModel):
    id: int
    subject: str
    content: str
    similarity_score: float
    thread_id: Optional[str]


class SimilarityResponse(BaseModel):
    best_match: Optional[SimilarEmail]
    similar_emails: List[SimilarEmail]
    similarity_score: float


class ThreadResponse(BaseModel):
    id: int
    thread_id: str
    subject: str
    last_updated: datetime
    participant_count: int
    email_count: int
    emails: List[EmailResponse]

    class Config:
        from_attributes = True

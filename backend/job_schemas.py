from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional


class JobPostingBase(BaseModel):
    title: str
    company: str
    description: str
    requirements: str
    location: str
    salary_range: Optional[str] = None


class JobPostingCreate(JobPostingBase):
    pass


class JobPostingResponse(JobPostingBase):
    id: int
    created_at: datetime
    status: str
    embedding_id: str

    class Config:
        from_attributes = True


class CandidateBase(BaseModel):
    name: str
    email: EmailStr
    resume_text: str
    skills: str
    experience: str
    preferred_location: Optional[str] = None


class CandidateCreate(CandidateBase):
    pass


class CandidateResponse(CandidateBase):
    id: int
    created_at: datetime
    last_updated: datetime
    embedding_id: str

    class Config:
        from_attributes = True


class MatchResponse(BaseModel):
    id: int
    job: JobPostingResponse
    candidate: CandidateResponse
    match_score: float
    ai_analysis: str
    created_at: datetime
    status: str

    class Config:
        from_attributes = True


class JobMatchResult(BaseModel):
    job: JobPostingResponse
    match_score: float
    ai_analysis: str


class CandidateMatchResult(BaseModel):
    candidate: CandidateResponse
    match_score: float
    ai_analysis: str


class JobMatches(BaseModel):
    job: JobPostingResponse
    matches: List[CandidateMatchResult]


class CandidateMatches(BaseModel):
    candidate: CandidateResponse
    matches: List[JobMatchResult]

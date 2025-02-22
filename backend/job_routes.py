from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import JobPosting, Candidate, Match, Email
from job_schemas import (
    JobPostingCreate,
    JobPostingResponse,
    CandidateCreate,
    CandidateResponse,
    JobMatches,
    CandidateMatches,
)
from job_matcher import JobMatcher
from vector_store import VectorStore
from config import Settings
from openai import AsyncOpenAI
import re
from datetime import datetime, timedelta
import json

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Initialize services
settings = Settings()
vector_store = VectorStore(settings)
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
job_matcher = JobMatcher(vector_store, openai_client)


@router.post("/postings/", response_model=JobPostingResponse)
async def create_job_posting(job: JobPostingCreate, db: Session = Depends(get_db)):
    """Create a new job posting"""
    try:
        # Create job posting
        job_posting = JobPosting(**job.dict())
        db.add(job_posting)
        db.flush()

        # Create embedding
        job_text = f"{job.title} {job.description} {job.requirements}"
        embedding_id = await vector_store.add_text(
            job_text,
            metadata={
                "type": "job",
                "embedding_id": f"job_{job_posting.id}",
            },
        )
        job_posting.embedding_id = embedding_id

        db.commit()
        return job_posting
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/candidates/", response_model=CandidateResponse)
async def create_candidate(candidate: CandidateCreate, db: Session = Depends(get_db)):
    """Create a new candidate profile"""
    try:
        # Create candidate
        candidate_profile = Candidate(**candidate.dict())
        db.add(candidate_profile)
        db.flush()

        # Create embedding
        candidate_text = (
            f"{candidate.skills} {candidate.experience} {candidate.resume_text}"
        )
        embedding_id = await vector_store.add_text(
            candidate_text,
            metadata={
                "type": "candidate",
                "embedding_id": f"candidate_{candidate_profile.id}",
            },
        )
        candidate_profile.embedding_id = embedding_id

        db.commit()
        return candidate_profile
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/postings/", response_model=List[JobPostingResponse])
async def list_job_postings(
    skip: int = 0, limit: int = 10, db: Session = Depends(get_db)
):
    """List all job postings with pagination"""
    jobs = db.query(JobPosting).offset(skip).limit(limit).all()
    return jobs


@router.get("/candidates/", response_model=List[CandidateResponse])
async def list_candidates(
    skip: int = 0, limit: int = 10, db: Session = Depends(get_db)
):
    """List all candidates with pagination"""
    candidates = db.query(Candidate).offset(skip).limit(limit).all()
    return candidates


@router.get("/postings/{job_id}/matches", response_model=JobMatches)
async def get_job_matches(job_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """Get matching candidates for a job posting"""
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    matches = await job_matcher.find_matching_candidates(job, db, limit)
    return {
        "job": job,
        "matches": [
            {
                "candidate": match["candidate"],
                "match_score": match["match_score"],
                "ai_analysis": match["ai_analysis"],
            }
            for match in matches
        ],
    }


@router.get("/candidates/{candidate_id}/matches", response_model=CandidateMatches)
async def get_candidate_matches(
    candidate_id: int, limit: int = 5, db: Session = Depends(get_db)
):
    """Get matching jobs for a candidate"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    matches = await job_matcher.find_matching_jobs(candidate, db, limit)
    return {
        "candidate": candidate,
        "matches": [
            {
                "job": match["job"],
                "match_score": match["match_score"],
                "ai_analysis": match["ai_analysis"],
            }
            for match in matches
        ],
    }


@router.post("/refresh/")
async def refresh_jobs_and_candidates(db: Session = Depends(get_db)):
    """Process emails to extract job postings and candidates"""
    try:
        # Get all emails instead of just recent ones
        emails = db.query(Email).all()

        jobs_created = 0
        candidates_created = 0

        for email in emails:
            try:
                # First, use OpenAI to classify the email and extract structured information
                prompt = f"""Analyze this email and determine if it's a job posting or a candidate profile.
                Then extract relevant information in JSON format.

                Email Subject: {email.subject}
                Email Content: {email.content}

                Respond in this JSON format:
                {{
                    "type": "job_posting" or "candidate_profile" or "other",
                    "confidence": 0.0 to 1.0,
                    "extracted_info": {{
                        // For job_posting:
                        "title": "extracted job title",
                        "company": "company name",
                        "location": "job location",
                        "requirements": "list of requirements",
                        "salary_range": "salary range if mentioned",

                        // For candidate_profile:
                        "name": "candidate name",
                        "skills": "extracted skills",
                        "experience": "extracted experience",
                        "preferred_location": "preferred location if mentioned"
                    }}
                }}"""

                response = await openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at analyzing emails and extracting job-related information.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )

                analysis = response.choices[0].message.content
                result = json.loads(analysis)

                if result["type"] == "job_posting" and result["confidence"] > 0.7:
                    # Check if job already exists
                    existing_job = (
                        db.query(JobPosting)
                        .filter(
                            JobPosting.title == result["extracted_info"]["title"],
                            JobPosting.company == result["extracted_info"]["company"],
                            JobPosting.source_email_id == email.id,
                        )
                        .first()
                    )

                    if not existing_job:
                        # Create job posting
                        job = JobPosting(
                            title=result["extracted_info"]["title"],
                            company=result["extracted_info"]["company"],
                            description=email.content,
                            requirements=result["extracted_info"]["requirements"],
                            location=result["extracted_info"]["location"],
                            salary_range=result["extracted_info"].get("salary_range"),
                            status="active",
                            source_email_id=email.id,
                        )
                        db.add(job)
                        db.flush()

                        # Create embedding for job
                        job_text = f"{job.title} {job.description} {job.requirements}"
                        embedding_id = await vector_store.add_text(
                            job_text,
                            metadata={
                                "type": "job",
                                "embedding_id": f"job_{job.id}",
                            },
                        )
                        job.embedding_id = embedding_id
                        jobs_created += 1

                elif (
                    result["type"] == "candidate_profile" and result["confidence"] > 0.7
                ):
                    # Check if candidate already exists
                    existing_candidate = (
                        db.query(Candidate)
                        .filter(Candidate.email == email.sender)
                        .first()
                    )

                    if not existing_candidate:
                        # Create candidate profile
                        candidate = Candidate(
                            name=result["extracted_info"]["name"],
                            email=email.sender,
                            resume_text=email.content,
                            skills=result["extracted_info"]["skills"],
                            experience=result["extracted_info"]["experience"],
                            preferred_location=result["extracted_info"].get(
                                "preferred_location"
                            ),
                        )
                        db.add(candidate)
                        db.flush()

                        # Create embedding for candidate
                        candidate_text = f"{candidate.skills} {candidate.experience} {candidate.resume_text}"
                        embedding_id = await vector_store.add_text(
                            candidate_text,
                            metadata={
                                "type": "candidate",
                                "embedding_id": f"candidate_{candidate.id}",
                            },
                        )
                        candidate.embedding_id = embedding_id
                        candidates_created += 1

            except Exception as email_error:
                print(f"Error processing email {email.id}: {str(email_error)}")
                continue

        db.commit()
        return {
            "message": f"Processed {len(emails)} emails. Created {jobs_created} jobs and {candidates_created} candidates."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

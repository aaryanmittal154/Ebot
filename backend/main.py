from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import uvicorn
from datetime import datetime
from sqlalchemy import or_

from database import get_db, init_db
from models import Base, Email
from schemas import EmailCreate, EmailResponse, SimilarityResponse
from email_processor import EmailProcessor
from vector_store import VectorStore
from config import Settings
from job_routes import router as job_router

app = FastAPI(title="Advanced Email RAG System")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
settings = Settings()
email_processor = EmailProcessor(settings)
vector_store = VectorStore(settings)


@app.on_event("startup")
async def startup_event():
    init_db()


@app.get("/emails/", response_model=List[EmailResponse])
async def get_emails(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all processed emails with pagination"""
    emails = db.query(Email).offset(skip).limit(limit).all()
    return emails


@app.post("/process-emails/")
async def process_new_emails(db: Session = Depends(get_db)):
    """Process new emails from the IMAP server"""
    try:
        processed_emails = await email_processor.process_new_emails(db)
        return {"message": f"Processed {len(processed_emails)} new emails"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/similar-emails/{email_id}", response_model=SimilarityResponse)
async def find_similar_emails(email_id: int, db: Session = Depends(get_db)):
    """Find similar emails for a given email ID"""
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    original_email = {
        "subject": email.subject,
        "content": email.content,
        "id": email.id,
        "thread_id": email.thread_id,
    }

    similar_emails = await vector_store.find_similar_emails(
        email.content,
        db,
        n_results=3,  # Limit to top 3 for LLM analysis
        current_thread_id=email.thread_id,
        original_email=original_email,
    )
    return similar_emails


@app.post("/auto-reply/{email_id}")
async def generate_auto_reply(email_id: int, db: Session = Depends(get_db)):
    """Generate an auto-reply based on similar past emails"""
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    similar_emails_response = await vector_store.find_similar_emails(email.content, db)

    if (
        similar_emails_response["similarity_score"] >= 0.7
    ):  # Lower threshold for better matches
        return {
            "can_auto_reply": True,
            "reply": similar_emails_response["best_match"]["content"],
            "similarity_score": similar_emails_response["similarity_score"],
        }
    else:
        return {
            "can_auto_reply": False,
            "similar_questions": similar_emails_response["similar_emails"],
            "message": "No similar question found with high confidence",
        }


@app.get("/emails/{email_id}", response_model=EmailResponse)
async def get_email(email_id: int, db: Session = Depends(get_db)):
    """Get a specific email by ID"""
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


@app.post("/reprocess-embeddings/")
async def reprocess_embeddings(db: Session = Depends(get_db)):
    """Reprocess all emails to update their embeddings with the new model"""
    try:
        # Get all emails
        emails = db.query(Email).all()

        # Clear existing collection
        vector_store.clear_collection()

        # Reprocess each email
        for email in emails:
            # Create new embedding
            embedding_id = await vector_store.add_text(
                email.content,
                metadata={
                    "subject": email.subject,
                    "thread_id": email.thread_id,
                },
            )

            # Update email record
            email.embedding_id = embedding_id

        db.commit()
        return {"message": f"Reprocessed {len(emails)} emails with new embeddings"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/")
async def search_emails(query: str, db: Session = Depends(get_db)):
    """Search emails by content and subject"""
    try:
        # Search in vector store first
        search_results = await vector_store.search_emails(query, db)

        if not search_results:
            # Fallback to basic SQL search if no vector results
            search_pattern = f"%{query}%"
            emails = (
                db.query(Email)
                .filter(
                    or_(
                        Email.subject.ilike(search_pattern),
                        Email.content.ilike(search_pattern),
                        Email.sender.ilike(search_pattern),
                    )
                )
                .all()
            )
            return {"results": emails}

        return search_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Add job routes
app.include_router(job_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

from database import SessionLocal, init_db
from models import Email, EmailThread, JobPosting, Candidate, Match
from vector_store import VectorStore
from config import Settings


def reset_database():
    print("Resetting database...")
    db = SessionLocal()

    # Delete all data in reverse order of dependencies
    print("Deleting existing data...")
    db.query(Match).delete()
    db.query(JobPosting).delete()
    db.query(Candidate).delete()
    db.query(Email).delete()
    db.query(EmailThread).delete()

    # Commit the changes
    db.commit()

    print("Reinitializing database...")
    init_db()

    # Reset ChromaDB collection
    print("Resetting ChromaDB collection...")
    vector_store = VectorStore(Settings())
    vector_store.clear_collection()

    print("Database reset complete!")


if __name__ == "__main__":
    reset_database()

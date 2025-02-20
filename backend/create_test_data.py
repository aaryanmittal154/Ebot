from datetime import datetime
from sqlalchemy.orm import Session
from models import Email
from database import SessionLocal, init_db

# Initialize database
init_db()

# Create test emails
db = SessionLocal()

# Sample job posting email
job_email = Email(
    message_id="test_job_1",
    subject="New Job Opening: Senior Software Engineer",
    sender="hr@company.com",
    recipient="jobs@company.com",
    content="""Position: Senior Software Engineer
Company: Tech Solutions Inc.
Location: San Francisco, CA
Requirements: Python, React, 5+ years experience
Salary: $150,000 - $200,000

We are looking for a Senior Software Engineer to join our team. The ideal candidate will have strong experience in Python and React development.

Key Responsibilities:
- Develop and maintain web applications
- Write clean, maintainable code
- Collaborate with cross-functional teams

Additional Requirements:
- Strong problem-solving skills
- Experience with cloud platforms
- Excellent communication skills
""",
    received_date=datetime.utcnow(),
    thread_id="job_thread_1",
    embedding_id="test_job_1",
    is_processed=True,
)

# Sample candidate email
candidate_email = Email(
    message_id="test_candidate_1",
    subject="Resume Submission - Software Engineer Application",
    sender="john.doe@email.com",
    recipient="jobs@company.com",
    content="""Name: John Doe
Skills: Python, JavaScript, React, Node.js, AWS
Experience: 6 years in full-stack development
Preferred Location: San Francisco, CA

Professional Summary:
I am a seasoned software engineer with 6 years of experience in full-stack development. I have successfully delivered multiple web applications using Python, React, and Node.js.

Key Achievements:
- Led a team of 5 developers
- Reduced application load time by 40%
- Implemented CI/CD pipelines

Education:
- BS in Computer Science
""",
    received_date=datetime.utcnow(),
    thread_id="candidate_thread_1",
    embedding_id="test_candidate_1",
    is_processed=True,
)

# Clear existing data
db.query(Email).delete()
db.commit()

# Add new test data
db.add(job_email)
db.add(candidate_email)
db.commit()
db.close()
print("Test emails created successfully!")

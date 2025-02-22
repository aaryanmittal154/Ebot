from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Email, EmailThread, JobPosting, Candidate, Match
from database import SessionLocal, init_db
import uuid
import random
import re

# Initialize database
init_db()

# Create test emails
db = SessionLocal()

# Clear existing data in the correct order
db.query(Match).delete()
db.query(JobPosting).delete()
db.query(Candidate).delete()
db.query(Email).delete()
db.query(EmailThread).delete()
db.commit()

# Sample email senders and domains
domains = [
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "company.com",
    "startup.io",
    "tech.co",
]
first_names = [
    "John",
    "Sarah",
    "Michael",
    "Emily",
    "David",
    "Lisa",
    "James",
    "Emma",
    "Alex",
    "Rachel",
]
last_names = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
]


def generate_email():
    first = random.choice(first_names)
    last = random.choice(last_names)
    domain = random.choice(domains)
    return f"{first.lower()}.{last.lower()}@{domain}"


# Generate some company emails
company_emails = [
    "hr@techstartup.com",
    "recruiting@innovate.io",
    "jobs@futuretech.co",
    "careers@aicompany.com",
    "talent@nextgen.com",
]

# Job posting templates
job_posting_templates = [
    {
        "role": "Senior AI Engineer",
        "content": """We're seeking a Senior AI Engineer to join our growing team at TechStartup!

Key Responsibilities:
- Lead the development of ML/AI solutions
- Mentor junior engineers and contribute to architecture decisions
- Collaborate with product and research teams
- Drive innovation in our AI platform

Requirements:
- 5+ years of experience in ML/AI development
- Strong Python programming skills
- Experience with modern ML frameworks (PyTorch, TensorFlow)
- Background in NLP and transformer architectures
- Track record of deploying ML models to production

Benefits:
- Competitive salary ($150k-$200k)
- Equity package
- Remote-first culture
- Comprehensive health benefits
- Learning and development budget

Join us in building the future of AI! Send your resume and a brief introduction.""",
    },
    {
        "role": "Frontend Developer",
        "content": """Exciting opportunity for a Frontend Developer to join our product team!

What you'll do:
- Build beautiful, responsive web applications
- Work with our design team to implement pixel-perfect UIs
- Optimize application performance
- Contribute to our component library

Required Skills:
- 3+ years of experience with React
- Strong TypeScript knowledge
- Experience with modern CSS and styling solutions
- Understanding of web performance optimization
- Eye for design and attention to detail

We offer:
- Competitive compensation
- Flexible working hours
- Health and dental coverage
- Regular team events
- Professional development opportunities

If you're passionate about creating exceptional user experiences, we'd love to hear from you!""",
    },
    {
        "role": "Product Manager",
        "content": """Product Manager Opening at InnovateTech!

We're looking for a Product Manager to drive our product strategy and execution.

Responsibilities:
- Own the product roadmap and vision
- Work closely with engineering and design teams
- Conduct user research and gather requirements
- Define and track key metrics
- Prioritize features and manage backlog

Requirements:
- 4+ years of product management experience
- Strong analytical and problem-solving skills
- Excellent communication abilities
- Experience with agile methodologies
- Technical background preferred

What we offer:
- Competitive base salary + bonus
- Stock options
- Premium healthcare
- Flexible PTO
- Remote work options

Join us in shaping the future of technology!""",
    },
]

# Technical discussion templates
technical_discussion_templates = [
    {
        "subject": "Code Review Feedback",
        "content": """Hi team,

I've reviewed the latest PR for the authentication service refactor and have some feedback:

1. Authentication middleware could be more modular
2. We should add more unit tests for edge cases
3. Consider using a connection pool for DB access
4. Some SQL queries could be optimized

I've added detailed comments in the PR. Let's discuss these points in our next sync.

Best regards,
{sender}""",
    },
    {
        "subject": "Performance Optimization Ideas",
        "content": """Team,

After analyzing our application performance metrics, I've identified several areas for improvement:

1. Frontend:
   - Implement lazy loading for images
   - Add component code splitting
   - Optimize bundle size

2. Backend:
   - Cache frequently accessed data
   - Optimize database queries
   - Implement request batching

Would love to get your thoughts on these suggestions and prioritize our optimization efforts.

Thanks,
{sender}""",
    },
    {
        "subject": "Technical Discussion",
        "content": """Hey everyone,

I'd like to propose switching our current monolithic architecture to a microservices approach. Here's why:

- Better scalability for individual components
- Easier maintenance and deployments
- More flexibility in choosing technologies
- Improved fault isolation

I've created a preliminary design doc here: [link]

Let me know your thoughts and concerns.

Best,
{sender}""",
    },
]

# Reply templates for different types of emails
job_application_replies = [
    """Dear {recipient},

I'm very interested in the {role} position at your company. With {years} years of relevant experience, I believe I would be a strong addition to your team.

Key highlights from my background:
- Led development of ML systems at {previous_company}
- Implemented and deployed various production AI models
- Mentored junior engineers and managed small teams
- Published research papers on deep learning architectures

I'm particularly drawn to your company's mission and the opportunity to work on cutting-edge AI solutions.

Looking forward to discussing this opportunity further.

Best regards,
{sender}""",
    """Hi {recipient},

I came across your job posting for the {role} position and I'm excited to apply. My background aligns perfectly with your requirements:

- {years}+ years of hands-on experience
- Strong track record in similar roles
- Expertise in required technologies
- Proven leadership abilities

I'm especially impressed by your company's recent projects in {domain} and would love to contribute my expertise.

Would appreciate the opportunity to discuss how I can add value to your team.

Best,
{sender}""",
    """Hello {recipient},

I'm writing to express my strong interest in the {role} position. Your company's innovative approach to {domain} really resonates with me.

My relevant experience includes:
- Developing scalable solutions at {previous_company}
- Leading cross-functional teams
- Implementing best practices and improving processes
- Contributing to open-source projects

I believe my skills and experience make me an ideal candidate for this role.

Thank you for considering my application.

Regards,
{sender}""",
]

technical_discussion_replies = [
    """Hi {sender},

Thanks for the detailed review. I agree with most points and have some additional thoughts:

1. Re: Authentication middleware
   - We could use a decorator pattern
   - Consider implementing rate limiting
   - Add request context validation

2. For the DB connection pool:
   - What size do you recommend?
   - Should we implement retry logic?

I'll start addressing these in the next PR.

Best,
{reply_sender}""",
    """Thanks for bringing this up, {sender}.

Your points make sense. Some additional considerations:

1. For the frontend optimizations:
   - We could use intersection observer for lazy loading
   - Consider using webpack bundle analyzer
   - Implement service worker for caching

2. Database optimizations:
   - Add proper indexing
   - Consider materialized views
   - Implement query caching

Happy to discuss these in more detail.

Regards,
{reply_sender}""",
    """Hey {sender},

Interesting proposal! Some thoughts on the microservices approach:

Pros:
+ Agreed on scalability benefits
+ Better team autonomy
+ Easier to maintain

Concerns:
- Increased operational complexity
- Service communication overhead
- Need for better monitoring

Let's discuss these points in the next architecture review.

Best,
{reply_sender}""",
]

# Create email threads first
threads = []
thread_subjects = [
    "Senior AI Engineer Position at TechStartup",
    "Frontend Developer Role",
    "Product Manager Opening",
    "DevOps Engineer Position",
    "Data Scientist Role",
    "Technical Discussion",
    "Project Update",
    "Team Meeting Notes",
    "Code Review Feedback",
    "Performance Optimization Ideas",
]

for subject in thread_subjects:
    thread = EmailThread(
        thread_id=str(uuid.uuid4()),
        subject=subject,
        last_updated=datetime.utcnow(),
        participant_count=1,
        email_count=1,
    )
    threads.append(thread)

db.add_all(threads)
db.commit()

# Now create emails
emails = []
base_date = datetime.utcnow() - timedelta(days=10)

for thread in threads:
    # Original email in thread
    sender = (
        random.choice(company_emails)
        if "Position" in thread.subject or "Role" in thread.subject
        else generate_email()
    )

    # Generate content based on thread type
    if "Position" in thread.subject or "Role" in thread.subject:
        # Find matching job template or use the first one
        job_template = next(
            (t for t in job_posting_templates if t["role"] in thread.subject),
            job_posting_templates[0],
        )
        content = job_template["content"]
        category = "job_posting"
    else:
        # Find matching technical template or use the first one
        tech_template = next(
            (
                t
                for t in technical_discussion_templates
                if t["subject"] in thread.subject
            ),
            technical_discussion_templates[0],
        )
        content = tech_template["content"].format(sender=sender.split("@")[0])
        category = "technical"

    original_email = Email(
        message_id=str(uuid.uuid4()),
        subject=thread.subject,
        sender=sender,
        recipient=(
            "jobs@techstartup.com"
            if "Position" in thread.subject or "Role" in thread.subject
            else generate_email()
        ),
        content=content,
        received_date=base_date + timedelta(hours=random.randint(0, 24)),
        thread_id=thread.thread_id,
        embedding_id=str(uuid.uuid4()),
        importance_score=0.0,
        is_processed=True,
        category=category,
    )
    emails.append(original_email)

    # Generate 2-4 replies for each thread
    num_replies = random.randint(2, 4)
    for i in range(num_replies):
        reply_sender = generate_email()

        # Generate reply content based on thread type
        if "Position" in thread.subject or "Role" in thread.subject:
            reply_template = random.choice(job_application_replies)
            role = thread.subject.split(" Position")[0].split(" Role")[0]
            content = reply_template.format(
                recipient=sender.split("@")[0],
                role=role,
                years=random.randint(3, 8),
                previous_company=random.choice(
                    ["Google", "Microsoft", "Amazon", "Meta", "Apple"]
                ),
                domain="AI" if "AI" in thread.subject else "technology",
                sender=reply_sender.split("@")[0],
            )
            category = "job_application"
        else:
            reply_template = random.choice(technical_discussion_replies)
            content = reply_template.format(
                sender=sender.split("@")[0], reply_sender=reply_sender.split("@")[0]
            )
            category = "technical"

        reply_email = Email(
            message_id=str(uuid.uuid4()),
            subject=f"Re: {thread.subject}",
            sender=reply_sender,
            recipient=sender,
            content=content,
            received_date=base_date + timedelta(hours=random.randint(24, 72)),
            thread_id=thread.thread_id,
            embedding_id=str(uuid.uuid4()),
            importance_score=0.0,
    is_processed=True,
            category=category,
        )
        emails.append(reply_email)

        # Update thread's participant count and email count
        thread.participant_count += 1
        thread.email_count += 1
        thread.last_updated = reply_email.received_date

db.add_all(emails)
db.commit()

print(f"Created {len(threads)} email threads and {len(emails)} emails successfully!")

# Create job postings from the email data
job_postings = []
for email in emails:
    if email.category == "job_posting":
        # Extract salary range from content if available
        salary_range = None
        if "salary" in email.content.lower():
            # Simple regex to find salary ranges like $150k-$200k
            salary_match = re.search(r"\$\d+k-\$\d+k", email.content)
            if salary_match:
                salary_range = salary_match.group(0)

        # Extract location if available
        location = "Remote"  # Default to remote
        if "location" in email.content.lower():
            location_match = re.search(r"location:?\s*([^.•\n]+)", email.content, re.I)
            if location_match:
                location = location_match.group(1).strip()

        # Extract requirements
        requirements = []
        if "requirements:" in email.content.lower():
            req_section = (
                email.content.lower().split("requirements:")[1].split("\n\n")[0]
            )
            requirements = [
                r.strip("- ").strip() for r in req_section.split("\n") if r.strip()
            ]

        job_posting = JobPosting(
            title=email.subject.replace("Position at", "")
            .replace("Role at", "")
            .strip(),
            company=email.sender.split("@")[1].split(".")[0].title(),
            description=email.content,
            requirements=requirements,
            location=location,
            salary_range=salary_range,
            created_at=email.received_date,
            status="active",
            embedding_id=str(uuid.uuid4()),
            source_email_id=email.id,
        )
        job_postings.append(job_posting)

db.add_all(job_postings)
db.commit()

# Create candidates from job application emails
candidates = []
for email in emails:
    if email.category == "job_application":
        # Extract experience from content
        experience = None
        exp_match = re.search(r"(\d+)\+?\s*years?", email.content)
        if exp_match:
            experience = f"{exp_match.group(1)}+ years"

        # Extract skills from content
        skills = []
        if (
            "experience" in email.content.lower()
            or "expertise" in email.content.lower()
        ):
            # Look for bullet points or lines containing technical terms
            skill_indicators = [
                "python",
                "javascript",
                "react",
                "node",
                "aws",
                "ml",
                "ai",
                "deep learning",
                "machine learning",
                "frontend",
                "backend",
                "full stack",
                "database",
                "cloud",
                "devops",
            ]
            for line in email.content.split("\n"):
                line = line.lower()
                if any(indicator in line for indicator in skill_indicators):
                    skills.append(line.strip("- ").strip())

        candidate = Candidate(
            name=email.sender.split("@")[0].replace(".", " ").title(),
            email=email.sender,
            resume_text=email.content,
            skills=skills,
            experience=experience if experience else "Not specified",
            preferred_location="Remote",  # Default to remote
            created_at=email.received_date,
            last_updated=email.received_date,
            embedding_id=str(uuid.uuid4()),
        )
        candidates.append(candidate)

db.add_all(candidates)
db.commit()

print(
    f"Created {len(job_postings)} job postings and {len(candidates)} candidates successfully!"
)

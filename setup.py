from setuptools import setup, find_packages

setup(
    name="email-rag",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.23",
        "psycopg2-binary>=2.9.9",
        "pydantic>=2.5.2",
        "chromadb>=0.4.18",
        "sentence-transformers>=2.2.2",
        "python-imap>=1.0.0",
        "email-validator>=2.1.0.post1",
        "python-multipart>=0.0.6",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "IMAPClient>=2.3.1",
        "langchain>=0.0.350",
        "python-dateutil>=2.8.2",
    ],
)

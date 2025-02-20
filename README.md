# Smart Email Manager

A sophisticated email management system that processes incoming emails, performs similarity search using advanced RAG (Retrieval-Augmented Generation), and generates auto-replies based on similar past conversations.

## Features

- 📧 IMAP email processing and storage
- 🔍 Advanced similarity search using ChromaDB and sentence transformers
- 💡 Intelligent auto-reply generation
- 🎯 Modern, responsive UI with Material-UI
- ⚡ Real-time email processing and updates
- 📊 Email categorization and importance scoring
- 🔄 Infinite scroll for efficient email browsing

## Tech Stack

### Backend
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- ChromaDB (Vector database)
- Sentence Transformers (Text embeddings)
- PostgreSQL (Database)
- Python IMAP client

### Frontend
- React with TypeScript
- Material-UI (Component library)
- React Query (Data fetching)
- React Router (Navigation)
- Axios (HTTP client)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd smart-email-manager
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install backend dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file with your configuration:
- Database URL
- IMAP server details
- Email credentials
- Security settings

5. Install frontend dependencies:
```bash
cd frontend
npm install
```

6. Create the database:
```bash
createdb emaildb  # If using PostgreSQL
```

## Running the Application

1. Start the backend server:
```bash
cd backend
uvicorn main:app --reload
```

2. Start the frontend development server:
```bash
cd frontend
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Usage

1. Configure your email settings in the `.env` file
2. Start both the backend and frontend servers
3. Access the web interface at http://localhost:3000
4. Click "Process New Emails" to fetch and process new emails
5. Browse through emails and view similarity matches
6. Generate auto-replies for emails with high similarity matches

## Security Considerations

- Store sensitive information in `.env` file
- Use app-specific passwords for email accounts
- Keep API keys and secrets secure
- Implement rate limiting for API endpoints
- Regular security updates for dependencies

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

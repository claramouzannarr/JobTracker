# Job Tracker

A comprehensive web application for tracking job applications with AI-powered resume evaluation.

## Features

- **User Authentication**: Secure registration and login
- **Application Tracking**: Track all your job applications in one place
- **Resume Evaluation**: Upload resumes and get detailed evaluations including:
  - Job compatibility scoring
  - Skills coverage and gaps
  - Grammar and spelling checks
  - Template quality assessment
  - Bullet point quality analysis
  - Cliché detection
- **Job Recommendations**: Get personalized job recommendations based on your profile
- **Interview Preparation**: Generate interview prep materials when you reach the interview stage

## Tech Stack

### Backend
- **FastAPI** - Python web framework
- **PostgreSQL** - Database
- **SQLAlchemy** - ORM
- **spaCy** - NLP for resume parsing
- **sentence-transformers** - Embeddings for semantic matching
- **LanguageTool** - Grammar checking
- **pdfplumber** / **python-docx** - Resume text extraction

### Frontend
- **React** with **TypeScript**
- **Tailwind CSS** - Styling
- **Vite** - Build tool
- **React Router** - Routing
- **Axios** - HTTP client

## Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL database

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install spaCy model:
```bash
# Method 1: Install via pip (recommended)
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# Method 2: Alternative pip install
pip install en-core-web-sm==3.7.1

# Method 3: Try the download command (may not work on all systems)
python -m spacy download en_core_web_sm
```

5. Create a `.env` file in the backend directory:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/jobtracker
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

6. Create the database:
```bash
createdb jobtracker
```

7. Run the backend server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user info

### Applications
- `GET /api/applications` - Get all applications
- `POST /api/applications` - Create new application
- `GET /api/applications/{id}` - Get application by ID
- `PUT /api/applications/{id}` - Update application
- `DELETE /api/applications/{id}` - Delete application

### Resumes
- `POST /api/resumes/upload/{application_id}` - Upload resume
- `GET /api/resumes/{application_id}/versions` - Get resume versions
- `GET /api/resumes/{resume_version_id}` - Get resume version details

### Jobs
- `GET /api/jobs/recommendations` - Get job recommendations

### Interview Prep
- `POST /api/interview-prep/generate/{application_id}` - Generate interview prep
- `GET /api/interview-prep/{application_id}` - Get interview prep

## Project Structure

```
JobTracker_c/
├── backend/
│   ├── app/
│   │   ├── routers/       # API routes
│   │   ├── services/      # Business logic
│   │   ├── models.py      # Database models
│   │   ├── schemas.py     # Pydantic schemas
│   │   ├── auth.py        # Authentication utilities
│   │   ├── database.py    # Database configuration
│   │   └── main.py        # FastAPI app
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/         # React pages
│   │   ├── contexts/      # React contexts
│   │   └── App.tsx
│   └── package.json
└── README.md
```

## Next Steps

- Add resume upload functionality to the frontend
- Display evaluation scores in the UI
- Implement job recommendations UI
- Add interview prep display page
- Enhance user profile editing
- Add filtering and sorting to applications table

## License

MIT


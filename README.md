# Job Tracker

A web application for tracking job applications with AI-powered resume analysis, job recommendations, and interview preparation.

## Features

- **User Authentication**: Secure registration and login with JWT
- **Application Tracking**: Create, update, and delete job applications with status tracking
- **Resume Analysis**: Upload resumes and get detailed evaluations including:
  - Format & structure scoring (15%)
  - Content depth scoring (30%) — action verbs, bullet quality, cliché detection
  - Job compatibility scoring via semantic embeddings (45%)
  - Grammar & spelling checks (10%)
  - Skill gap analysis
- **Job Recommendations**: Personalized job recommendations via Adzuna API, ranked by semantic similarity to your resume
- **Interview Preparation**: AI-generated interview questions and answer evaluation using OpenAI GPT

## Tech Stack

### Backend
- **FastAPI** — Python web framework
- **PostgreSQL** — Database
- **SQLAlchemy** — ORM
- **OpenAI API** (gpt-4o-mini) — Interview prep generation and evaluation
- **sentence-transformers** — Semantic embeddings for resume/job matching
- **LanguageTool** — Grammar checking
- **Adzuna API** — Job listings ingestion
- **pdfplumber** / **python-docx** — Resume text extraction
- **spaCy** — NLP for resume parsing and skill extraction

### Frontend
- **React** with **TypeScript**
- **Tailwind CSS** — Styling
- **Vite** — Build tool
- **React Router** — Routing
- **Axios** — HTTP client

## Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL database
- OpenAI API key
- Adzuna API credentials (optional, for job recommendations)

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
python -m spacy download en_core_web_sm
```

5. Create a `.env` file in the backend directory:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/jobtracker
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL_GENERATE=gpt-4o-mini
OPENAI_MODEL_EVAL=gpt-4o-mini
OPENAI_EMBED_MODEL=text-embedding-3-small

ADZUNA_APP_ID=your-adzuna-app-id
ADZUNA_APP_KEY=your-adzuna-app-key
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

The frontend will be available at `http://localhost:5173`

## API Endpoints

### Authentication
- `POST /api/auth/register` — Register a new user
- `POST /api/auth/login` — Login
- `GET /api/auth/me` — Get current user info
- `PATCH /api/auth/me` — Update user profile

### Applications
- `GET /api/applications` — Get all applications
- `POST /api/applications` — Create new application
- `GET /api/applications/{id}` — Get application by ID
- `GET /api/applications/{id}/evaluation` — Get resume evaluation for an application
- `PUT /api/applications/{id}` — Update application
- `DELETE /api/applications/{id}` — Delete application

### Resumes
- `POST /api/resumes/upload/{application_id}` — Upload and analyze a resume
- `GET /api/resumes/{application_id}/versions` — Get all resume versions for an application
- `GET /api/resumes/{resume_version_id}` — Get a specific resume version

### Jobs
- `GET /api/jobs/recommendations` — Get personalized job recommendations
- `POST /api/jobs/ingest/adzuna` — Ingest jobs from Adzuna API
- `POST /api/jobs/ingest/adzuna/demo` — Ingest demo jobs

### Interview Prep
- `POST /api/interview-prep/generate` — Generate interview questions for an application
- `POST /api/interview-prep/evaluate` — Evaluate a written answer
- `POST /api/interview-prep/voice-answer` — Submit and evaluate a voice answer
- `GET /api/interview-prep/{application_id}` — Get interview prep for an application

## Project Structure

```
JobTracker_c/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── applications.py
│   │   │   ├── resumes.py
│   │   │   ├── jobs.py
│   │   │   ├── interview_prep.py
│   │   │   └── admin.py
│   │   ├── services/
│   │   │   ├── resume_analyzer.py       # Resume scoring pipeline
│   │   │   ├── resume_extraction.py     # PDF/DOCX text extraction
│   │   │   ├── resume_parser.py         # Resume section parsing
│   │   │   ├── skill_extraction.py      # Skill detection & gap analysis
│   │   │   ├── embedding_service.py     # Semantic embeddings
│   │   │   ├── job_recommendation_service.py
│   │   │   ├── job_ingestion_service.py
│   │   │   ├── interview_prep_service.py
│   │   │   └── providers/
│   │   │       └── adzuna_client.py
│   │   ├── models.py      # SQLAlchemy models
│   │   ├── schemas.py     # Pydantic schemas
│   │   ├── auth.py        # JWT authentication
│   │   ├── config.py      # App settings
│   │   ├── database.py    # DB connection & migrations
│   │   └── main.py        # FastAPI app entry point
│   ├── scripts/
│   │   └── ingest_adzuna_demo.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   └── OnboardingPage.tsx
│   │   ├── components/
│   │   │   └── SearchableSelect.tsx
│   │   ├── contexts/
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
└── README.md
```

## License

MIT

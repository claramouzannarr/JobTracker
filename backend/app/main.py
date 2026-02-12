from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.database import engine, Base
from app.routers import auth, applications, resumes, jobs, interview_prep, admin

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Tracker API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced error handling for validation
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["resumes"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(interview_prep.router, prefix="/api/interview-prep", tags=["interview-prep"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/")
async def root():
    return {"message": "Job Tracker API"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


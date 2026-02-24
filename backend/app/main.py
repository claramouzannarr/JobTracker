from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.database import engine, Base, migrate_resume_versions_table, migrate_job_postings_table, migrate_interview_prep_tables
from app.routers import auth, applications, resumes, jobs, interview_prep, admin

# Create tables
Base.metadata.create_all(bind=engine)

# Run migrations to add missing columns
migrate_resume_versions_table()
migrate_job_postings_table()
migrate_interview_prep_tables()

app = FastAPI(title="Job Tracker API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Only log API requests (not static files or health checks)
    if "/api/" in str(request.url):
        print(f"\n=== REQUEST DEBUG ===")
        print(f"Method: {request.method}")
        print(f"URL: {request.url}")
        auth_header = request.headers.get("authorization", None)
        if auth_header:
            print(f"Authorization header: {auth_header[:50]}...")
            print(f"Authorization header length: {len(auth_header)}")
        else:
            print("WARNING: No Authorization header found!")
        print(f"=====================\n")
    
    response = await call_next(request)
    
    # Log response status for API requests
    if "/api/" in str(request.url):
        print(f"Response status: {response.status_code}")
    
    return response

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

# Note: FastAPI redirects /api/applications to /api/applications/ by default
# To prevent losing Authorization header during redirect, frontend should use trailing slashes
# OR we can add middleware to preserve headers during redirects


@app.get("/")
async def root():
    return {"message": "Job Tracker API"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


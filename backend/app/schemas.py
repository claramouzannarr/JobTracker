from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    age: Optional[int] = None
    country: Optional[str] = None
    graduation_year: Optional[int] = None
    highest_degree: Optional[str] = None
    major: Optional[List[str]] = None  # List of majors/fields of study
    years_experience: Optional[int] = None
    primary_industry_preference: Optional[str] = None
    primary_role_preference: Optional[str] = None
    desired_countries: Optional[List[str]] = None
    languages_spoken: Optional[List[str]] = None
    work_authorization: Optional[str] = None
    remote_preference: Optional[str] = None
    job_type_preference: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Application schemas
class ApplicationBase(BaseModel):
    company_name: str
    job_title: str
    job_url: Optional[str] = None
    job_description_text: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    status: str = "Preparing"  # Preparing, Applied, Interview Prep, Rejected
    notes: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationResponse(ApplicationBase):
    id: int
    user_id: int
    stage_updated_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    resume_score: Optional[float] = None  # Overall score from latest resume

    class Config:
        from_attributes = True


# Resume schemas
class ResumeVersionResponse(BaseModel):
    id: int
    application_id: int
    file_path: str
    extracted_text: Optional[str] = None
    parsed_sections: Optional[Dict[str, Any]] = None
    evaluation_scores: Optional[Dict[str, Any]] = None
    overall_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResumeUploadResponse(BaseModel):
    resume_version: ResumeVersionResponse
    evaluation_scores: Dict[str, Any]
    overall_score: float
    suggestions: List[str]


# Evaluation scores schema
class EvaluationScores(BaseModel):
    job_compatibility: float
    skills_coverage: float
    grammar_score: float
    template_quality: float
    bullet_quality: float
    cliche_penalty: float
    overall_score: float
    skill_gaps: List[str]
    grammar_errors: List[Dict[str, Any]]
    cliche_phrases: List[str]


# Job recommendation schemas
class JobRecommendation(BaseModel):
    id: int
    title: str
    company: str
    description_text: Optional[str] = None
    country: Optional[str] = None
    remote_flag: bool
    job_url: Optional[str] = None
    similarity_score: float

    class Config:
        from_attributes = True


# Job recommendation with explainability (recommendation endpoint)
class JobRecommendationWithReasons(BaseModel):
    job_id: int
    title: str
    company: str
    location_display: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    remote_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    description_text: Optional[str] = None
    score: float
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    penalties_applied: List[str] = []


# Adzuna ingestion request
class AdzunaIngestRequest(BaseModel):
    country: str = "gb"
    what: Optional[str] = None
    where: Optional[str] = None
    pages: int = 3
    results_per_page: int = 50


# Interview prep schemas
class InterviewPrepResponse(BaseModel):
    id: int
    application_id: int
    questions: List[str]
    resources_links: List[str]
    topics_to_review: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


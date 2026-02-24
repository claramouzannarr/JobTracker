from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    age = Column(Integer)
    country = Column(String)
    graduation_year = Column(Integer)
    highest_degree = Column(String)
    major = Column(JSON)  # List of majors/fields of study
    years_experience = Column(Integer)
    primary_industry_preference = Column(String)
    primary_role_preference = Column(String)
    desired_countries = Column(JSON)  # List of countries
    languages_spoken = Column(JSON)  # List of languages
    work_authorization = Column(String)
    gpa = Column(Float)
    remote_preference = Column(String)  # "remote", "onsite", "hybrid", "any"
    job_type_preference = Column(String)  # "full-time", "part-time", "internship", "any"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_name = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    job_url = Column(String)
    job_description_text = Column(Text)
    industry = Column(String)
    country = Column(String)
    status = Column(String, default="Preparing")  # Preparing, Applied, Interview Prep, Rejected
    stage_updated_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="applications")
    resume_versions = relationship("ResumeVersion", back_populates="application", cascade="all, delete-orphan")
    interview_prep = relationship("InterviewPrep", back_populates="application", uselist=False, cascade="all, delete-orphan")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    file_path = Column(String, nullable=False)
    extracted_text = Column(Text)
    parsed_sections = Column(JSON)  # Store parsed sections structure
    evaluation_scores = Column(JSON)  # Store all evaluation metrics
    overall_score = Column(Float)  # Overall score (0-100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", back_populates="resume_versions")


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_job_posting_source_external_id"),)

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)  # adzuna, Greenhouse, Lever, etc.
    external_id = Column(String, index=True)  # ID from external API; unique per source
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    description_text = Column(Text)
    job_url = Column(String)
    country = Column(String)
    location_display = Column(String)  # Human-readable location string
    contract_type = Column(String)  # full-time, part-time, etc.
    salary_min = Column(Float)
    salary_max = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)
    remote_flag = Column(Boolean, default=False)
    remote_type = Column(String)  # "remote", "hybrid", "onsite"
    description_hash = Column(String)  # For detecting description changes to recompute embedding
    embedding_vector = Column(JSON)  # 384-dim embedding (all-MiniLM-L6-v2)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterviewPrep(Base):
    __tablename__ = "interview_prep"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), unique=True, nullable=False)
    questions = Column(JSON)  # Legacy: list of question strings (kept for backward compatibility)
    resources_links = Column(JSON)  # Legacy
    topics_to_review = Column(JSON)  # Legacy
    generated_json = Column(JSON)  # Full prep package: role_context, questions[], skill_gaps, study_plan, answer_rubric
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    application = relationship("Application", back_populates="interview_prep")
    answers = relationship("InterviewAnswer", back_populates="interview_prep", cascade="all, delete-orphan")


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True)
    interview_prep_id = Column(Integer, ForeignKey("interview_prep.id"), nullable=False)
    question_id = Column(String, nullable=False)  # e.g. "q1", "q3"
    answer_text = Column(Text)  # Typed answer (or transcript from voice)
    transcript_text = Column(Text, nullable=True)  # Voice transcript if submitted via voice
    score = Column(Integer)  # 0-5
    feedback_json = Column(JSON)  # strengths, missing_points, improved_answer, next_drill
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interview_prep = relationship("InterviewPrep", back_populates="answers")


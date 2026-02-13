from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Float
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

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)  # Greenhouse, Lever, SmartRecruiters, Manual
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    description_text = Column(Text)
    country = Column(String)
    remote_flag = Column(Boolean, default=False)
    job_url = Column(String)
    embedding_vector = Column(JSON)  # Store embedding as JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterviewPrep(Base):
    __tablename__ = "interview_prep"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), unique=True, nullable=False)
    questions = Column(JSON)  # List of questions
    resources_links = Column(JSON)  # List of resource URLs
    topics_to_review = Column(JSON)  # List of topics/skills
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    application = relationship("Application", back_populates="interview_prep")


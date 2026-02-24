# System Overview: AI-Powered Job Application Tracker

## Introduction

This document provides a high-level overview of how the Job Application Tracking System works. The system helps job seekers by automatically analyzing their resumes, matching them with relevant job opportunities, and preparing them for interviews using artificial intelligence.

The system consists of four main components:
1. **User Interface** - How users interact with the system
2. **Resume Analyzer** - Automated resume evaluation and feedback
3. **Job Recommendation** - Personalized job matching
4. **Interview Preparation** - Role-specific interview questions and resources

---

## 1. User Interface

### 1.1 System Flow

When users first access the system, they go through a simple registration and onboarding process:

**Registration & Onboarding:**
- Users create an account with basic information (name, email, password)
- After registration, users complete a questionnaire that collects:
  - **Career preferences**: Desired role (e.g., Software Engineer, Data Scientist)
  - **Industry preference**: Target industry (e.g., Technology, Finance)
  - **Location preferences**: Current country and desired countries to work in
  - **Work arrangement**: Remote, onsite, hybrid, or any
  - **Job type**: Full-time, part-time, internship, or any
  - **Experience level**: Years of professional experience

This questionnaire data is crucial because it personalizes the entire user experience, especially for job recommendations.

### 1.2 Main Dashboard

Once logged in, users see their **Application Dashboard**, which displays:
- All job applications they've created
- Application status (Preparing, Applied, Interview Prep, Rejected)
- Resume analysis scores for each application
- Quick actions to add new applications or view details

### 1.3 Adding a Job Application

When adding a new job application, users provide:
- Company name
- Job title/role
- Location
- Job description (optional but recommended)
- **Resume upload (mandatory)** - PDF or DOCX format

After submitting, the system automatically analyzes the resume and displays results in an organized, easy-to-understand format.

### 1.4 Displaying Results

The system presents resume analysis results in **expandable tabs**:
- **Overall Score**: A single number (0-100) representing resume quality
- **Format Score**: Structure and organization evaluation
- **Job Compatibility**: How well the resume matches the job description
- **Grammar & Spelling**: Language quality assessment
- **ATS Score**: Applicant Tracking System optimization

Each tab shows:
- A score with visual progress bar
- What was done well (strengths)
- What needs improvement (issues)
- Specific, actionable suggestions for improvement

---

## 2. Resume Analyzer

### 2.1 Overview

The Resume Analyzer is the core feature that automatically evaluates resume quality. It processes uploaded resumes through multiple evaluation modules and provides comprehensive feedback.

### 2.2 How It Works

**Step 1: Text Extraction**
- The system extracts text from PDF or DOCX files
- Uses specialized libraries (PDFPlumber for PDFs, python-docx for Word documents)
- If text extraction is poor, the system can use OCR (Optical Character Recognition) as a fallback

**Step 2: Section Detection**
- The system identifies different resume sections by looking for common headings:
  - Header (name and contact information)
  - Summary or Objective
  - Education
  - Experience
  - Skills
  - Projects (optional)
  - Certifications, Languages, Awards (optional)
- Uses pattern matching and keyword detection to find section boundaries

**Step 3: Structured Parsing**
- Extracts structured information from each section:
  - **Experience**: Company names, job titles, dates, bullet points describing responsibilities
  - **Education**: Degrees, institutions, graduation dates
  - **Skills**: Technical and soft skills listed
  - **Projects**: Project names, descriptions, technologies used

**Step 4: Multi-Dimensional Evaluation**
The system runs five independent evaluation modules:

### 2.3 Format Evaluation

**Purpose**: Assesses resume structure and organization

**What It Checks:**
- **Required sections present**: Header with contact info, Education, Experience, Skills
- **Section ordering**: Compares actual order with recommended order based on career level
  - Entry-level: Header → Summary → Education → Experience → Skills
  - Experienced: Header → Summary → Experience → Skills → Education
- **Page length**: Appropriate length for career level (typically 1 page for entry, 2 for experienced)
- **Bullet consistency**: Similar number of bullet points across experience entries

**Techniques Used:**
- Pattern matching for section detection
- Sequence comparison algorithms for ordering evaluation
- Heuristic rules for format compliance

**Output**: Score (0-100) with specific feedback on what's missing or incorrectly ordered

### 2.4 Grammar & Spelling Evaluation

**Purpose**: Identifies language errors and writing quality issues

**What It Checks:**
- Grammar mistakes (subject-verb agreement, tense consistency, etc.)
- Spelling errors
- Punctuation issues
- Sentence structure problems

**Techniques Used:**
- **LanguageTool**: Open-source grammar and spell checker
- Error counting per 100 words
- Severity weighting for different error types

**Output**: Score (0-100) with examples of errors found and suggested corrections

### 2.5 Job Compatibility Evaluation

**Purpose**: Measures how well the resume matches a specific job description

**What It Checks:**
- **Skill matching**: Extracts required skills from job description and compares with resume skills
- **Semantic similarity**: Uses AI to understand meaning beyond exact keyword matching
- **Coverage ratio**: Percentage of required skills found in resume
- **Missing critical skills**: Identifies important skills mentioned in job description but not in resume

**Techniques Used:**
- **PhraseMatcher**: Exact skill matching using a comprehensive skill vocabulary
- **Semantic Embeddings**: Uses SentenceTransformer (MiniLM model) to create numerical representations of text that capture meaning
- **Cosine Similarity**: Measures how similar the job description and resume are in meaning
- **Skill Extraction**: NLP techniques to identify technical skills, tools, and technologies from text

**Output**: Score (0-100) showing matched skills, missing skills, and how semantically similar the resume is to the job description

**Note**: This evaluation only runs if a job description is provided. If no job description is available, this section is skipped.

### 2.6 ATS (Applicant Tracking System) Score

**Purpose**: Evaluates resume content depth and optimization for automated screening systems

**What It Checks:**
- **Cliché detection**: Identifies overused phrases that don't add value ("team player", "hardworking", "detail-oriented")
- **Action verb quality**: Checks if bullet points start with strong, specific action verbs (e.g., "Developed", "Implemented") rather than weak phrases (e.g., "Responsible for", "Worked on")
- **Quantification**: Evaluates whether achievements include numbers, percentages, or measurable results
  - Especially important when impact verbs (increased, improved, reduced) are used
  - Expects at least 2 out of 3 bullet points to include metrics
- **Skill Demonstrated Index (SDI)**: Measures how well skills are demonstrated across different resume sections
  - Weights skills found in Experience and Projects more heavily than those just listed in Skills section
  - Rewards resumes that show skills in action, not just mention them
- **Experience density**: Checks for sufficient experience entries with proper dates and detailed descriptions
- **Skills coverage**: Counts unique skills and evaluates if the number is appropriate for the role

**Techniques Used:**
- Keyword matching for cliché detection
- Pattern recognition for action verb identification
- Regular expressions for number/metric detection
- Weighted scoring system for skill demonstration across sections
- Heuristic rules for content depth evaluation

**Output**: Score (0-100) with detailed breakdown of what's strong and what needs improvement

### 2.7 Overall Score Calculation

The system combines all evaluation scores using a weighted formula:
- **Format**: 25% weight
- **ATS Content Depth**: 25% weight
- **Job Compatibility**: 25% weight (only if job description provided)
- **Grammar**: 10% weight
- **Skills Coverage**: 15% weight (adjusted if no job description)

The final score is a number between 0 and 100, representing overall resume quality.

---

## 3. Job Recommendation System

### 3.1 Overview

The Job Recommendation System suggests relevant job postings to users based on their profile, preferences, and resume content. It uses AI to understand what jobs match a user's skills and preferences.

### 3.2 How It Works

**Step 1: Building User Profile**
- Combines user's resume text with questionnaire preferences
- Creates a "profile text" that includes:
  - Resume content (skills, experience, education)
  - Desired role preference ("Looking for Software Engineer roles")
  - Industry preference ("Interested in Technology industry")

**Step 2: Creating Semantic Embeddings**
- Uses **SentenceTransformer** (MiniLM model) to convert text into numerical vectors (embeddings)
- These embeddings capture the meaning and context of text, not just keywords
- Both user profile and job descriptions are converted to embeddings

**Step 3: Computing Similarity**
- Calculates **cosine similarity** between user profile embedding and each job posting embedding
- This measures how semantically similar the user is to each job
- Higher similarity = better match

**Step 4: Applying Preference Filters**
The system adjusts similarity scores based on questionnaire preferences:

**Location Filtering:**
- Jobs in user's country or desired countries get full score
- Jobs in other countries get 20% penalty

**Remote Preference:**
- If user wants remote but job is onsite → 30% penalty
- If user wants onsite but job is remote → 30% penalty
- Hybrid preference has no penalty

**Job Type:**
- If job type (full-time, part-time, internship) doesn't match preference → 40% penalty

**Experience Level:**
- Estimates user's seniority from years of experience
- Estimates job's required seniority from title and description
- Major mismatches (senior user + entry job) → 50% penalty
- Minor mismatches → 15% penalty

**Industry Preference:**
- Already captured in semantic embedding, so jobs in preferred industry naturally score higher

**Step 5: Ranking and Returning Results**
- All jobs are sorted by final similarity score (after filters)
- Top N jobs (default: 10) are returned as recommendations
- Each recommendation includes similarity score, job details, and why it was recommended

### 3.3 Techniques Used

- **Semantic Embeddings**: SentenceTransformer model to understand meaning
- **Cosine Similarity**: Mathematical measure of similarity between vectors
- **Rule-Based Filtering**: Preference-based score adjustments
- **Heuristic Matching**: Seniority and job type estimation from text

---

## 4. Interview Preparation

### 4.1 Overview

The Interview Preparation feature uses **OpenAI** and **context from the user’s resume and job description** to generate tailored prep and to evaluate practice answers. It behaves like a professional recruiter and career coach: supportive, direct, and grounded only in the provided documents.

### 4.2 How It Works

**Step 1: Generate Prep (RAG-style context)**
- The system loads the **latest resume text** for the application and the **job description** from the database.
- User chooses preparation **days**, **focus** (technical, behavioral, case, resume), and **difficulty**.
- **Seniority** is inferred from years of experience (&lt;2 = entry, 2–4 = mid, ≥5 = senior).
- Resume and job description are truncated (e.g. 4,000 characters each) to control cost and token usage.
- **OpenAI** (e.g. gpt-4o-mini) is called with this context and returns a **structured prep package** (JSON).

**Step 2: Prep Package Contents**
- **Role context**: Target title, seniority, company, key requirements.
- **Questions**: Technical, behavioral, resume-specific (and optionally case), each with what good looks like, common mistakes, follow-ups, difficulty, and short evidence pointers from the documents.
- **Skill gaps**: Matched skills, missing skills, and priorities to learn.
- **Study plan**: Day-by-day focus, tasks, and deliverable for the chosen number of days.
- **Answer rubric**: Scoring scale (0–5) and criteria (e.g. structure, relevance, evidence, clarity, impact).

**Step 3: Practice and Evaluation**
- User can **type** an answer or **record** a voice answer for any question.
- **Typed answers**: Sent to the evaluate endpoint; OpenAI scores using the rubric and returns strengths, missing points, an improved answer, and a next drill.
- **Voice answers**: Audio is transcribed with **Whisper**, then the transcript is evaluated the same way as a typed answer.
- Scores and feedback are stored per question (**InterviewAnswer** table) and shown in the UI.

### 4.3 Techniques Used

- **Context-grounded generation**: Resume and job description text are the only sources; the model is instructed not to invent company-specific facts and to say when information is missing.
- **OpenAI API**: Chat Completions with JSON output for generation and evaluation; Whisper for speech-to-text.
- **Structured output**: Strict JSON schema for the prep package and for evaluation feedback to keep responses consistent and parseable.
- **Cost control**: Token limits (e.g. max_tokens), truncation of resume/JD, and use of gpt-4o-mini by default.

### 4.4 Configuration

- **Backend**: OpenAI is configured via **backend/.env** (not the project root). Required: `OPENAI_API_KEY`. Optional: `OPENAI_MODEL_GENERATE`, `OPENAI_MODEL_EVAL`, `OPENAI_EMBED_MODEL` (defaults: gpt-4o-mini, text-embedding-3-small).
- **Security**: `.env` is gitignored; the API key is never committed.

---

## 5. System Integration

### 5.1 How Components Work Together

The four main components are integrated to provide a seamless user experience:

1. **User completes questionnaire** → Data stored for personalization
2. **User adds job application** → Resume uploaded and analyzed
3. **Resume Analyzer evaluates** → Scores and feedback displayed
4. **User views recommendations** → System suggests matching jobs using questionnaire data and resume
5. **User prepares for interview** → System generates tailored prep from resume + JD, then user practices with typed or voice answers and receives scored feedback

### 5.2 Data Flow

```
User Registration
    ↓
Questionnaire Completion → Stored in User Profile
    ↓
Add Job Application + Upload Resume
    ↓
Resume Analyzer Processes → Scores Generated
    ↓
Results Displayed to User
    ↓
[Optional] View Job Recommendations → Uses Profile + Resume
    ↓
[Optional] Generate Interview Prep → Uses resume + job description; user practices and gets evaluated feedback
```

---

## 6. Key Technologies Used

### 6.1 Natural Language Processing (NLP)
- **spaCy**: Text processing, part-of-speech tagging, named entity recognition
- **PhraseMatcher**: Efficient keyword and skill matching
- **LanguageTool**: Grammar and spell checking

### 6.2 Machine Learning
- **SentenceTransformer (MiniLM)**: Semantic embeddings for understanding text meaning
- **Cosine Similarity**: Measuring similarity between text representations
- **scikit-learn**: Machine learning utilities

### 6.3 Document Processing
- **PDFPlumber**: PDF text extraction
- **python-docx**: Word document processing
- **PyTesseract**: OCR for image-based documents

### 6.4 Web Technologies
- **FastAPI**: Backend API framework
- **React + TypeScript**: Frontend user interface
- **PostgreSQL**: Database for storing user data and applications

### 6.5 Interview Prep (OpenAI)
- **OpenAI API**: Chat Completions for prep generation and answer evaluation; Whisper for voice transcription
- **Structured JSON**: Prep package (role_context, questions, skill_gaps, study_plan, answer_rubric) and evaluation feedback (score, strengths, missing_points, improved_answer, next_drill)
- **Context only**: Resume and job description text from the database; no internal tools or RAG systems exposed to the user

---

## 7. Summary

This system provides job seekers with:

1. **Automated Resume Evaluation**: Comprehensive, objective feedback on resume quality across multiple dimensions
2. **Personalized Job Matching**: AI-powered recommendations based on skills, preferences, and resume content
3. **Targeted Interview Preparation**: Role-specific questions and study materials
4. **Centralized Application Tracking**: Single platform to manage all job applications and resume versions

The system uses a combination of rule-based evaluation, natural language processing, and machine learning to provide intelligent, actionable feedback that helps users improve their resumes and succeed in their job search.

---

*This document provides a high-level overview. For detailed technical specifications and implementation details, refer to the comprehensive METHODOLOGY.md document.*

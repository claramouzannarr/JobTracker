import re
import language_tool_python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import Dict, List, Any, Optional
from app.services.skill_extraction import extract_skills, extract_skills_from_job_description, compute_skill_gaps, compute_skill_coverage
from app.services.resume_parser import parse_resume

# Initialize models
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    embedding_model = None
    print(f"Warning: Could not load embedding model: {e}")

try:
    grammar_tool = language_tool_python.LanguageTool('en-US')
except Exception as e:
    grammar_tool = None
    print(f"Warning: Could not load LanguageTool: {e}")

# Cliché phrases to detect
CLICHE_PHRASES = [
    "hardworking", "team player", "responsible for", "worked on",
    "detail oriented", "detail-oriented", "detail oriented person",
    "self motivated", "self-motivated", "quick learner",
    "think outside the box", "go-getter", "results driven",
    "results-driven", "proven track record", "excellent communication skills",
    "strong work ethic", "ability to work", "good at",
]

# Strong action verbs
ACTION_VERBS = [
    "led", "built", "designed", "optimized", "implemented", "developed",
    "created", "improved", "increased", "decreased", "reduced", "achieved",
    "managed", "delivered", "launched", "established", "executed", "transformed",
    "architected", "engineered", "automated", "streamlined", "enhanced",
    "scaled", "deployed", "integrated", "collaborated", "mentored", "trained",
]


def evaluate_job_compatibility(resume_text: str, job_description: Optional[str] = None) -> float:
    """Evaluate job compatibility using embedding similarity."""
    if not job_description or embedding_model is None:
        return 0.5  # Default score if no JD or model
    
    try:
        resume_embedding = embedding_model.encode([resume_text])
        jd_embedding = embedding_model.encode([job_description])
        similarity = cosine_similarity(resume_embedding, jd_embedding)[0][0]
        return float(similarity)
    except Exception as e:
        print(f"Error computing job compatibility: {e}")
        return 0.5


def evaluate_skills_coverage(resume_text: str, job_description: Optional[str] = None) -> Dict[str, Any]:
    """Evaluate skills coverage and gaps."""
    resume_skills = extract_skills(resume_text)
    
    if not job_description:
        return {
            "score": 0.5,
            "resume_skills": list(resume_skills),
            "job_skills": [],
            "gaps": [],
        }
    
    job_skills = extract_skills_from_job_description(job_description)
    coverage = compute_skill_coverage(resume_skills, job_skills)
    gaps = compute_skill_gaps(resume_skills, job_skills)
    
    return {
        "score": coverage,
        "resume_skills": list(resume_skills),
        "job_skills": list(job_skills),
        "gaps": list(gaps),
    }


def evaluate_grammar(resume_text: str) -> Dict[str, Any]:
    """Evaluate grammar and spelling using LanguageTool."""
    if grammar_tool is None:
        return {
            "score": 0.5,
            "error_count": 0,
            "errors": [],
        }
    
    try:
        errors = grammar_tool.check(resume_text)
        error_count = len(errors)
        
        # Score: fewer errors = higher score
        # Normalize: assume max 20 errors for a resume = 0 score
        max_errors = 20
        score = max(0, 1 - (error_count / max_errors))
        
        error_details = []
        for error in errors[:10]:  # Limit to first 10 errors
            error_details.append({
                "message": error.message,
                "context": error.context,
                "offset": error.offset,
                "length": error.errorLength,
            })
        
        return {
            "score": score,
            "error_count": error_count,
            "errors": error_details,
        }
    except Exception as e:
        print(f"Error in grammar checking: {e}")
        return {
            "score": 0.5,
            "error_count": 0,
            "errors": [],
        }


def evaluate_template_quality(resume_text: str, sections: Dict[str, str]) -> float:
    """Evaluate template/structure quality using rule-based checks."""
    score = 0.0
    max_score = 0.0
    
    # Check for required sections (40 points)
    required_sections = ["experience", "education", "skills"]
    max_score += 40
    found_sections = 0
    for section in required_sections:
        if any(req in key.lower() for key in sections.keys()):
            found_sections += 1
    score += (found_sections / len(required_sections)) * 40
    
    # Check text density (20 points)
    max_score += 20
    lines = resume_text.split("\n")
    avg_line_length = sum(len(line) for line in lines) / len(lines) if lines else 0
    if 40 <= avg_line_length <= 80:  # Good line length
        score += 20
    elif 30 <= avg_line_length < 40 or 80 < avg_line_length <= 100:
        score += 10
    
    # Check for bullet points (20 points)
    max_score += 20
    bullet_count = resume_text.count("•") + resume_text.count("-") + resume_text.count("*")
    if bullet_count >= 5:
        score += 20
    elif bullet_count >= 3:
        score += 10
    
    # Check length (20 points) - not too short, not too long
    max_score += 20
    word_count = len(resume_text.split())
    if 200 <= word_count <= 500:  # Good length
        score += 20
    elif 100 <= word_count < 200 or 500 < word_count <= 800:
        score += 10
    
    return score / max_score if max_score > 0 else 0.5


def evaluate_bullet_quality(resume_text: str) -> Dict[str, Any]:
    """Evaluate quality of bullet points."""
    # Extract bullet points
    bullets = []
    lines = resume_text.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("•", "-", "*")) or re.match(r"^\d+\.", stripped):
            bullets.append(stripped)
    
    if not bullets:
        return {
            "score": 0.3,
            "total_bullets": 0,
            "strong_bullets": 0,
        }
    
    strong_bullets = 0
    for bullet in bullets:
        bullet_score = 0
        
        # Check for action verb at start
        first_words = bullet.split()[:2]
        if any(verb.lower() in " ".join(first_words).lower() for verb in ACTION_VERBS):
            bullet_score += 1
        
        # Check for numbers/KPIs
        if re.search(r'\d+', bullet):
            bullet_score += 1
        
        # Check length (at least 8 words)
        if len(bullet.split()) >= 8:
            bullet_score += 1
        
        if bullet_score >= 2:
            strong_bullets += 1
    
    score = strong_bullets / len(bullets) if bullets else 0
    
    return {
        "score": score,
        "total_bullets": len(bullets),
        "strong_bullets": strong_bullets,
    }


def detect_cliches(resume_text: str) -> Dict[str, Any]:
    """Detect cliché phrases and weak language."""
    found_cliches = []
    text_lower = resume_text.lower()
    
    for cliche in CLICHE_PHRASES:
        if cliche.lower() in text_lower:
            found_cliches.append(cliche)
    
    # Penalty: more clichés = lower score
    penalty = min(1.0, len(found_cliches) * 0.1)  # 0.1 penalty per cliché, max 1.0
    score = max(0, 1.0 - penalty)
    
    return {
        "score": score,
        "cliches_found": found_cliches,
        "count": len(found_cliches),
    }


def evaluate_resume(resume_text: str, job_description: Optional[str] = None) -> Dict[str, Any]:
    """Main function to evaluate resume across all dimensions."""
    parsed = parse_resume(resume_text)
    sections = parsed.get("sections", {})
    
    # Run all evaluations
    job_compat = evaluate_job_compatibility(resume_text, job_description)
    skills_eval = evaluate_skills_coverage(resume_text, job_description)
    grammar_eval = evaluate_grammar(resume_text)
    template_eval = evaluate_template_quality(resume_text, sections)
    bullet_eval = evaluate_bullet_quality(resume_text)
    cliche_eval = detect_cliches(resume_text)
    
    # Compute overall score with weights
    weights = {
        "job_compatibility": 0.30,
        "bullet_quality": 0.25,
        "skills_coverage": 0.15,
        "grammar": 0.15,
        "template_quality": 0.10,
        "cliche_penalty": 0.05,
    }
    
    overall_score = (
        weights["job_compatibility"] * job_compat +
        weights["bullet_quality"] * bullet_eval["score"] +
        weights["skills_coverage"] * skills_eval["score"] +
        weights["grammar"] * grammar_eval["score"] +
        weights["template_quality"] * template_eval +
        weights["cliche_penalty"] * cliche_eval["score"]
    )
    
    return {
        "job_compatibility": job_compat,
        "skills_coverage": skills_eval["score"],
        "skill_gaps": skills_eval["gaps"],
        "resume_skills": skills_eval["resume_skills"],
        "grammar_score": grammar_eval["score"],
        "grammar_errors": grammar_eval["errors"],
        "template_quality": template_eval,
        "bullet_quality": bullet_eval["score"],
        "bullet_stats": {
            "total": bullet_eval["total_bullets"],
            "strong": bullet_eval["strong_bullets"],
        },
        "cliche_score": cliche_eval["score"],
        "cliches_found": cliche_eval["cliches_found"],
        "overall_score": overall_score,
    }


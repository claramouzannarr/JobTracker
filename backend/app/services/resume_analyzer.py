"""
Comprehensive Resume Analyzer Pipeline
Implements all evaluation modules according to spec.
"""
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import language_tool_python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

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

# Configuration constants
MIN_TEXT_LENGTH = 100  # Minimum characters for valid extraction
MAX_PAGES_GRAD = 1
MAX_PAGES_EXPERIENCED = 2

# Cliché phrases
CLICHE_PHRASES = [
    "hardworking", "team player", "responsible for", "worked on",
    "detail oriented", "detail-oriented", "detail oriented person",
    "self motivated", "self-motivated", "quick learner",
    "think outside the box", "go-getter", "results driven",
    "results-driven", "proven track record", "excellent communication skills",
    "strong work ethic", "ability to work", "good at",
    "duties included", "helped with", "assisted in"
]

# Strong action verbs
STRONG_ACTION_VERBS = [
    "led", "built", "designed", "optimized", "implemented", "developed",
    "created", "improved", "increased", "decreased", "reduced", "achieved",
    "managed", "delivered", "launched", "established", "executed", "transformed",
    "architected", "engineered", "automated", "streamlined", "enhanced",
    "scaled", "deployed", "integrated", "collaborated", "mentored", "trained",
    "boosted", "strengthened", "accelerated", "maximized", "minimized"
]

# Weak action verbs (penalty)
WEAK_ACTION_VERBS = [
    "responsible for", "worked on", "helped", "assisted", "involved in",
    "participated in", "contributed to", "exposed to"
]

# Impact verbs that should have numbers
IMPACT_VERBS = [
    "increased", "improved", "reduced", "boosted", "strengthened",
    "optimized", "accelerated", "maximized", "minimized", "decreased",
    "enhanced", "scaled", "grew", "expanded", "cut", "saved"
]

# Skill aliases for normalization
SKILL_ALIASES = {
    "microsoft 365": ["microsoft365", "office 365", "ms 365", "m365"],
    "sql": ["structured query language"],
    "aws": ["amazon web services"],
    "api": ["application programming interface", "apis"],
    "ui/ux": ["user interface", "user experience", "ui", "ux"],
}


def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, remove punctuation, collapse whitespace)."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_skill(skill: str) -> str:
    """Normalize skill name using aliases."""
    normalized = normalize_text(skill)
    for canonical, aliases in SKILL_ALIASES.items():
        if normalized == canonical or normalized in [normalize_text(a) for a in aliases]:
            return canonical
    return normalized


def extract_resume_sections(raw_text: str) -> Dict[str, Any]:
    """
    Extract and normalize resume sections.
    Returns structured sections with parsed content.
    """
    sections = {
        "Header": {"lines": [], "emails": [], "phones": [], "links": []},
        "Summary": {"text": ""},
        "Education": {"items": []},
        "Experience": {"items": []},
        "Skills": {"skills_text": "", "skills_list": []},
        "Projects": {"items": []},
        "Other": {"items": []}
    }
    
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    current_section = "Other"
    current_content = []
    
    # Section heading patterns
    section_patterns = {
        r"^(summary|professional\s+summary|objective|profile|about)$": "Summary",
        r"^(education|academic\s+background|academics)$": "Education",
        r"^(experience|work\s+experience|employment|professional\s+experience|work\s+history)$": "Experience",
        r"^(skills|technical\s+skills|core\s+competencies|key\s+skills)$": "Skills",
        r"^(projects|project\s+experience|selected\s+projects)$": "Projects",
    }
    
    # Extract header info (first few lines)
    header_lines = lines[:5]
    for line in header_lines:
        # Extract emails
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line)
        sections["Header"]["emails"].extend(emails)
        
        # Extract phones
        phones = re.findall(r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}', line)
        sections["Header"]["phones"].extend(phones)
        
        # Extract links
        links = re.findall(r'https?://[^\s]+|www\.[^\s]+|linkedin\.com/[^\s]+|github\.com/[^\s]+', line)
        sections["Header"]["links"].extend(links)
        
        sections["Header"]["lines"].append(line)
    
    # Parse sections
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        is_heading = False
        
        for pattern, section_name in section_patterns.items():
            if re.match(pattern, line_lower):
                # Save previous section
                if current_section != "Other" and current_content:
                    sections[current_section]["text"] = "\n".join(current_content)
                
                current_section = section_name
                current_content = []
                is_heading = True
                break
        
        if not is_heading:
            current_content.append(line)
    
    # Save last section
    if current_content:
        sections[current_section]["text"] = "\n".join(current_content)
    
    # Parse Experience items (look for company/role patterns)
    experience_text = sections["Experience"]["text"]
    if experience_text:
        # Simple parsing: look for company names (all caps or title case) followed by dates
        exp_items = []
        exp_lines = experience_text.split('\n')
        current_item = {"company": "", "role": "", "bullets": [], "dates": ""}
        
        for line in exp_lines:
            # Check for date pattern
            if re.search(r'\d{4}', line):
                if current_item["company"]:
                    exp_items.append(current_item)
                current_item = {"company": "", "role": "", "bullets": [], "dates": ""}
                current_item["dates"] = line
            
            # Check for bullet
            elif line.strip().startswith(('•', '-', '*')) or re.match(r'^\d+\.', line.strip()):
                current_item["bullets"].append(line.strip())
            # Assume company/role line (title case or all caps)
            elif line.strip() and not current_item["company"]:
                parts = line.split('|')
                if len(parts) >= 2:
                    current_item["company"] = parts[0].strip()
                    current_item["role"] = parts[1].strip()
                else:
                    current_item["company"] = line.strip()
        
        if current_item["company"]:
            exp_items.append(current_item)
        
        sections["Experience"]["items"] = exp_items
    
    # Parse Skills list
    skills_text = sections["Skills"]["text"]
    if skills_text:
        # Extract skills (comma-separated, bullet points, or line-separated)
        skills_list = []
        for line in skills_text.split('\n'):
            if ',' in line:
                skills_list.extend([s.strip() for s in line.split(',')])
            elif line.strip().startswith(('•', '-', '*')):
                skills_list.append(line.strip().lstrip('•-* ').strip())
            elif line.strip():
                skills_list.append(line.strip())
        sections["Skills"]["skills_list"] = [s for s in skills_list if s]
        sections["Skills"]["skills_text"] = skills_text
    
    return sections


def evaluate_format_score(sections: Dict[str, Any], career_level: str = "experienced", page_count: int = 1) -> Dict[str, Any]:
    """
    Evaluate format/structure score.
    Checks: required sections, ordering, page count, bullet consistency.
    """
    score = 0.0
    max_score = 100.0
    issues = []
    strengths = []
    details = {}
    
    # 1. Required sections check (30 points)
    required_sections = ["Header", "Experience", "Education", "Skills"]
    found_sections = []
    section_details = {}
    
    for section in required_sections:
        section_data = sections.get(section, {})
        is_present = False
        
        if section == "Header":
            has_email = bool(section_data.get("emails"))
            has_phone = bool(section_data.get("phones"))
            has_links = bool(section_data.get("links"))
            is_present = has_email or has_phone or has_links
            section_details[section] = {
                "present": is_present,
                "has_email": has_email,
                "has_phone": has_phone,
                "has_links": has_links
            }
        elif section == "Skills":
            has_list = bool(section_data.get("skills_list"))
            has_text = bool(section_data.get("skills_text"))
            is_present = has_list or has_text
            skills_count = len(section_data.get("skills_list", []))
            section_details[section] = {
                "present": is_present,
                "skills_count": skills_count,
                "has_list": has_list
            }
        else:
            has_text = bool(section_data.get("text"))
            has_items = bool(section_data.get("items"))
            is_present = has_text or has_items
            items_count = len(section_data.get("items", []))
            section_details[section] = {
                "present": is_present,
                "has_text": has_text,
                "items_count": items_count
            }
        
        if is_present:
            found_sections.append(section)
            strengths.append(f"✓ {section} section found")
        else:
            issues.append(f"Missing {section} section")
    
    section_score = (len(found_sections) / len(required_sections)) * 30
    score += section_score
    missing_sections = [s for s in required_sections if s not in found_sections]
    
    details["sections"] = {
        "found": found_sections,
        "missing": missing_sections,
        "section_details": section_details,
        "score_breakdown": f"{len(found_sections)}/{len(required_sections)} sections found ({section_score:.1f}/30 points)"
    }
    
    # 2. Section ordering (20 points)
    ordering_ok = True
    if career_level == "grad":
        # Recommended: Header → Summary → Education → Experience → Skills
        recommended_order = ["Header", "Summary", "Education", "Experience", "Skills"]
    else:
        # Recommended: Header → Summary → Experience → Skills → Education
        recommended_order = ["Header", "Summary", "Experience", "Skills", "Education"]
    
    # Check if sections appear in reasonable order (simplified check)
    found_order = [s for s in recommended_order if s in found_sections]
    ordering_match = len(found_order) / len(found_sections) if found_sections else 0
    
    if ordering_match >= 0.8:  # 80% match
        score += 20
        strengths.append("✓ Sections are well-ordered")
    else:
        ordering_ok = False
        issues.append(f"Section ordering doesn't match recommended order for {career_level} level")
        score += 10
    
    details["ordering"] = {
        "recommended_order": recommended_order,
        "actual_order": found_sections,
        "match_percentage": ordering_match * 100,
        "score_breakdown": f"{ordering_match * 100:.0f}% match with recommended order ({20 if ordering_ok else 10}/20 points)"
    }
    
    # 3. Page count check (20 points)
    max_pages = MAX_PAGES_GRAD if career_level == "grad" else MAX_PAGES_EXPERIENCED
    if page_count <= max_pages:
        score += 20
        strengths.append(f"✓ Page count ({page_count}) is appropriate")
    elif page_count <= max_pages + 1:
        score += 10
        issues.append(f"Resume is {page_count} pages (recommended: {max_pages} for {career_level})")
    else:
        issues.append(f"Resume is too long ({page_count} pages, recommended: {max_pages})")
    
    details["page_count"] = {
        "current": page_count,
        "recommended": max_pages,
        "career_level": career_level,
        "score_breakdown": f"{page_count} pages ({20 if page_count <= max_pages else 10 if page_count <= max_pages + 1 else 0}/20 points)"
    }
    
    # 4. Bullet consistency (30 points)
    experience_items = sections.get("Experience", {}).get("items", [])
    max_bullets = 0
    min_bullets = 0
    total_bullets = 0
    
    if experience_items:
        bullet_counts = [len(item.get("bullets", [])) for item in experience_items]
        if bullet_counts:
            max_bullets = max(bullet_counts)
            min_bullets = min(bullet_counts)
            total_bullets = sum(bullet_counts)
            diff = max_bullets - min_bullets
            
            if diff <= 2:
                score += 30
                strengths.append(f"✓ Consistent bullet points across {len(experience_items)} experience entries")
            elif diff <= 4:
                score += 20
                issues.append(f"Bullet point counts vary: {min_bullets}-{max_bullets} per entry")
            else:
                score += 10
                issues.append(f"Inconsistent bullets: counts range from {min_bullets} to {max_bullets}")
            
            details["bullets"] = {
                "total_experience_items": len(experience_items),
                "total_bullets": total_bullets,
                "average_per_item": round(total_bullets / len(experience_items), 1),
                "min_bullets": min_bullets,
                "max_bullets": max_bullets,
                "consistency_diff": diff,
                "score_breakdown": f"{diff} bullet difference ({30 if diff <= 2 else 20 if diff <= 4 else 10}/30 points)"
            }
    else:
        issues.append("No experience items found with bullet points")
        details["bullets"] = {
            "total_experience_items": 0,
            "total_bullets": 0,
            "score_breakdown": "No experience items found (0/30 points)"
        }
    
    return {
        "score": min(100, max(0, score)),
        "missing_sections": missing_sections,
        "ordering_ok": ordering_ok,
        "page_count": page_count,
        "issues": issues,
        "strengths": strengths,
        "details": details,
        "bullet_consistency": {
            "experience_max_diff": max_bullets - min_bullets if experience_items else 0,
            "penalty": max(0, 30 - (score % 30))
        } if experience_items else {}
    }


def evaluate_grammar_score(raw_text: str, sections: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate grammar and spelling using LanguageTool.
    Runs on bullets and summary sentences.
    """
    if grammar_tool is None:
        return {
            "score": 50.0,
            "errors_per_100_words": 0,
            "top_examples": [],
            "error_count": 0
        }
    
    # Extract text to check: summary + bullets
    text_to_check = []
    
    # Add summary
    summary_text = sections.get("Summary", {}).get("text", "")
    if summary_text:
        text_to_check.append(summary_text)
    
    # Add all bullets from experience
    experience_items = sections.get("Experience", {}).get("items", [])
    for item in experience_items:
        text_to_check.extend(item.get("bullets", []))
    
    combined_text = "\n".join(text_to_check)
    if not combined_text:
        combined_text = raw_text[:1000]  # Fallback to first 1000 chars
    
    try:
        errors = grammar_tool.check(combined_text)
        error_count = len(errors)
        word_count = len(combined_text.split())
        errors_per_100_words = (error_count / word_count * 100) if word_count > 0 else 0
        
        # Score: start at 100, subtract penalty
        score = max(0, 100 - min(40, errors_per_100_words * 2))
        
        # Get top examples
        top_examples = []
        for error in errors[:5]:
            top_examples.append({
                "text": error.context[:100] if error.context else "",
                "issue": error.message,
                "suggestion": error.replacements[0] if error.replacements else ""
            })
        
        return {
            "score": score,
            "errors_per_100_words": round(errors_per_100_words, 2),
            "top_examples": top_examples,
            "error_count": error_count
        }
    except Exception as e:
        print(f"Error in grammar checking: {e}")
        return {
            "score": 50.0,
            "errors_per_100_words": 0,
            "top_examples": [],
            "error_count": 0
        }


def extract_job_keywords(job_description: str) -> Dict[str, List[str]]:
    """
    Extract keywords from job description.
    Returns: required_keywords, optional_keywords
    """
    if not job_description:
        return {"required": [], "optional": []}
    
    # Normalize JD text
    jd_lower = job_description.lower()
    
    # Extract technical skills/tools (common patterns)
    tech_patterns = [
        r'\b(aws|azure|gcp|kubernetes|docker|jenkins|git|github|gitlab)\b',
        r'\b(python|java|javascript|typescript|react|vue|angular|node\.?js|sql|nosql|mongodb|postgresql|mysql)\b',
        r'\b(microsoft\s+365|office\s+365|excel|powerpoint|word|outlook)\b',
        r'\b(tableau|power\s+bi|looker|qlik|snowflake|redshift|bigquery)\b',
        r'\b(machine\s+learning|ml|artificial\s+intelligence|ai|deep\s+learning|nlp)\b',
        r'\b(agile|scrum|kanban|ci/cd|devops|microservices)\b',
    ]
    
    required_keywords = []
    optional_keywords = []
    
    # Extract using patterns
    for pattern in tech_patterns:
        matches = re.findall(pattern, jd_lower, re.IGNORECASE)
        required_keywords.extend([normalize_skill(m) for m in matches])
    
    # Also extract noun phrases (simplified)
    # Look for capitalized terms that might be tools/technologies
    capitalized_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', job_description)
    optional_keywords.extend([normalize_skill(t.lower()) for t in capitalized_terms[:20]])
    
    return {
        "required": list(set(required_keywords)),
        "optional": list(set(optional_keywords))[:30]
    }


def evaluate_job_compatibility(resume_text: str, job_description: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluate job compatibility using keyword matching + embeddings.
    """
    if not job_description:
        return {
            "score": 0.0,
            "required_keywords": [],
            "matched_required": [],
            "missing_required": [],
            "soft_similarity": 0.0
        }
    
    # Extract keywords from JD
    jd_keywords = extract_job_keywords(job_description)
    required_keywords = jd_keywords["required"]
    
    if not required_keywords:
        # Fallback: use embedding similarity only
        if embedding_model:
            try:
                resume_emb = embedding_model.encode([resume_text])
                jd_emb = embedding_model.encode([job_description])
                similarity = float(cosine_similarity(resume_emb, jd_emb)[0][0])
                return {
                    "score": similarity * 100,
                    "required_keywords": [],
                    "matched_required": [],
                    "missing_required": [],
                    "soft_similarity": similarity
                }
            except Exception as e:
                print(f"Error computing embeddings: {e}")
    
    # Normalize resume text
    resume_normalized = normalize_text(resume_text)
    
    # Match keywords
    matched_required = []
    for keyword in required_keywords:
        keyword_normalized = normalize_skill(keyword)
        if keyword_normalized in resume_normalized:
            matched_required.append(keyword)
    
    missing_required = [k for k in required_keywords if k not in matched_required]
    
    # Compute coverage
    coverage = len(matched_required) / len(required_keywords) if required_keywords else 0.0
    
    # Compute embedding similarity (soft match)
    soft_similarity = 0.0
    if embedding_model:
        try:
            resume_emb = embedding_model.encode([resume_text])
            jd_emb = embedding_model.encode([job_description])
            soft_similarity = float(cosine_similarity(resume_emb, jd_emb)[0][0])
        except Exception as e:
            print(f"Error computing embeddings: {e}")
    
    # Combined score: 70% keyword coverage, 30% embedding similarity
    score = (coverage * 70) + (soft_similarity * 30)
    
    return {
        "score": min(100, max(0, score)),
        "required_keywords": required_keywords,
        "matched_required": matched_required,
        "missing_required": missing_required,
        "soft_similarity": round(soft_similarity, 3)
    }


def evaluate_ats_score(raw_text: str, sections: Dict[str, Any], job_description: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluate ATS content depth score.
    Checks: clichés, action verbs, KPIs/quantification, skills coverage, experience density.
    """
    score = 0.0
    max_score = 100.0
    issues = []
    strengths = []
    details = {}
    
    # 1. Cliché penalty (20 points)
    text_lower = raw_text.lower()
    cliches_found = []
    for cliche in CLICHE_PHRASES:
        if cliche.lower() in text_lower:
            cliches_found.append(cliche)
    
    cliche_penalty = min(20, len(cliches_found) * 3)
    cliche_score = max(0, 20 - cliche_penalty)
    score += cliche_score
    
    if cliches_found:
        issues.append(f"Found {len(cliches_found)} cliché phrase(s)")
        details["cliches"] = {
            "found": cliches_found,
            "count": len(cliches_found),
            "score_breakdown": f"{len(cliches_found)} clichés found ({cliche_score}/20 points)"
        }
    else:
        strengths.append("✓ No clichés detected - using original language")
        details["cliches"] = {
            "found": [],
            "count": 0,
            "score_breakdown": "No clichés found (20/20 points)"
        }
    
    # 2. Action verb quality (20 points)
    experience_items = sections.get("Experience", {}).get("items", [])
    strong_verb_count = 0
    weak_verb_count = 0
    total_bullets = 0
    strong_verbs_found = []
    weak_verbs_found = []
    
    for item in experience_items:
        bullets = item.get("bullets", [])
        total_bullets += len(bullets)
        for bullet in bullets:
            first_words = " ".join(bullet.split()[:3]).lower()
            found_strong = [v for v in STRONG_ACTION_VERBS if v in first_words]
            found_weak = [v for v in WEAK_ACTION_VERBS if v in first_words]
            
            if found_strong:
                strong_verb_count += 1
                strong_verbs_found.extend(found_strong[:1])  # Track first occurrence
            elif found_weak:
                weak_verb_count += 1
                weak_verbs_found.extend(found_weak[:1])
    
    if total_bullets > 0:
        strong_ratio = strong_verb_count / total_bullets
        weak_ratio = weak_verb_count / total_bullets
        verb_score = (strong_ratio * 20) - (weak_ratio * 10)
        score += max(0, verb_score)
        
        if strong_ratio >= 0.5:
            strengths.append(f"✓ {int(strong_ratio * 100)}% of bullets start with strong action verbs")
        else:
            issues.append(f"Only {int(strong_ratio * 100)}% of bullets use strong action verbs (target: 50%+)")
        
        details["action_verbs"] = {
            "total_bullets": total_bullets,
            "strong_verbs": strong_verb_count,
            "weak_verbs": weak_verb_count,
            "strong_ratio": round(strong_ratio, 2),
            "weak_ratio": round(weak_ratio, 2),
            "examples_strong": list(set(strong_verbs_found))[:5],
            "examples_weak": list(set(weak_verbs_found))[:3],
            "score_breakdown": f"{int(strong_ratio * 100)}% strong verbs ({max(0, verb_score):.1f}/20 points)"
        }
    else:
        issues.append("No bullet points found in experience")
        details["action_verbs"] = {
            "total_bullets": 0,
            "score_breakdown": "No bullets found (0/20 points)"
        }
    
    # 3. KPI and quantification (30 points)
    impact_verb_without_number = []
    bullets_with_numbers = 0
    bullets_with_percentages = 0
    bullets_with_currency = 0
    
    for item in experience_items:
        bullets = item.get("bullets", [])
        for bullet in bullets:
            # Check for numbers (digits, %, $, etc.)
            has_number = bool(re.search(r'\d+|%|\$|€|k\b|m\b|bn\b', bullet, re.IGNORECASE))
            if has_number:
                bullets_with_numbers += 1
                if '%' in bullet:
                    bullets_with_percentages += 1
                if re.search(r'\$|€|£', bullet):
                    bullets_with_currency += 1
            
            # Check for impact verbs without numbers
            first_words = " ".join(bullet.split()[:3]).lower()
            if any(verb in first_words for verb in IMPACT_VERBS) and not has_number:
                impact_verb_without_number.append(bullet[:80])
    
    if total_bullets > 0:
        kpi_ratio = bullets_with_numbers / total_bullets
        expected_ratio = 0.66  # 2 out of 3 should have numbers
        if kpi_ratio >= expected_ratio:
            score += 30
            strengths.append(f"✓ {int(kpi_ratio * 100)}% of bullets include quantifiable metrics")
        elif kpi_ratio >= 0.5:
            score += 20
            issues.append(f"Only {int(kpi_ratio * 100)}% of bullets have numbers (target: 66%+)")
        else:
            score += 10
            issues.append(f"Low quantification: only {int(kpi_ratio * 100)}% of bullets have numbers")
        
        details["quantification"] = {
            "total_bullets": total_bullets,
            "bullets_with_numbers": bullets_with_numbers,
            "bullets_with_percentages": bullets_with_percentages,
            "bullets_with_currency": bullets_with_currency,
            "kpi_ratio": round(kpi_ratio, 2),
            "expected_ratio": expected_ratio,
            "impact_verbs_without_numbers": impact_verb_without_number[:5],
            "score_breakdown": f"{int(kpi_ratio * 100)}% quantified ({30 if kpi_ratio >= expected_ratio else 20 if kpi_ratio >= 0.5 else 10}/30 points)"
        }
    else:
        details["quantification"] = {
            "total_bullets": 0,
            "score_breakdown": "No bullets found (0/30 points)"
        }
    
    if impact_verb_without_number:
        issues.append(f"{len(impact_verb_without_number)} impact verbs missing numbers")
    
    # 4. Skills coverage (15 points)
    skills_list = sections.get("Skills", {}).get("skills_list", [])
    skills_count = len(skills_list)
    
    # Compare to JD if available
    if job_description:
        jd_keywords = extract_job_keywords(job_description)
        jd_skills = set(jd_keywords["required"] + jd_keywords["optional"][:10])
        resume_skills_set = set([normalize_skill(s) for s in skills_list])
        matched_skills = jd_skills & resume_skills_set
        coverage = len(matched_skills) / len(jd_skills) if jd_skills else 0
        skills_score = coverage * 15
        
        if coverage >= 0.5:
            strengths.append(f"✓ {int(coverage * 100)}% of job-required skills are present")
        else:
            issues.append(f"Only {int(coverage * 100)}% of job-required skills matched")
        
        details["skills"] = {
            "resume_skills_count": skills_count,
            "job_required_skills": len(jd_skills),
            "matched_skills": list(matched_skills)[:10],
            "missing_skills": list(jd_skills - resume_skills_set)[:10],
            "coverage": round(coverage, 2),
            "score_breakdown": f"{int(coverage * 100)}% match ({skills_score:.1f}/15 points)"
        }
    else:
        # Base score on count
        if skills_count >= 10:
            skills_score = 15
            strengths.append(f"✓ Comprehensive skills list ({skills_count} skills)")
        elif skills_count >= 5:
            skills_score = 10
            issues.append(f"Consider adding more skills (currently {skills_count})")
        else:
            skills_score = 5
            issues.append(f"Limited skills listed ({skills_count})")
        
        details["skills"] = {
            "resume_skills_count": skills_count,
            "score_breakdown": f"{skills_count} skills listed ({skills_score}/15 points)"
        }
    
    score += skills_score
    
    # 5. Experience density (15 points)
    experience_count = len(experience_items)
    if experience_count >= 3:
        score += 15
        strengths.append(f"✓ Strong experience depth ({experience_count} entries)")
    elif experience_count >= 2:
        score += 10
        issues.append(f"Consider adding more experience entries (currently {experience_count})")
    elif experience_count >= 1:
        score += 5
        issues.append(f"Limited experience entries ({experience_count})")
    else:
        issues.append("No experience items found")
    
    # Check for dates
    dates_found = bool(re.search(r'\d{4}', raw_text))
    if dates_found:
        strengths.append("✓ Dates found in experience")
    else:
        issues.append("No dates found in experience")
        score -= 5
    
    details["experience"] = {
        "experience_count": experience_count,
        "has_dates": dates_found,
        "score_breakdown": f"{experience_count} entries, dates: {'yes' if dates_found else 'no'} ({15 if experience_count >= 3 else 10 if experience_count >= 2 else 5 if experience_count >= 1 else 0}/15 points)"
    }
    
    return {
        "score": min(100, max(0, score)),
        "cliches_found": cliches_found,
        "kpi_ratio": {
            "latest_role": kpi_ratio if total_bullets > 0 else 0,
            "expected": 0.66
        },
        "impact_verb_without_number": impact_verb_without_number[:5],
        "skills_count": skills_count,
        "experience_items": experience_count,
        "issues": issues,
        "strengths": strengths,
        "details": details
    }


def analyze_resume(
    raw_text: str,
    job_description: Optional[str] = None,
    career_level: str = "experienced",
    page_count: int = 1
) -> Dict[str, Any]:
    """
    Main function: comprehensive resume analysis pipeline.
    Returns complete evaluation with all module scores.
    """
    # Extract sections
    sections = extract_resume_sections(raw_text)
    
    # Run all evaluation modules
    format_eval = evaluate_format_score(sections, career_level, page_count)
    grammar_eval = evaluate_grammar_score(raw_text, sections)
    job_compat_eval = evaluate_job_compatibility(raw_text, job_description)
    ats_eval = evaluate_ats_score(raw_text, sections, job_description)
    
    # Compute overall score with weights
    weights = {
        "format": 0.25,
        "ats": 0.25,
        "job_compatibility": 0.25 if job_description else 0.0,
        "grammar": 0.10,
        "skills_coverage": 0.15 if not job_description else 0.0,
    }
    
    # Redistribute job_compatibility weight if JD missing
    if not job_description:
        weights["ats"] = 0.35
        weights["format"] = 0.30
    
    overall_score = (
        weights["format"] * format_eval["score"] +
        weights["ats"] * ats_eval["score"] +
        weights["job_compatibility"] * job_compat_eval["score"] +
        weights["grammar"] * grammar_eval["score"] +
        weights["skills_coverage"] * (ats_eval["score"] * 0.5)  # Use ATS as proxy
    )
    
    # Generate top 5 actionable suggestions
    suggestions = []
    if format_eval.get("missing_sections"):
        suggestions.append(f"Add missing sections: {', '.join(format_eval['missing_sections'])}")
    if job_compat_eval.get("missing_required"):
        suggestions.append(f"Include keywords: {', '.join(job_compat_eval['missing_required'][:3])}")
    if ats_eval.get("cliches_found"):
        suggestions.append(f"Remove clichés: {', '.join(ats_eval['cliches_found'][:2])}")
    if ats_eval.get("impact_verb_without_number"):
        suggestions.append("Add numbers/metrics to impact verbs")
    if grammar_eval.get("error_count", 0) > 5:
        suggestions.append(f"Fix {grammar_eval['error_count']} grammar/spelling errors")
    
    # Ensure we have 5 suggestions
    while len(suggestions) < 5:
        suggestions.append("Review resume for overall clarity and impact")
    
    return {
        "overall_score": round(overall_score, 1),
        "format": format_eval,
        "grammar": grammar_eval,
        "job_compatibility": job_compat_eval,
        "ats": ats_eval,
        "parsed_sections": sections,
        "suggestions": suggestions[:5]
    }

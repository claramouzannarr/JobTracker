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
from app.services.skill_extraction import (
    extract_skills,
    extract_skills_from_job_description,
    extract_skills_from_bullets,
    compute_skill_coverage,
    compute_skill_gaps
)

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
    section_sequence = []  # Track actual order sections appear in resume
    
    # Section heading patterns
    section_patterns = {
        r"^(summary|professional\s+summary|objective|profile|about)$": "Summary",
        r"^(education|academic\s+background|academics)$": "Education",
        r"^(experience|work\s+experience|employment|professional\s+experience|work\s+history)$": "Experience",
        # Treat various skill-related headers (including "Programming Languages")
        # as the canonical Skills section.
        r"^(skills|technical\s+skills|core\s+competencies|key\s+skills|"
        r"programming\s+languages?|programming\s+skills|technical\s+proficiencies?|"
        r"tools\s+and\s+technologies|tools\s*/\s*technologies|technology\s+stack)$": "Skills",
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
    
    # Parse sections and track order
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        is_heading = False
        
        for pattern, section_name in section_patterns.items():
            if re.match(pattern, line_lower):
                # Save previous section
                if current_section != "Other" and current_content:
                    sections[current_section]["text"] = "\n".join(current_content)
                
                # Track section order (only add once per section)
                if section_name not in section_sequence:
                    section_sequence.append(section_name)
                
                current_section = section_name
                current_content = []
                is_heading = True
                break
        
        if not is_heading:
            current_content.append(line)
    
    # Save last section
    if current_content:
        sections[current_section]["text"] = "\n".join(current_content)
    
    # Store section sequence for ordering evaluation
    sections["_section_sequence"] = section_sequence
    
    # Parse Experience items (look for company/role patterns)
    experience_text = sections.get("Experience", {}).get("text", "")
    if experience_text:
        # Improved parsing: handle various formats
        exp_items = []
        exp_lines = experience_text.split('\n')
        current_item = {"company": "", "role": "", "bullets": [], "dates": ""}
        
        # Common bullet characters (including many PDF/Word variants)
        bullet_chars = [
            '•', '-', '*', '◦', '▪', '▸', '▹', '▫', '→', '·',
            '●', '○', '■', '♦', '‣', '▶', '►', '➤', '➔', '▻', '–', '—',
            '',  # common PDF/Word bullet (U+F0B7)
        ]

        # Heuristic: some PDF extractors drop bullet glyphs and indentation.
        # If we are already inside an experience item (company/dates seen),
        # treat long "action sentence" lines as bullets.
        common_bullet_openers = {
            "led", "built", "designed", "implemented", "developed", "created",
            "improved", "increased", "reduced", "optimized", "automated",
            "deployed", "integrated", "managed", "owned", "delivered",
            "architected", "engineered", "launched", "streamlined",
            "collaborated", "mentored", "analyzed",
        }
        
        def is_bullet_line(line: str) -> bool:
            """Check if a line is a bullet point."""
            stripped = line.strip()
            if not stripped:
                return False
            
            # Check for common bullet characters (with optional leading whitespace)
            if any(stripped.startswith(char) for char in bullet_chars):
                return True
            
            # Check for numbered bullets (1., 2., etc.)
            if re.match(r'^\d+[\.\)]\s', stripped):
                return True
            
            # Check for indented lines that might be bullets (2+ spaces or tab)
            if re.match(r'^[\s]{2,}', line) and len(stripped) > 10:
                # Likely a bullet if indented and has content
                return True
            
            return False
        
        for line in exp_lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            
            # Check for date pattern (year in date format)
            if re.search(r'\d{4}', stripped_line) and (
                re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', stripped_line.lower()) or
                re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', stripped_line) or
                re.search(r'\d{4}\s*[-–—]\s*\d{4}', stripped_line) or
                re.search(r'\d{4}\s*[-–—]\s*(present|current|now)', stripped_line.lower())
            ):
                if current_item["company"] or current_item["bullets"]:
                    exp_items.append(current_item)
                current_item = {"company": "", "role": "", "bullets": [], "dates": ""}
                current_item["dates"] = stripped_line
            
            # Check for bullet point
            elif is_bullet_line(line):
                # Clean bullet: remove bullet char and leading whitespace
                bullet_text = stripped_line
                for char in bullet_chars:
                    if bullet_text.startswith(char):
                        bullet_text = bullet_text[len(char):].strip()
                        break
                # Remove numbered prefix if present
                bullet_text = re.sub(r'^\d+[\.\)]\s*', '', bullet_text).strip()
                if bullet_text:
                    current_item["bullets"].append(bullet_text)
            
            # Bullet fallback: treat action-style lines as bullets when we have context
            # (company or dates already seen for this item).
            elif (current_item.get("company") or current_item.get("dates")) and not is_bullet_line(line):
                # Avoid accidentally treating headers as bullets
                if (
                    len(stripped_line) >= 18
                    and re.match(r"^[A-Za-z]", stripped_line)
                    and '|' not in stripped_line
                    and not re.match(r"^(experience|education|skills|projects|summary)\b", stripped_line.lower())
                ):
                    first_word = (stripped_line.split()[:1] or [""])[0].lower().strip(".,;:!?()[]{}")
                    has_metric = bool(re.search(r"\d+|%|\$|€|£", stripped_line))
                    if first_word in common_bullet_openers or has_metric:
                        current_item["bullets"].append(stripped_line)

            # Check if this looks like a company/role line
            elif not current_item["company"] and not is_bullet_line(line):
                # Look for company/role patterns
                # Pattern 1: Company | Role
                if '|' in stripped_line:
                    parts = stripped_line.split('|')
                    if len(parts) >= 2:
                        current_item["company"] = parts[0].strip()
                        current_item["role"] = parts[1].strip()
                    else:
                        current_item["company"] = stripped_line
                # Pattern 2: Company - Role
                elif ' - ' in stripped_line or ' – ' in stripped_line:
                    parts = re.split(r'\s*[-–]\s*', stripped_line, 1)
                    if len(parts) >= 2:
                        current_item["company"] = parts[0].strip()
                        current_item["role"] = parts[1].strip()
                    else:
                        current_item["company"] = stripped_line
                # Pattern 3: Just company name (if it looks like a title/company)
                elif len(stripped_line) > 3 and len(stripped_line) < 100:
                    # If it's all caps or title case, likely a company/role
                    if stripped_line.isupper() or (stripped_line[0].isupper() and not re.search(r'\d{4}', stripped_line)):
                        current_item["company"] = stripped_line
                # Otherwise, if we already have bullets, this might be a continuation
                elif current_item["bullets"]:
                    # Could be a continuation of previous bullet or new content
                    pass
        
        # Add last item if it has content
        if current_item["company"] or current_item["bullets"]:
            exp_items.append(current_item)
        
        sections["Experience"]["items"] = exp_items
    
    # Parse Projects items (similar to Experience)
    projects_text = sections.get("Projects", {}).get("text", "")
    if projects_text:
        proj_items = []
        proj_lines = projects_text.split('\n')
        current_item = {"title": "", "bullets": [], "dates": ""}
        
        # Reuse bullet detection function with extended bullet characters
        bullet_chars = [
            '•', '-', '*', '◦', '▪', '▸', '▹', '▫', '→', '·',
            '●', '○', '■', '♦', '‣', '▶', '►', '➤', '➔', '▻', '–', '—',
            '',  # common PDF/Word bullet (U+F0B7)
        ]
        
        def is_bullet_line(line: str) -> bool:
            """Check if a line is a bullet point."""
            stripped = line.strip()
            if not stripped:
                return False
            if any(stripped.startswith(char) for char in bullet_chars):
                return True
            if re.match(r'^\d+[\.\)]\s', stripped):
                return True
            if re.match(r'^[\s]{2,}', line) and len(stripped) > 10:
                return True
            return False
        
        for line in proj_lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            
            # Check for date pattern
            if re.search(r'\d{4}', stripped_line) and (
                re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', stripped_line.lower()) or
                re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', stripped_line) or
                re.search(r'\d{4}\s*[-–—]\s*\d{4}', stripped_line) or
                re.search(r'\d{4}\s*[-–—]\s*(present|current|now)', stripped_line.lower())
            ):
                if current_item["title"] or current_item["bullets"]:
                    proj_items.append(current_item)
                current_item = {"title": "", "bullets": [], "dates": ""}
                current_item["dates"] = stripped_line
            
            # Check for bullet point
            elif is_bullet_line(line):
                bullet_text = stripped_line
                for char in bullet_chars:
                    if bullet_text.startswith(char):
                        bullet_text = bullet_text[len(char):].strip()
                        break
                bullet_text = re.sub(r'^\d+[\.\)]\s*', '', bullet_text).strip()
                if bullet_text:
                    current_item["bullets"].append(bullet_text)
            
            # Check if this looks like a project title
            elif not current_item["title"] and not is_bullet_line(line):
                if len(stripped_line) > 3 and len(stripped_line) < 100:
                    if stripped_line[0].isupper() and not re.search(r'\d{4}', stripped_line):
                        current_item["title"] = stripped_line
        
        # Add last item if it has content
        if current_item["title"] or current_item["bullets"]:
            proj_items.append(current_item)
        
        sections["Projects"]["items"] = proj_items
    
    # Parse Skills list
    skills_text = sections.get("Skills", {}).get("text", "")
    if skills_text:
        # Extract skills (prefer delimiter-based parsing; avoid treating full sentences as skills).
        # IMPORTANT: store the canonical skills detected via the skill extractor, not raw text tokens,
        # so we don't surface stopwords/locations as "skills".
        raw_candidates: list[str] = []
        for line in skills_text.split('\n'):
            l = line.strip()
            if not l:
                continue

            # Strip leading bullet glyphs (including Word/PDF variants)
            l = re.sub(r"^[\s•\-\*]+", "", l).strip()
            if not l:
                continue

            # Split on common delimiters inside a line
            if any(d in l for d in [",", ";", "·", "•", "|"]):
                parts = re.split(r"[,;|•·]+", l)
                raw_candidates.extend([p.strip() for p in parts if p.strip()])
            else:
                # Only accept short single items as a skill; ignore paragraph-like lines
                raw_candidates.append(l)

        stopish = {
            "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "is",
            "it", "of", "on", "or", "our", "the", "to", "we", "while", "with", "within",
        }

        def is_probable_skill(s: str) -> bool:
            s2 = s.strip()
            if not s2:
                return False
            if len(s2) < 2 or len(s2) > 40:
                return False
            # Drop sentence-like lines
            if s2.count(" ") >= 5:
                return False
            s2_lower = s2.lower()
            if s2_lower in stopish:
                return False
            # Drop obvious narrative fragments
            if any(phrase in s2_lower for phrase in ["overview note", "current security", "situation"]):
                return False
            return True

        cleaned = []
        seen = set()
        for c in raw_candidates:
            c2 = c.strip().strip(".")
            if not is_probable_skill(c2):
                continue
            key = c2.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(c2)

        # Canonicalize to known skills using the extractor
        try:
            from app.services.skill_extraction import extract_skills
            canonical = sorted(list(extract_skills(" ".join(cleaned)))) if cleaned else []
        except Exception:
            canonical = []

        # If canonical extraction yields nothing (e.g., spaCy model missing),
        # fall back to the cleaned list to avoid wiping the Skills section entirely.
        sections["Skills"]["skills_list"] = canonical if canonical else cleaned
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
    
    # Get actual order from section sequence (order sections appear in resume)
    actual_order = sections.get("_section_sequence", [])
    # Add Header if not in sequence (it's always first)
    if "Header" not in actual_order:
        actual_order = ["Header"] + actual_order
    
    # Filter to only sections that exist
    found_order = [s for s in actual_order if s in found_sections]
    recommended_found = [s for s in recommended_order if s in found_sections]
    
    # Calculate ordering match: compare positions of sections
    if len(found_order) > 1:
        # Count how many adjacent pairs match the recommended order
        matches = 0
        total_pairs = 0
        for i in range(len(found_order) - 1):
            current_section = found_order[i]
            next_section = found_order[i + 1]
            
            if current_section in recommended_order and next_section in recommended_order:
                total_pairs += 1
                current_idx = recommended_order.index(current_section)
                next_idx = recommended_order.index(next_section)
                if next_idx > current_idx:
                    matches += 1
        
        ordering_match = matches / total_pairs if total_pairs > 0 else 0
    else:
        ordering_match = 1.0 if found_order else 0
    
    if ordering_match >= 0.8:  # 80% match
        score += 20
        strengths.append("✓ Sections are well-ordered")
    else:
        ordering_ok = False
        issues.append(f"Section ordering doesn't match recommended order for {career_level} level")
        score += 10
    
    details["ordering"] = {
        "recommended_order": recommended_order,
        "actual_order": found_order,
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

            # New rule: full points only when each experience entry
            # has exactly the same number of bullets (and at least one).
            unique_counts = set(bullet_counts)
            if len(unique_counts) == 1 and next(iter(unique_counts)) > 0:
                score += 30
                strengths.append(
                    f"✓ Exactly {next(iter(unique_counts))} bullet(s) for each of the "
                    f"{len(experience_items)} experience entries"
                )
                bullet_score_points = 30
            elif diff <= 2:
                # Partial credit when counts are close but not identical
                score += 15
                bullet_score_points = 15
                issues.append(
                    f"Bullet point counts are close but not identical "
                    f"({min_bullets}-{max_bullets} per entry; aim for the same count per role)"
                )
            else:
                score += 5
                bullet_score_points = 5
                issues.append(
                    f"Inconsistent bullets across roles "
                    f"({min_bullets}-{max_bullets} per entry; align bullet counts per role)"
                )

            details["bullets"] = {
                "total_experience_items": len(experience_items),
                "total_bullets": total_bullets,
                "average_per_item": round(total_bullets / len(experience_items), 1),
                "min_bullets": min_bullets,
                "max_bullets": max_bullets,
                "consistency_diff": diff,
                "exact_match_required": True,
                "score_breakdown": (
                    f"{'Exact match' if len(unique_counts) == 1 and next(iter(unique_counts)) > 0 else f'{diff} bullet difference'} "
                    f"({bullet_score_points}/30 points)"
                )
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
    Score: 0-100 (100 = perfect, no errors)
    """
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
    
    # If no text to check, return perfect score
    if not combined_text.strip():
        return {
            "score": 100.0,
            "errors_per_100_words": 0,
            "top_examples": [],
            "error_count": 0,
            "word_count": 0
        }
    
    # Check if grammar_tool is available
    if grammar_tool is None:
        # If tool unavailable, return neutral score but indicate it
        return {
            "score": 100.0,  # Assume perfect if tool unavailable
            "errors_per_100_words": 0,
            "top_examples": [],
            "error_count": 0,
            "word_count": len(combined_text.split()),
            "tool_available": False
        }
    
    try:
        errors = grammar_tool.check(combined_text)
        error_count = len(errors)
        word_count = len(combined_text.split())
        errors_per_100_words = (error_count / word_count * 100) if word_count > 0 else 0
        
        # Score: start at 100, subtract penalty
        # Max penalty is 40 points (so minimum score is 60)
        # Formula: 100 - min(40, errors_per_100_words * 2)
        # This means: 0 errors = 100, 20 errors/100 words = 60, 40+ errors/100 words = 60
        score = max(60, 100 - min(40, errors_per_100_words * 2))
        
        # If no errors, ensure perfect score
        if error_count == 0:
            score = 100.0
        
        # Get top examples
        top_examples = []
        for error in errors[:5]:
            top_examples.append({
                "text": error.context[:100] if error.context else "",
                "issue": error.message,
                "suggestion": error.replacements[0] if error.replacements else ""
            })
        
        return {
            "score": round(score, 1),
            "errors_per_100_words": round(errors_per_100_words, 2),
            "top_examples": top_examples,
            "error_count": error_count,
            "word_count": word_count,
            "tool_available": True
        }
    except Exception as e:
        print(f"Error in grammar checking: {e}")
        # On error, return perfect score (assume no errors if check fails)
        return {
            "score": 100.0,
            "errors_per_100_words": 0,
            "top_examples": [],
            "error_count": 0,
            "word_count": len(combined_text.split()),
            "tool_available": True,
            "error": str(e)
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

    # Canonical skill casing (so JD skills match resume skills exactly)
    vocab_lower_to_canonical = {}
    try:
        from app.services.skill_extraction import load_skill_vocabulary
        vocab = load_skill_vocabulary()
        vocab_lower_to_canonical = {v.lower(): v for v in vocab}
    except Exception:
        vocab_lower_to_canonical = {}
    
    # Extract technical skills/tools (common patterns)
    tech_patterns = [
        r'\b(aws|azure|gcp|kubernetes|docker|jenkins|git|github|gitlab)\b',
        r'\b(python|java|javascript|typescript|react|vue|angular|node\.?js|sql|nosql|mongodb|postgresql|mysql)\b',
        r'\b(microsoft\s+365|office\s+365|excel|powerpoint|word|outlook)\b',
        r'\b(tableau|power\s+bi|looker|qlik|snowflake|redshift|bigquery)\b',
        r'\b(machine\s+learning|ml|artificial\s+intelligence|ai|deep\s+learning|nlp)\b',
        r'\b(agile|scrum|kanban|ci/cd|devops|microservices)\b',
    ]
    
    required_keywords: list[str] = []
    optional_keywords: list[str] = []
    
    # Extract using patterns
    for pattern in tech_patterns:
        matches = re.findall(pattern, jd_lower, re.IGNORECASE)
        for m in matches:
            nm = normalize_skill(m).lower()
            required_keywords.append(vocab_lower_to_canonical.get(nm, nm))
    
    # OPTIONAL keywords fallback:
    # Previously we added arbitrary capitalized phrases (e.g., "At Microsoft") which polluted
    # job_skills and caused nonsense "missing skills" like "we", "at microsoft", etc.
    #
    # We now only include optional terms if they map to a known skill in our vocabulary.
    try:
        vocab_lower = set(vocab_lower_to_canonical.keys()) if vocab_lower_to_canonical else set()

        capitalized_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', job_description)
        for t in capitalized_terms[:40]:
            norm = normalize_skill(t.lower())
            if norm.lower() in vocab_lower:
                optional_keywords.append(vocab_lower_to_canonical.get(norm.lower(), norm))
    except Exception:
        # If vocabulary can't be loaded, skip optional extraction entirely to avoid false positives.
        pass
    
    return {
        "required": list(set(required_keywords)),
        "optional": list(set(optional_keywords))[:30]
    }


def compute_skill_demonstrated_index(sections: Dict[str, Any], K: float = 25.0) -> Dict[str, Any]:
    """
    Compute Skill Demonstrated Index (SDI) based on weighted skills from different sections.
    Uses per-bullet extraction for better context.
    
    Skills mentioned in Skills section are less informative than skills used in Experience/Projects,
    because recruiters care about demonstrated use.
    
    Formula:
    - WeightedSkillCount = w_exp * |S_exp| + w_proj * |S_proj| + w_skills * |S_skills|
    - Richness = min(1, WeightedSkillCount / K)
    
    Weights:
    - w_exp = 1.0 (Experience section)
    - w_proj = 0.8 (Projects section)
    - w_skills = 0.4 (Skills section)
    - w_summary = 0.3 (Summary section, optional)
    
    K is chosen so that a strong resume maps near 1.0 (default K=25.0)
    """
    # Extract skills from each section using per-bullet extraction
    skills_exp_set = set()
    skills_proj_set = set()
    skills_list_set = set()
    skills_summary_set = set()
    
    # Extract from Experience section - per bullet point
    experience_items = sections.get("Experience", {}).get("items", [])
    for item in experience_items:
        bullets = item.get("bullets", [])
        if bullets:
            try:
                bullet_skills = extract_skills_from_bullets(bullets)
                for bullet_idx, skills in bullet_skills.items():
                    skills_exp_set.update(skills)
            except Exception as e:
                print(f"Error extracting skills from Experience bullets: {e}")
    
    # Extract from Projects section - per bullet point
    projects_items = sections.get("Projects", {}).get("items", [])
    for item in projects_items:
        bullets = item.get("bullets", [])
        if bullets:
            try:
                bullet_skills = extract_skills_from_bullets(bullets)
                for bullet_idx, skills in bullet_skills.items():
                    skills_proj_set.update(skills)
            except Exception as e:
                print(f"Error extracting skills from Projects bullets: {e}")
    
    # Extract from Skills section
    skills_list = sections.get("Skills", {}).get("skills_list", [])
    skills_text = sections.get("Skills", {}).get("text", "")
    if skills_list:
        # Extract skills from the list
        skills_list_text = " ".join(skills_list)
        try:
            skills_list_set = extract_skills(skills_list_text)
        except Exception as e:
            print(f"Error extracting skills from Skills list: {e}")
    elif skills_text:
        try:
            skills_list_set = extract_skills(skills_text)
        except Exception as e:
            print(f"Error extracting skills from Skills text: {e}")
    
    # Extract from Summary section (optional)
    summary_text = sections.get("Summary", {}).get("text", "")
    if summary_text:
        try:
            skills_summary_set = extract_skills(summary_text)
        except Exception as e:
            print(f"Error extracting skills from Summary: {e}")
    
    # Compute weighted skill count
    w_exp = 1.0
    w_proj = 0.8
    w_skills = 0.4
    w_summary = 0.3
    
    weighted_skill_count = (
        w_exp * len(skills_exp_set) +
        w_proj * len(skills_proj_set) +
        w_skills * len(skills_list_set) +
        w_summary * len(skills_summary_set)
    )
    
    # Normalize to richness score
    richness = min(1.0, weighted_skill_count / K)
    
    # Get all unique skills across sections
    all_demonstrated_skills = skills_exp_set.union(skills_proj_set).union(skills_list_set).union(skills_summary_set)
    
    return {
        "sdi_score": round(richness * 100, 1),  # Convert to 0-100 scale
        "richness": round(richness, 3),
        "weighted_skill_count": round(weighted_skill_count, 2),
        "skills_exp": sorted(list(skills_exp_set)),
        "skills_proj": sorted(list(skills_proj_set)),
        "skills_list": sorted(list(skills_list_set)),
        "skills_summary": sorted(list(skills_summary_set)),
        "all_demonstrated_skills": sorted(list(all_demonstrated_skills)),
        "counts": {
            "experience": len(skills_exp_set),
            "projects": len(skills_proj_set),
            "skills_section": len(skills_list_set),
            "summary": len(skills_summary_set),
            "total_unique": len(all_demonstrated_skills)
        }
    }


def evaluate_job_compatibility(
    resume_text: str, 
    job_description: Optional[str] = None,
    sections: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluate job compatibility using skill extraction + embeddings.
    Only computes when job description exists.
    
    Formula:
    - JD SkillCoverage: |S_job ∩ S_resume| / |S_job|
    - Similarity: cosine(embed(JD), embed(resume))
    - Compatibility = α SkillCoverage + (1-α) Similarity (where α = 0.7)
    """
    # Only compute if JD exists
    if not job_description:
        return None
    
    # Extract skills from job description using PhraseMatcher + semantic matching
    try:
        job_skills_set = extract_skills_from_job_description(job_description)
        job_skills = sorted(list(job_skills_set))
    except Exception as e:
        print(f"Error extracting skills from JD: {e}")
        job_skills_set = set()
        job_skills = []
    
    # If advanced JD skill extraction fails or returns nothing, fall back to
    # regex-based keyword extraction so we still have a meaningful skill set.
    if not job_skills_set:
        try:
            jd_keywords = extract_job_keywords(job_description)
            fallback_required = set(jd_keywords.get("required", []))
            fallback_optional = set(jd_keywords.get("optional", []))
            job_skills_set = fallback_required.union(fallback_optional)
            job_skills = sorted(list(job_skills_set))
        except Exception as e:
            print(f"Error in JD keyword fallback: {e}")
    
    # Extract skills from resume using demonstrated skills from sections if available
    resume_skills_set = set()
    if sections:
        # Use SDI logic to get demonstrated skills
        try:
            sdi_result = compute_skill_demonstrated_index(sections)
            demonstrated_skills = sdi_result.get("all_demonstrated_skills", [])
            resume_skills_set.update(demonstrated_skills)
        except Exception as e:
            print(f"Error computing demonstrated skills: {e}")
    
    # Also extract from full resume text
    try:
        full_resume_skills = extract_skills(resume_text)
        resume_skills_set.update(full_resume_skills)
    except Exception as e:
        print(f"Error extracting skills from resume: {e}")
    
    resume_skills = sorted(list(resume_skills_set))
    
    # Compute skill coverage: |S_job ∩ S_resume| / |S_job|
    skill_coverage = compute_skill_coverage(resume_skills_set, job_skills_set)
    
    # Compute matched and missing skills
    matched_skills_set = job_skills_set.intersection(resume_skills_set)
    missing_skills_set = compute_skill_gaps(resume_skills_set, job_skills_set)
    matched_skills = sorted(list(matched_skills_set))
    missing_skills = sorted(list(missing_skills_set))
    
    # Compute embedding similarity (soft semantic signal)
    embedding_similarity = 0.0
    if embedding_model:
        try:
            resume_emb = embedding_model.encode([resume_text])
            jd_emb = embedding_model.encode([job_description])
            embedding_similarity = float(cosine_similarity(resume_emb, jd_emb)[0][0])
        except Exception as e:
            print(f"Error computing embeddings: {e}")
    
    # If no skills found, fallback to embedding similarity only
    if not job_skills_set:
        return {
            "score": min(100, max(0, embedding_similarity * 100)),
            "job_skills": [],
            "resume_skills": resume_skills,
            "matched_skills": [],
            "missing_skills": [],
            "skill_coverage": 0.0,
            "embedding_similarity": round(embedding_similarity, 3)
        }
    
    # Combined score: α SkillCoverage + (1-α) Similarity
    # α = 0.7 (70% skill coverage, 30% embedding similarity)
    alpha = 0.7
    score = (alpha * skill_coverage * 100) + ((1 - alpha) * embedding_similarity * 100)
    
    return {
        "score": min(100, max(0, score)),
        "job_skills": job_skills,
        "resume_skills": resume_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "skill_coverage": round(skill_coverage, 3),
        "embedding_similarity": round(embedding_similarity, 3)
    }


def evaluate_ats_score(raw_text: str, sections: Dict[str, Any], job_description: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluate ATS content depth score.
    Checks: clichés, action verbs, KPIs/quantification, skills coverage, experience density.
    """
    score = 0.0
    # Max raw score components:
    # 20 (clichés) + 10 (action verbs) + 30 (quantification) + 15 (experience) = 75
    max_raw_score = 75.0
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
        # Include specific cliché phrases directly in the issue text so users
        # always see which words to replace.
        unique_cliches = sorted(set(cliches_found))
        examples = ", ".join(unique_cliches[:5])
        issues.append(
            f"Cliché phrases found ({len(cliches_found)}): {examples}"
        )
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
    
    # 2. Action verb and opening-phrase quality (10 points)
    experience_items = sections.get("Experience", {}).get("items", [])
    strong_verb_count = 0
    weak_or_cliche_count = 0
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
            found_cliche = [c for c in CLICHE_PHRASES if c in first_words]
            
            if found_strong:
                strong_verb_count += 1
                strong_verbs_found.extend(found_strong[:1])  # Track first occurrence
            elif found_weak or found_cliche:
                weak_or_cliche_count += 1
                # Track weak/cliché examples for messaging
                if found_weak:
                    weak_verbs_found.extend(found_weak[:1])
                elif found_cliche:
                    weak_verbs_found.extend(found_cliche[:1])
    
    if total_bullets > 0:
        # New, simpler scoring:
        # - Start with full 10 points.
        # - If there are no strong-verb openings at all, drop to 5.
        # - If any bullets start with cliché/weak phrases, apply a flat 1-point penalty.
        verb_score = 10.0

        if strong_verb_count == 0:
            issues.append("No bullets start with strong action verbs; consider openings like led, implemented, designed.")
            verb_score = 5.0
        else:
            strengths.append(
                f"✓ Uses strong action verbs such as: {', '.join(sorted(set(strong_verbs_found))[:5])}"
            )

        if weak_or_cliche_count == 0:
            strengths.append("✓ No bullets start with weak or cliché openings")
        else:
            issues.append(
                f"{weak_or_cliche_count} bullets start with weak or cliché phrases "
                f"(e.g., {', '.join(sorted(set(weak_verbs_found))[:3])})"
            )
            verb_score = max(0.0, verb_score - 1.0)

        score += verb_score

        details["action_verbs"] = {
            "total_bullets": total_bullets,
            "strong_verbs": strong_verb_count,
            "weak_or_cliche_openings": weak_or_cliche_count,
            "examples_strong": list(set(strong_verbs_found))[:5],
            "examples_weak": list(set(weak_verbs_found))[:3],
            "score_breakdown": (
                f"{strong_verb_count} bullets with strong action verbs, "
                f"{weak_or_cliche_count} with weak/cliché openings "
                f"({verb_score:.1f}/10 points)"
            )
        }
    else:
        issues.append("No bullet points found in experience")
        details["action_verbs"] = {
            "total_bullets": 0,
            "score_breakdown": "No bullets found (0/10 points)"
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
    
    # 4. Skills overview (informational only, no numeric SDI shown)
    # We still surface a simple count of unique demonstrated skills across sections,
    # but do not expose the SDI metric or its percentage.
    skills_list = sections.get("Skills", {}).get("skills_list", [])
    skills_count = len(skills_list)

    try:
        sdi_result = compute_skill_demonstrated_index(sections)
        counts = sdi_result.get("counts", {})
        exp_count = counts.get("experience", 0)
        proj_count = counts.get("projects", 0)
        skills_section_count = counts.get("skills_section", 0)
        total_unique = counts.get("total_unique", 0)

        if skills_section_count > 0:
            skills_count = skills_section_count

        details["skills"] = {
            "experience_skills": exp_count,
            "projects_skills": proj_count,
            "skills_section_count": skills_section_count,
            "total_unique_skills": total_unique,
            "score_breakdown": (
                f"Demonstrated skills: {total_unique} unique skills across "
                f"experience, projects, skills, and summary (informational only)"
            )
        }
    except Exception as e:
        print(f"Error computing skills overview: {e}")
        # Fallback to basic skills count (informational only)
        details["skills"] = {
            "resume_skills_count": skills_count,
            "score_breakdown": (
                f"{skills_count} skills listed in the skills section "
                f"(informational only)"
            )
        }
    
    # 5. Experience density (15 points)
    experience_count = len(experience_items)
    experience_score = 0
    
    if experience_count >= 3:
        experience_score = 15
        strengths.append(f"✓ Strong experience depth ({experience_count} entries)")
    elif experience_count >= 2:
        experience_score = 10
        issues.append(f"Consider adding more experience entries (currently {experience_count})")
    elif experience_count >= 1:
        experience_score = 5
        issues.append(f"Limited experience entries ({experience_count})")
    else:
        issues.append("No experience items found")
        experience_score = 0
    
    # Check for dates (part of experience score) - only within Experience section
    experience_text = sections.get("Experience", {}).get("text", "")
    dates_found = False
    
    # Check in Experience section text
    if experience_text:
        dates_found = bool(re.search(r'\d{4}', experience_text))
    
    # Also check in individual experience items
    if not dates_found and experience_items:
        for item in experience_items:
            # Check in dates field
            if item.get("dates") and re.search(r'\d{4}', item.get("dates", "")):
                dates_found = True
                break
            # Check in company/role line (sometimes dates are there)
            company_role = f"{item.get('company', '')} {item.get('role', '')}"
            if re.search(r'\d{4}', company_role):
                dates_found = True
                break
    
    if dates_found:
        strengths.append("✓ Dates found in experience")
    else:
        issues.append("No dates found in experience")
        # Reduce experience score by 2 points if no dates (but don't go below 0)
        experience_score = max(0, experience_score - 2)
    
    score += experience_score
    
    details["experience"] = {
        "experience_count": experience_count,
        "has_dates": dates_found,
        "experience_score": experience_score,
        "score_breakdown": f"{experience_count} entries, dates: {'yes' if dates_found else 'no'} ({experience_score}/15 points)"
    }
    
    # Normalize raw score (0–max_raw_score) to 0–100 scale for Content Depth.
    final_score = min(100, max(0, (score / max_raw_score) * 100.0))

    return {
        "score": round(final_score, 1),
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
    job_compat_eval = evaluate_job_compatibility(raw_text, job_description, sections)
    content_depth_eval = evaluate_ats_score(raw_text, sections, job_description)
    
    # Compute overall score with weights (percentages)
    # Requested:
    # - 15% format evaluation
    # - 10% grammar
    # - 45% job compatibility
    # - 30% content depth
    weights = {
        "format": 0.15,
        "grammar": 0.10,
        "job_compatibility": 0.45,
        "content_depth": 0.30,
    }

    # If JD missing, exclude job compatibility and renormalize remaining weights
    if not job_description or not job_compat_eval:
        weights["job_compatibility"] = 0.0

    total_w = sum(weights.values()) or 1.0
    norm = {k: (v / total_w) for k, v in weights.items()}

    overall_score = (
        norm["format"] * format_eval["score"] +
        norm["content_depth"] * content_depth_eval["score"] +
        (norm["job_compatibility"] * job_compat_eval["score"] if job_compat_eval else 0) +
        norm["grammar"] * grammar_eval["score"]
    )
    
    # Generate top 5 actionable suggestions
    suggestions = []
    if format_eval.get("missing_sections"):
        suggestions.append(f"Add missing sections: {', '.join(format_eval['missing_sections'])}")
    if job_compat_eval and job_compat_eval.get("missing_skills"):
        suggestions.append(f"Include skills: {', '.join(job_compat_eval['missing_skills'][:3])}")
    if content_depth_eval.get("cliches_found"):
        suggestions.append(f"Remove clichés: {', '.join(content_depth_eval['cliches_found'][:2])}")
    if content_depth_eval.get("impact_verb_without_number"):
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
        "content_depth": content_depth_eval,
        "parsed_sections": sections,
        "suggestions": suggestions[:5]
    }

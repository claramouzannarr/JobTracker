import re
import spacy
from typing import Dict, List, Optional

# Load spaCy model (will need to download: python -m spacy download en_core_web_trf)
try:
    nlp = spacy.load("en_core_web_trf")
except OSError:
    # Fallback to smaller model if transformer not available
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        nlp = None
        print("Warning: spaCy model not found. Please install: python -m spacy download en_core_web_sm")


# Section heading patterns
SECTION_PATTERNS = [
    r"^(education|academic\s+background|educational\s+background)$",
    r"^(experience|work\s+experience|employment|professional\s+experience)$",
    r"^(skills|technical\s+skills|core\s+competencies)$",
    r"^(projects|project\s+experience|personal\s+projects)$",
    r"^(summary|professional\s+summary|objective|profile)$",
    r"^(certifications|certificates)$",
    r"^(awards|honors|achievements)$",
]


def detect_sections(text: str) -> Dict[str, str]:
    """Split resume text into sections using heuristic heading detection."""
    sections = {}
    lines = text.split("\n")
    current_section = "other"
    current_content = []
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Check if line looks like a section heading
        is_heading = False
        for pattern in SECTION_PATTERNS:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                # Save previous section
                if current_section != "other" and current_content:
                    sections[current_section] = "\n".join(current_content)
                
                # Start new section
                current_section = line_stripped.lower()
                current_content = []
                is_heading = True
                break
        
        if not is_heading:
            current_content.append(line_stripped)
    
    # Save last section
    if current_section != "other" and current_content:
        sections[current_section] = "\n".join(current_content)
    
    return sections


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract named entities using spaCy."""
    if nlp is None:
        return {"organizations": [], "dates": [], "degrees": []}
    
    doc = nlp(text)
    entities = {
        "organizations": [],
        "dates": [],
        "degrees": [],
    }
    
    for ent in doc.ents:
        if ent.label_ == "ORG":
            entities["organizations"].append(ent.text)
        elif ent.label_ == "DATE":
            entities["dates"].append(ent.text)
        # Degrees are often in PERSON or MISC, so we'll handle them separately
    
    # Extract degree patterns
    degree_patterns = [
        r"\b(BS|BA|B\.S\.|B\.A\.|MS|MA|M\.S\.|M\.A\.|PhD|Ph\.D\.|MBA|M\.B\.A\.)\b",
        r"\b(Bachelor|Master|Doctorate|Doctor)\b",
    ]
    for pattern in degree_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities["degrees"].extend(matches)
    
    return entities


def parse_resume(text: str) -> Dict[str, any]:
    """Main function to parse resume into structured format."""
    sections = detect_sections(text)
    entities = extract_entities(text)
    
    return {
        "sections": sections,
        "entities": entities,
        "raw_text": text,
    }


import pandas as pd
import spacy
from spacy.matcher import PhraseMatcher
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Set, Dict, Optional
import os

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_trf")
except OSError:
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        nlp = None

# Load sentence transformer model
try:
    skill_embedder = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    skill_embedder = None
    print(f"Warning: Could not load sentence transformer: {e}")

# Default skill vocabulary (can be loaded from CSV later)
DEFAULT_SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
    "React", "Vue", "Angular", "Node.js", "Django", "Flask", "FastAPI",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "TensorFlow", "PyTorch", "scikit-learn", "pandas", "numpy",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git",
    "Machine Learning", "Deep Learning", "Data Science", "NLP",
    "Salesforce", "Tableau", "Power BI", "Excel", "Bloomberg",
    "Agile", "Scrum", "JIRA", "Confluence",
    "HTML", "CSS", "Tailwind", "Bootstrap",
    "REST API", "GraphQL", "Microservices",
    "Linux", "Unix", "Shell Scripting",
]


def load_skill_vocabulary(csv_path: Optional[str] = None) -> List[str]:
    """Load skill vocabulary from CSV or use default."""
    if csv_path and os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            skills = df['skill'].tolist() if 'skill' in df.columns else DEFAULT_SKILLS
            return skills
        except Exception as e:
            print(f"Error loading skill CSV: {e}, using defaults")
            return DEFAULT_SKILLS
    return DEFAULT_SKILLS


def extract_skills_with_matcher(text: str, skill_vocab: List[str]) -> Set[str]:
    """Extract skills using spaCy PhraseMatcher."""
    if nlp is None:
        return set()
    
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(skill.lower()) for skill in skill_vocab]
    matcher.add("SKILLS", patterns)
    
    doc = nlp(text.lower())
    matches = matcher(doc, as_spans=True)
    
    found_skills = set()
    for match in matches:
        # Get original case from vocabulary
        matched_text = match.text
        for skill in skill_vocab:
            if skill.lower() == matched_text.lower():
                found_skills.add(skill)
                break
    
    return found_skills


def find_semantic_skills(text: str, skill_vocab: List[str], threshold: float = 0.6) -> Set[str]:
    """Find skills using semantic similarity with embeddings."""
    if skill_embedder is None:
        return set()
    
    # Extract potential skill phrases (words/phrases that might be skills)
    # Simple heuristic: capitalize words, technical terms, etc.
    words = text.split()
    potential_skills = []
    
    # Look for capitalized words/phrases that might be skills
    for i, word in enumerate(words):
        if word[0].isupper() and len(word) > 2:
            # Check if it's part of a multi-word skill
            phrase = word
            if i + 1 < len(words) and words[i + 1][0].isupper():
                phrase = f"{word} {words[i + 1]}"
            potential_skills.append(phrase)
    
    if not potential_skills:
        return set()
    
    # Get embeddings
    try:
        skill_embeddings = skill_embedder.encode(skill_vocab, convert_to_numpy=True)
        potential_embeddings = skill_embedder.encode(potential_skills, convert_to_numpy=True)
        
        # Compute similarities
        similarities = cosine_similarity(potential_embeddings, skill_embeddings)
        
        found_skills = set()
        for i, potential in enumerate(potential_skills):
            max_sim_idx = np.argmax(similarities[i])
            max_sim = similarities[i][max_sim_idx]
            if max_sim >= threshold:
                found_skills.add(skill_vocab[max_sim_idx])
        
        return found_skills
    except Exception as e:
        print(f"Error in semantic skill matching: {e}")
        return set()


def extract_skills(text: str, skill_vocab: Optional[List[str]] = None) -> Set[str]:
    """Main function to extract skills from text."""
    if skill_vocab is None:
        skill_vocab = load_skill_vocabulary()
    
    # Combine exact matching and semantic matching
    exact_skills = extract_skills_with_matcher(text, skill_vocab)
    semantic_skills = find_semantic_skills(text, skill_vocab)
    
    return exact_skills.union(semantic_skills)


def extract_skills_from_job_description(jd_text: str, skill_vocab: Optional[List[str]] = None) -> Set[str]:
    """Extract required skills from job description."""
    return extract_skills(jd_text, skill_vocab)


def compute_skill_gaps(resume_skills: Set[str], job_skills: Set[str]) -> Set[str]:
    """Compute skills required by job but missing from resume."""
    return job_skills - resume_skills


def compute_skill_coverage(resume_skills: Set[str], job_skills: Set[str]) -> float:
    """Compute what percentage of job skills are covered by resume."""
    if not job_skills:
        return 1.0
    matched = resume_skills.intersection(job_skills)
    return len(matched) / len(job_skills)


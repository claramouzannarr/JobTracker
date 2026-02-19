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

# Expanded skill vocabulary - comprehensive list of technical skills
DEFAULT_SKILLS = [
    # Programming Languages
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "C", "Go", "Rust", "Swift", "Kotlin",
    "Ruby", "PHP", "Perl", "Scala", "R", "MATLAB", "Julia", "Haskell", "Erlang", "Elixir",
    # Web Frameworks & Libraries
    "React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt.js", "Ember.js", "Backbone.js",
    "Node.js", "Express", "NestJS", "Django", "Flask", "FastAPI", "Spring", "Spring Boot",
    "ASP.NET", "Laravel", "Symfony", "Ruby on Rails", "Phoenix", "Gin", "Echo",
    # Databases
    "SQL", "PostgreSQL", "MySQL", "SQLite", "Oracle", "SQL Server", "MongoDB", "Redis",
    "Cassandra", "DynamoDB", "CouchDB", "Neo4j", "Elasticsearch", "InfluxDB",
    # Data Science & ML
    "TensorFlow", "PyTorch", "Keras", "scikit-learn", "pandas", "numpy", "scipy",
    "Matplotlib", "Seaborn", "Plotly", "Jupyter", "Apache Spark", "Hadoop", "Hive",
    "Machine Learning", "Deep Learning", "Data Science", "NLP", "Computer Vision",
    "Natural Language Processing", "Reinforcement Learning", "Neural Networks",
    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes", "K8s", "Terraform",
    "Ansible", "Jenkins", "GitLab CI", "GitHub Actions", "CircleCI", "Travis CI",
    "CloudFormation", "Lambda", "EC2", "S3", "RDS", "VPC", "IAM", "CloudWatch",
    # Tools & Platforms
    "Git", "SVN", "Mercurial", "JIRA", "Confluence", "Trello", "Asana", "Slack",
    "Salesforce", "Tableau", "Power BI", "Looker", "Qlik", "Excel", "Bloomberg Terminal",
    "Splunk", "Datadog", "New Relic", "Grafana", "Prometheus",
    # Frontend Technologies
    "HTML", "CSS", "SASS", "SCSS", "Less", "Tailwind CSS", "Bootstrap", "Material-UI",
    "Ant Design", "Chakra UI", "Styled Components", "Webpack", "Vite", "Parcel",
    "Babel", "ESLint", "Prettier", "Jest", "Cypress", "Selenium", "Playwright",
    # APIs & Architecture
    "REST API", "GraphQL", "gRPC", "SOAP", "Microservices", "Serverless", "Event-Driven",
    "Message Queue", "RabbitMQ", "Apache Kafka", "Redis Pub/Sub", "WebSocket",
    # Operating Systems & Scripting
    "Linux", "Unix", "Windows", "macOS", "Shell Scripting", "Bash", "PowerShell",
    "Zsh", "Cron", "System Administration",
    # Security
    "OAuth", "JWT", "SSL", "TLS", "Encryption", "Penetration Testing", "OWASP",
    # Methodologies
    "Agile", "Scrum", "Kanban", "DevOps", "CI/CD", "TDD", "BDD", "Pair Programming",
    # Finance & Trading
    "Quantitative Finance", "Algorithmic Trading", "Risk Management", "Derivatives",
    # Other
    "Blockchain", "Ethereum", "Solidity", "Smart Contracts", "Web3",
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
    """Find skills using semantic similarity with embeddings - improved to handle lowercase and context."""
    if skill_embedder is None:
        return set()
    
    # Improved extraction: look for technical terms regardless of case
    # Extract n-grams (1-3 words) that might be skills
    words = text.split()
    potential_skills = []
    
    # Extract potential skill phrases (1-3 word n-grams)
    for i in range(len(words)):
        # Single word (if it looks technical)
        word = words[i].strip('.,;:!?()[]{}')
        if len(word) > 2 and (word[0].isupper() or word.islower()):
            # Check if it's a known technical term pattern
            if any(char.isdigit() for char in word) or word.lower() in ['api', 'sdk', 'ide', 'ui', 'ux', 'ci', 'cd']:
                potential_skills.append(word)
            elif word[0].isupper() or (word.islower() and len(word) > 4):
                potential_skills.append(word)
        
        # Two-word phrases
        if i + 1 < len(words):
            word2 = words[i + 1].strip('.,;:!?()[]{}')
            phrase = f"{word} {word2}"
            # Include if at least one word is capitalized or both are lowercase technical terms
            if (word[0].isupper() or word2[0].isupper()) or (word.islower() and word2.islower() and len(phrase) > 6):
                potential_skills.append(phrase)
        
        # Three-word phrases (for skills like "Machine Learning", "Natural Language Processing")
        if i + 2 < len(words):
            word2 = words[i + 1].strip('.,;:!?()[]{}')
            word3 = words[i + 2].strip('.,;:!?()[]{}')
            phrase = f"{word} {word2} {word3}"
            if word[0].isupper() and word2[0].isupper():
                potential_skills.append(phrase)
    
    # Remove duplicates and filter out common non-technical words
    potential_skills = list(set(potential_skills))
    common_words = {'the', 'and', 'or', 'but', 'with', 'for', 'from', 'this', 'that', 'these', 'those'}
    potential_skills = [p for p in potential_skills if p.lower() not in common_words and len(p) > 2]
    
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


def extract_skills_from_bullets(bullets: List[str], skill_vocab: Optional[List[str]] = None) -> Dict[str, Set[str]]:
    """
    Extract skills per bullet point for better context.
    Returns a dict mapping bullet index to set of skills found in that bullet.
    """
    if skill_vocab is None:
        skill_vocab = load_skill_vocabulary()
    
    bullet_skills = {}
    for idx, bullet in enumerate(bullets):
        if bullet.strip():
            skills = extract_skills(bullet, skill_vocab)
            if skills:
                bullet_skills[idx] = skills
    
    return bullet_skills


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


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
    """Extract skills using spaCy PhraseMatcher with optimized lookup."""
    if nlp is None:
        return set()
    
    # Prebuild lookup dict for O(1) case recovery (performance improvement)
    skill_lookup = {skill.lower(): skill for skill in skill_vocab}
    
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(skill.lower()) for skill in skill_vocab]
    matcher.add("SKILLS", patterns)
    
    doc = nlp(text.lower())
    matches = matcher(doc, as_spans=True)
    
    found_skills = set()
    for match in matches:
        # O(1) lookup instead of O(n) loop
        matched_lower = match.text.lower()
        if matched_lower in skill_lookup:
            found_skills.add(skill_lookup[matched_lower])
    
    return found_skills


def find_semantic_skills(text: str, skill_vocab: List[str], threshold: float = 0.6) -> Set[str]:
    """Find skills using semantic similarity with embeddings - improved precision with POS filtering."""
    if skill_embedder is None:
        return set()
    
    # Use spaCy for better candidate extraction with POS tagging
    if nlp is None:
        # Fallback to simple extraction if spaCy not available
        words = text.split()
        potential_skills = []
        for i in range(len(words)):
            word = words[i].strip('.,;:!?()[]{}')
            if len(word) > 2 and word[0].isupper():
                potential_skills.append(word)
            if i + 1 < len(words):
                word2 = words[i + 1].strip('.,;:!?()[]{}')
                if word[0].isupper() and word2[0].isupper():
                    potential_skills.append(f"{word} {word2}")
    else:
        # Use spaCy for better noun phrase extraction
        doc = nlp(text)
        potential_skills = []
        
        # Extract noun phrases and proper nouns (more likely to be skills)
        for chunk in doc.noun_chunks:
            # Filter: must be 1-3 words, not too common
            if 1 <= len(chunk) <= 3:
                phrase = chunk.text.strip('.,;:!?()[]{}')
                if len(phrase) > 2:
                    potential_skills.append(phrase)
        
        # Also extract capitalized sequences (technical terms)
        for token in doc:
            if token.is_upper and len(token.text) > 2:
                potential_skills.append(token.text)
            # Check for multi-word capitalized sequences
            if token.is_title and token.i + 1 < len(doc):
                next_token = doc[token.i + 1]
                if next_token.is_title:
                    potential_skills.append(f"{token.text} {next_token.text}")
    
    # Filter out common stopwords and non-technical patterns
    common_words = {
        'the', 'and', 'or', 'but', 'with', 'for', 'from', 'this', 'that', 'these', 'those',
        'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would', 'should', 'could',
        'can', 'may', 'might', 'must', 'shall', 'team', 'project', 'work', 'company'
    }
    
    # Filter by character patterns: avoid common verbs and stopwords
    filtered_skills = []
    for phrase in potential_skills:
        phrase_lower = phrase.lower()
        # Skip if it's a common word
        if phrase_lower in common_words:
            continue
        # Skip if it's too short or too long
        if len(phrase) < 3 or len(phrase) > 50:
            continue
        # Skip if it's mostly lowercase and looks like a verb (ends with -ed, -ing, -s)
        if phrase_lower.endswith(('ed', 'ing', 's')) and not phrase[0].isupper():
            continue
        # Keep if it has technical indicators (numbers, special chars, or is capitalized)
        if any(c.isdigit() for c in phrase) or phrase[0].isupper() or phrase_lower in ['api', 'sdk', 'ide', 'ui', 'ux', 'ci', 'cd', 'sql', 'nosql']:
            filtered_skills.append(phrase)
        # Keep multi-word capitalized phrases
        elif ' ' in phrase and any(w[0].isupper() for w in phrase.split()):
            filtered_skills.append(phrase)
    
    potential_skills = list(set(filtered_skills))
    
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


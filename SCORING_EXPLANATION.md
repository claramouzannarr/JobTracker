# Resume Evaluation Scoring Breakdown

## What "Dates Missing" Means

**"Dates missing"** refers to the absence of **employment dates** (years) in the Experience section of your resume. The system searches for 4-digit years (like "2020", "2021", etc.) anywhere in the resume text.

**Why it matters:**
- Recruiters need to see when you worked at each company to understand your career timeline
- Missing dates make it harder to assess your experience level and career progression
- It's a basic resume requirement that ATS systems expect

**Penalty:** If no dates are found, the Experience Density score is reduced by 2 points (out of 15).

---

## Section 1: Format & Structure Score (100 points total)

Evaluates the basic structure and organization of your resume.

### 1. Required Sections (30 points)
**What it checks:** Presence of essential resume sections
- **Header** (contact info): Email, phone, or links (LinkedIn/GitHub)
- **Experience** section
- **Education** section  
- **Skills** section

**Scoring:**
- 30 points if all 4 sections are present
- Pro-rated: (found_sections / 4) × 30
- Example: 3/4 sections = 22.5 points

### 2. Section Ordering (20 points)
**What it checks:** Whether sections appear in the recommended order

**Recommended order:**
- **For graduates:** Header → Summary → Education → Experience → Skills
- **For experienced:** Header → Summary → Experience → Skills → Education

**Scoring:**
- 20 points if ≥80% match with recommended order
- 10 points if <80% match
- 0 points if sections are completely out of order

### 3. Page Count (20 points)
**What it checks:** Resume length appropriateness

**Recommended:**
- **Graduates:** 1 page maximum
- **Experienced:** 2 pages maximum

**Scoring:**
- 20 points if within recommended page count
- 10 points if 1 page over (e.g., 2 pages for grad, 3 pages for experienced)
- 0 points if 2+ pages over

### 4. Bullet Consistency (30 points)
**What it checks:** Consistency in number of bullet points across experience entries

**Scoring:**
- 30 points if difference ≤ 2 bullets (e.g., all entries have 3-5 bullets)
- 20 points if difference ≤ 4 bullets (e.g., entries range from 2-6 bullets)
- 10 points if difference > 4 bullets (e.g., entries range from 1-8 bullets)
- 0 points if no experience items found

**Example:** If you have 3 jobs with 4, 5, and 4 bullets respectively → difference is 1 → 30 points ✓

---

## Section 2: Grammar & Spelling Score (100 points total)

Evaluates grammar, spelling, and language quality.

### Grammar & Spelling (100 points)
**What it checks:** Grammar and spelling errors in Summary and Experience bullet points

**Scoring:**
- **100 points** = Perfect, 0 errors
- **60-99 points** = Based on errors per 100 words
  - Formula: `100 - min(40, errors_per_100_words × 2)`
  - Minimum score is 60 (even with many errors)
  - Example: 10 errors per 100 words = 100 - 20 = 80 points

**What counts as errors:**
- Spelling mistakes
- Grammar mistakes (subject-verb agreement, tense, etc.)
- Punctuation errors
- Style issues detected by LanguageTool

**Note:** Only checks Summary section and Experience bullet points (not full resume text)

---

## Section 3: ATS Content Depth Score (100 points total)

Evaluates the quality and depth of content that ATS systems and recruiters look for.

### 1. Cliché Detection (20 points)
**What it checks:** Overused phrases that make your resume generic

**Common clichés detected:**
- "hardworking", "team player", "detail-oriented"
- "self-motivated", "quick learner"
- "think outside the box", "go-getter"
- "results-driven", "proven track record"
- "excellent communication skills"
- "duties included", "helped with", "assisted in"

**Scoring:**
- 20 points = No clichés found
- Penalty: -3 points per cliché found (max -20 points)
- Example: 3 clichés = 20 - 9 = 11 points

### 2. Action Verb Quality (20 points)
**What it checks:** Whether bullet points start with strong, impactful action verbs

**Strong verbs (examples):**
- "led", "built", "designed", "optimized", "implemented"
- "developed", "created", "improved", "increased"
- "achieved", "managed", "delivered", "launched"
- "transformed", "architected", "engineered", "automated"

**Weak verbs (examples):**
- "worked on", "helped with", "assisted in"
- "was responsible for", "did", "made"

**Scoring:**
- Formula: `(strong_verb_ratio × 20) - (weak_verb_ratio × 10)`
- Example: 60% strong verbs, 10% weak verbs = (0.6 × 20) - (0.1 × 10) = 12 - 1 = 11 points
- Minimum: 0 points

### 3. Quantification & KPIs (30 points)
**What it checks:** Whether bullet points include numbers, metrics, percentages, or financial data

**What counts as quantification:**
- Numbers: "increased sales by 25%"
- Percentages: "improved efficiency by 30%"
- Currency: "$1M revenue", "€500K budget"
- Counts: "managed team of 10", "processed 1000+ requests"
- Time: "reduced processing time by 50%"

**Scoring:**
- 30 points if ≥66% of bullets have numbers (target: 2 out of 3 bullets)
- 20 points if 50-65% of bullets have numbers
- 10 points if <50% of bullets have numbers
- 0 points if no bullets found

**Example:** 10 bullets, 7 have numbers = 70% = 30 points ✓

### 4. Skill Demonstrated Index - SDI (15 points)
**What it checks:** How well you demonstrate skills through actual work (not just listing them)

**How it works:**
- Extracts skills from **Experience** bullets (weight: 1.0)
- Extracts skills from **Projects** bullets (weight: 0.8)
- Extracts skills from **Skills** section (weight: 0.4)
- Extracts skills from **Summary** (weight: 0.3)

**Why weights matter:** Skills mentioned in Experience/Projects show you actually used them, while skills just listed are less credible.

**Scoring:**
- Calculates weighted skill count: `(exp_skills × 1.0) + (proj_skills × 0.8) + (skills_section × 0.4) + (summary × 0.3)`
- Converts to 0-100 scale, then to 15-point scale
- Example: SDI score of 80% = (80/100) × 15 = 12 points

### 5. Experience Density (15 points)
**What it checks:** Number of experience entries and presence of dates

**Scoring:**
- **15 points** if ≥3 experience entries AND dates present
- **13 points** if ≥3 experience entries BUT no dates (-2 penalty)
- **10 points** if 2 experience entries AND dates present
- **8 points** if 2 experience entries BUT no dates (-2 penalty)
- **5 points** if 1 experience entry AND dates present
- **3 points** if 1 experience entry BUT no dates (-2 penalty)
- **0 points** if no experience entries

**What "dates" means:** The system searches for 4-digit years (like "2020-2022", "Jan 2021 - Dec 2023") anywhere in the resume text.

---

## Section 4: Job Compatibility Score (100 points total)

**Only calculated when a job description is provided.**

Evaluates how well your resume matches a specific job posting.

### Skill Coverage (70% of score)
**What it checks:** How many required skills from the job description appear in your resume

**How it works:**
- Extracts skills from job description using PhraseMatcher + semantic matching
- Extracts skills from your resume (prioritizing demonstrated skills from Experience/Projects)
- Calculates: `(matched_skills / required_skills) × 100`

**Scoring:**
- Coverage percentage × 70 points
- Example: 80% skill coverage = 0.8 × 70 = 56 points

### Semantic Similarity (30% of score)
**What it checks:** Overall content similarity between your resume and job description

**How it works:**
- Uses AI embeddings (SentenceTransformer) to compare full resume text vs. job description
- Calculates cosine similarity (0-1 scale)

**Scoring:**
- Similarity score × 30 points
- Example: 0.85 similarity = 0.85 × 30 = 25.5 points

### Final Score
**Formula:** `(Skill Coverage × 0.7) + (Semantic Similarity × 0.3)`

**Example:**
- Skill Coverage: 80% → 56 points
- Semantic Similarity: 85% → 25.5 points
- **Total: 81.5 points**

---

## Summary: Point Totals

| Section | Max Points | What It Evaluates |
|---------|------------|-------------------|
| **Format & Structure** | 100 | Sections present, ordering, page count, bullet consistency |
| **Grammar & Spelling** | 100 | Grammar/spelling errors in summary and bullets |
| **ATS Content Depth** | 100 | Clichés, action verbs, quantification, skills demonstration, experience density |
| **Job Compatibility** | 100 | Skill match + semantic similarity (only when JD provided) |

---

## Overall Score Calculation

The overall score is a weighted average:

**When Job Description is provided:**
- Format: 25%
- ATS: 25%
- Job Compatibility: 25%
- Grammar: 10%
- Skills Coverage: 0% (already in ATS)

**When NO Job Description:**
- Format: 30%
- ATS: 35%
- Grammar: 10%
- Skills Coverage: 15% (uses ATS as proxy)
- Job Compatibility: 0%

**Example with JD:**
- Format: 85 → 21.25 points
- ATS: 75 → 18.75 points
- Job Compatibility: 80 → 20 points
- Grammar: 95 → 9.5 points
- **Overall: 69.5/100**

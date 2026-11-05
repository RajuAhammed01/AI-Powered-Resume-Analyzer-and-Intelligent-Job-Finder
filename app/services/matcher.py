"""
JobSnap — Intelligent Matching Engine
======================================
Multi-signal scoring that goes beyond keyword frequency:
- Focused semantic similarity (strips boilerplate from both resume & job)
- Job title alignment via Sentence-BERT
- Experience relevance extraction
- Education & qualification matching

All functions are stateless and used by skill_gap.py for final scoring.
"""

import re
import warnings

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from sentence_transformers import SentenceTransformer
    _MODEL = None
except ImportError:
    _MODEL = False

_EMBED_CACHE = {}


def get_sentence_transformer():
    global _MODEL
    if _MODEL is False:
        return None
    if _MODEL is None:
        try:
            # Load small model for fast CPU inference
            _MODEL = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception:
            _MODEL = False
            return None
    return _MODEL


def _get_embedding(text: str):
    model = get_sentence_transformer()
    if model is None:
        return None
    key = (len(text), text[:250])
    if key not in _EMBED_CACHE:
        _EMBED_CACHE[key] = model.encode(text)
    return _EMBED_CACHE[key]


def basic_match_score(resume_skills, job_skills):
    if not job_skills:
        return 0
    matched = set(resume_skills) & set(job_skills)
    return int((len(matched) / len(set(job_skills))) * 100)


# ── Boilerplate stripping ─────────────────────────────────────────────────────

# Common filler in job descriptions that inflates cosine similarity without
# carrying any meaningful professional signal.
_JOB_BOILERPLATE_PATTERNS = [
    r"(?i)equal\s+opportunity\s+employer.*?(?:\n|$)",
    r"(?i)we\s+are\s+(?:an?\s+)?(?:equal|diverse|inclusive).*?(?:\n|$)",
    r"(?i)benefits?\s*(?:include|:).*?(?=\n\n|\Z)",
    r"(?i)(?:health|dental|vision|401k|pto|insurance|vacation)\s+(?:plan|benefit|coverage).*?(?:\n|$)",
    r"(?i)salary\s*(?:range)?:?\s*\$[\d,]+.*?(?:\n|$)",
    r"(?i)about\s+(?:us|the\s+company|our\s+team).*?(?=\n\n|\Z)",
    r"(?i)apply\s+(?:now|here|today|by).*?(?:\n|$)",
    r"(?i)how\s+to\s+apply.*?(?:\n|$)",
]

# Common filler in resumes that doesn't represent skill or experience signal.
_RESUME_BOILERPLATE_PATTERNS = [
    r"(?i)curriculum\s+vitae",
    r"(?i)references?\s+(?:available|upon|on)\s+request",
    r"(?i)personal\s+(?:information|details)\s*:",
    r"(?i)date\s+of\s+birth.*?(?:\n|$)",
    r"(?i)nationality.*?(?:\n|$)",
    r"(?i)marital\s+status.*?(?:\n|$)",
    r"(?i)passport\s+no.*?(?:\n|$)",
]


def _strip_boilerplate(text: str, patterns: list[re.Pattern]) -> str:
    """Remove boilerplate sections from text to focus on professional content."""
    cleaned = text
    for pat in patterns:
        cleaned = re.sub(pat, " ", cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def _extract_core_requirements(job_desc: str) -> str:
    """
    Extract the requirements/responsibilities/qualifications section from a
    job description, discarding company overview and benefits boilerplate.
    Falls back to the full (cleaned) description if no section is found.
    """
    # Try to find requirements / qualifications / responsibilities sections
    section_pattern = re.compile(
        r"(?:^|\n)\s*(?:requirements?|qualifications?|what\s+(?:you(?:'ll)?\s+)?(?:need|bring)"
        r"|must\s+have|responsibilities|key\s+skills|technical\s+skills"
        r"|what\s+we(?:'re)?\s+looking\s+for|your\s+(?:role|responsibilities)|job\s+duties)"
        r"\s*:?",
        re.IGNORECASE,
    )

    matches = list(section_pattern.finditer(job_desc))
    if matches:
        # Take everything from the first match to the end,
        # then strip standard boilerplate.
        start = matches[0].start()
        core = job_desc[start:]
        return _strip_boilerplate(core, _JOB_BOILERPLATE_PATTERNS)

    return _strip_boilerplate(job_desc, _JOB_BOILERPLATE_PATTERNS)


def _build_resume_signal(resume_text: str, resume_skills: list[str] = None,
                         experience_text: str = "", education_text: str = "") -> str:
    """
    Build a focused signal string from the resume that emphasises professional
    content (skills, experience, projects, education) over noise (address,
    dates, formatting artefacts).
    """
    parts = []

    # Skills keywords — explicitly repeated so they have high TF weight
    if resume_skills:
        parts.append("Technical Skills: " + ", ".join(resume_skills))

    # Experience section — the richest professional signal
    if experience_text and experience_text.strip():
        parts.append(experience_text.strip())
    else:
        # Fallback: try to extract experience from full text
        exp_match = re.search(
            r"(?:experience|employment|work\s+history)\s*:?\s*\n(.*?)(?=\n\s*(?:education|skills|projects|certifications)\s*:?|\Z)",
            resume_text, re.IGNORECASE | re.DOTALL,
        )
        if exp_match:
            parts.append(exp_match.group(1).strip())

    # Education section
    if education_text and education_text.strip():
        parts.append(education_text.strip())

    # Projects section
    proj_match = re.search(
        r"(?:projects?|portfolio|key\s+achievements?)\s*:?\s*\n(.*?)(?=\n\s*(?:education|skills|experience|certifications)\s*:?|\Z)",
        resume_text, re.IGNORECASE | re.DOTALL,
    )
    if proj_match:
        parts.append(proj_match.group(1).strip())

    if not parts:
        # Last resort — use the whole text, stripped of boilerplate
        return _strip_boilerplate(resume_text, _RESUME_BOILERPLATE_PATTERNS)

    combined = "\n".join(parts)
    return _strip_boilerplate(combined, _RESUME_BOILERPLATE_PATTERNS)


# ── Public scoring functions ──────────────────────────────────────────────────

def tfidf_cosine_score(resume_text: str, job_description: str) -> int:
    """
    Legacy API — raw text similarity.  Kept for backward compatibility.
    New code should call focused_semantic_score() instead.
    """
    if not resume_text.strip() or not job_description.strip():
        return 0

    emb_resume = _get_embedding(resume_text)
    if emb_resume is not None:
        emb_job = _get_embedding(job_description)
        if emb_job is not None:
            return int(cosine_similarity([emb_resume], [emb_job])[0][0] * 100)

    # Fallback to TF-IDF
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform([resume_text, job_description])
    return int(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100)


def focused_semantic_score(resume_text: str, job_description: str,
                           resume_skills: list[str] = None,
                           experience_text: str = "",
                           education_text: str = "") -> int:
    """
    Compute semantic similarity after stripping boilerplate from both sides
    and concentrating on professional signal (skills, experience, projects).
    """
    if not resume_text.strip() or not job_description.strip():
        return 0

    resume_signal = _build_resume_signal(resume_text, resume_skills, experience_text, education_text)
    job_signal = _extract_core_requirements(job_description)

    if not resume_signal.strip() or not job_signal.strip():
        # Fallback to full-text comparison
        return tfidf_cosine_score(resume_text, job_description)

    emb_resume = _get_embedding(resume_signal)
    if emb_resume is not None:
        emb_job = _get_embedding(job_signal)
        if emb_job is not None:
            score = cosine_similarity([emb_resume], [emb_job])[0][0]
            return int(max(0, min(100, score * 100)))

    # Fallback to TF-IDF on cleaned texts
    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf = vectorizer.fit_transform([resume_signal, job_signal])
        return int(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100)
    except Exception:
        return 0


def title_alignment_score(
    candidate_title: str,
    job_title: str,
    candidate_domain: str = "",
    job_domain: str = "",
) -> int:
    """
    Score how well the candidate's professional title/role matches the job title.
    Integrates career domain intelligence to ensure roles in the same domain
    (e.g., Frontend Developer & React Developer, or ML Engineer & Data Analyst)
    receive high compatibility, while unrelated career categories are penalized.
    Returns 0-100.
    """
    if not candidate_title or not job_title:
        return 40

    c = candidate_title.strip().lower()
    j = job_title.strip().lower()

    # Determine career domains if not provided
    from app.services.profile_detector import (
        classify_job_domain,
        is_job_domain_compatible,
    )

    cand_dom = candidate_domain or classify_job_domain(candidate_title)["domain"]
    j_dom = job_domain or classify_job_domain(job_title)["domain"]

    is_compatible, domain_mult, _ = is_job_domain_compatible(cand_dom, j_dom)

    # If completely unrelated domain (e.g. Sales, Accounting, or Frontend vs Data/ML)
    if not is_compatible:
        return max(5, int(15 * domain_mult))

    # Exact or near-exact match
    if c == j or c in j or j in c:
        return 96

    # Both within same technical domain
    same_domain = (cand_dom == j_dom) and (cand_dom != "general_tech")

    # Domain specific high-priority synergies explicitly requested
    if cand_dom == "frontend" and any(k in j for k in ["frontend", "front-end", "react", "vue", "ui developer", "ui engineer"]):
        return 95
    if cand_dom == "data_ml" and any(k in j for k in ["machine learning", "data scientist", "data analyst", "ai engineer", "deep learning"]):
        return 95

    raw_score = 0
    # Sentence-BERT similarity on titles
    emb_c = _get_embedding(f"job title: {candidate_title}")
    if emb_c is not None:
        emb_j = _get_embedding(f"job title: {job_title}")
        if emb_j is not None:
            sim = float(cosine_similarity([emb_c], [emb_j])[0][0])
            if sim >= 0.85:
                raw_score = 92
            elif sim >= 0.40:
                raw_score = int(35 + (sim - 0.40) * (57 / 0.45))
            else:
                raw_score = int(sim * 75)

    if raw_score == 0:
        # Keyword overlap fallback
        role_tokens = {
            "engineer", "developer", "programmer", "architect", "scientist",
            "analyst", "consultant", "manager", "lead", "specialist", "designer",
            "administrator", "devops", "intern", "trainee", "director", "head",
        }
        domain_tokens = {
            "software", "backend", "frontend", "fullstack", "full-stack",
            "data", "machine learning", "ml", "ai", "deep learning", "cloud",
            "mobile", "web", "ios", "android", "security", "network", "database",
            "qa", "test", "embedded", "systems", "platform", "infrastructure",
            "product", "project", "ux", "ui", "react",
        }

        c_words = set(c.replace("-", " ").split())
        j_words = set(j.replace("-", " ").split())

        role_overlap = c_words & j_words & role_tokens
        domain_overlap = c_words & j_words & domain_tokens
        total_signal = len(role_overlap) + len(domain_overlap)

        if total_signal >= 2:
            raw_score = 75
        elif total_signal == 1:
            raw_score = 50
        else:
            raw_score = 30

    if same_domain:
        raw_score = max(raw_score, 85)

    # Scale by domain compatibility multiplier
    final_score = int(round(raw_score * domain_mult))
    return max(5, min(98, final_score))


def extract_experience_years(text: str) -> float:
    """
    Extract the most prominent 'years of experience' figure from resume text.
    Returns 0.0 if not found.
    """
    patterns = [
        # "5+ years of experience", "5 years experience", "over 5 years"
        r"(\d+)\+?\s*(?:years?|yrs?)[\s\-]+(?:of\s+)?(?:experience|work|professional)",
        r"(?:over|more\s+than|approx(?:imately)?\.?)\s*(\d+)\s*(?:years?|yrs?)",
        # "experience: 5 years"
        r"experience\s*:?\s*(\d+)\s*(?:years?|yrs?)",
    ]
    max_years = 0.0
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val = float(m.group(1))
            if 0 < val <= 40:
                max_years = max(max_years, val)

    if max_years == 0:
        # Heuristic: count distinct year ranges like "2019-2022", "Jan 2020 - Present"
        year_ranges = re.findall(
            r"(20[0-2]\d|19[89]\d)\s*[-–—]\s*(20[0-2]\d|[Pp]resent|[Cc]urrent|[Nn]ow)",
            text,
        )
        if year_ranges:
            import datetime
            current_year = datetime.datetime.now().year
            total_years = 0.0
            for start_str, end_str in year_ranges:
                start_y = int(start_str)
                if end_str.isdigit():
                    end_y = int(end_str)
                else:
                    end_y = current_year
                span = max(0, end_y - start_y)
                total_years += span
            max_years = min(total_years, 30.0)

    return max_years


def experience_relevance_score(resume_text: str, job_description: str,
                               experience_text: str = "") -> int:
    """
    Score how relevant the candidate's work experience is to the job.
    Considers years of experience, domain keyword overlap in experience section,
    and seniority alignment.
    Returns 0-100.
    """
    if not resume_text.strip():
        return 0

    score = 0.0
    exp_text = experience_text if experience_text else resume_text
    candidate_years = extract_experience_years(resume_text)

    # A) Years of experience vs. job requirements
    job_years = 0.0
    for pat in [r"(\d+)\+?\s*(?:years?|yrs?)", r"minimum\s+(\d+)\s+(?:years?|yrs?)"]:
        m = re.search(pat, job_description, re.IGNORECASE)
        if m:
            job_years = float(m.group(1))
            break

    if job_years > 0:
        if candidate_years >= job_years:
            score += 40  # Meets or exceeds requirement
        elif candidate_years >= job_years * 0.6:
            score += 25  # Close enough
        elif candidate_years > 0:
            score += 10  # Some experience
    else:
        # Job doesn't specify years — reward having any experience
        if candidate_years >= 3:
            score += 35
        elif candidate_years >= 1:
            score += 25
        elif candidate_years > 0:
            score += 15
        else:
            score += 10  # No detectable years

    # B) Domain keyword overlap between experience section and job description
    # Extract meaningful domain terms (3+ chars) from job description
    job_lower = job_description.lower()
    exp_lower = exp_text.lower()

    # Get distinctive terms from the job description (not stop words)
    domain_terms = set()
    for word in re.findall(r"\b[a-z]{4,}\b", job_lower):
        if word not in {"with", "have", "that", "this", "from", "will", "your",
                        "they", "been", "their", "were", "would", "about", "which",
                        "when", "make", "like", "time", "just", "know", "take",
                        "come", "could", "than", "look", "only", "into", "year",
                        "most", "also", "work", "team", "role", "join", "more",
                        "other", "some", "what", "well", "should", "able", "each",
                        "must", "need", "very", "such", "including", "based",
                        "using", "experience", "required", "preferred", "strong"}:
            domain_terms.add(word)

    if domain_terms:
        overlap = sum(1 for t in domain_terms if t in exp_lower)
        ratio = overlap / max(1, len(domain_terms))
        score += min(40, int(ratio * 60))
    else:
        score += 15

    # C) Seniority signal
    senior_keywords = {"senior", "lead", "principal", "staff", "head", "director", "vp", "manager"}
    junior_keywords = {"junior", "intern", "trainee", "entry", "associate", "graduate"}

    job_is_senior = any(k in job_lower for k in senior_keywords)
    job_is_junior = any(k in job_lower for k in junior_keywords)
    resume_is_senior = any(k in resume_text.lower() for k in senior_keywords)
    resume_is_junior = any(k in resume_text.lower() for k in junior_keywords)

    if job_is_senior and resume_is_senior:
        score += 20
    elif job_is_junior and (resume_is_junior or candidate_years <= 2):
        score += 20
    elif not job_is_senior and not job_is_junior:
        score += 15  # Mid-level, no strong signal either way
    else:
        score += 5   # Mismatch

    return int(min(100, max(0, score)))


def education_qualification_score(resume_text: str, job_description: str,
                                  education_text: str = "") -> int:
    """
    Score alignment of education and certifications with the job requirements.
    Returns 0-100.
    """
    score = 0.0
    edu_text = education_text.lower() if education_text else ""
    full_lower = resume_text.lower()
    job_lower = job_description.lower()

    # Use education text if available, else full resume
    search_text = edu_text if edu_text else full_lower

    # A) Degree level detection (30 pts max)
    degree_level = 0
    if re.search(r"\b(?:ph\.?d|doctor(?:ate)?|d\.?phil)\b", search_text):
        degree_level = 4
    elif re.search(r"\b(?:m\.?s\.?c?\.?|master(?:'?s)?|m\.?tech|m\.?eng|mba)\b", search_text):
        degree_level = 3
    elif re.search(r"\b(?:b\.?s\.?c?\.?|bachelor(?:'?s)?|b\.?tech|b\.?eng|b\.?a\.?)\b", search_text):
        degree_level = 2
    elif re.search(r"\b(?:diploma|associate|certificate|certification)\b", search_text):
        degree_level = 1

    # Check what the job requires
    job_wants_phd = bool(re.search(r"\b(?:ph\.?d|doctorate)\b", job_lower))
    job_wants_masters = bool(re.search(r"\b(?:master(?:'?s)?|m\.?s\.?c?\.?)\b", job_lower))
    job_wants_bachelors = bool(re.search(r"\b(?:bachelor(?:'?s)?|b\.?s\.?c?\.?|degree)\b", job_lower))

    if job_wants_phd:
        if degree_level >= 4:
            score += 30
        elif degree_level >= 3:
            score += 20
        elif degree_level >= 2:
            score += 10
    elif job_wants_masters:
        if degree_level >= 3:
            score += 30
        elif degree_level >= 2:
            score += 20
        elif degree_level >= 1:
            score += 10
    elif job_wants_bachelors:
        if degree_level >= 2:
            score += 30
        elif degree_level >= 1:
            score += 20
    else:
        # Job doesn't specify degree — give baseline credit for any degree
        score += min(25, degree_level * 8)

    # B) Field relevance (35 pts max)
    relevant_fields = {
        "computer science", "software engineering", "information technology",
        "computer engineering", "data science", "artificial intelligence",
        "machine learning", "mathematics", "statistics", "electrical engineering",
        "information systems", "cyber security", "computational",
    }
    field_match = any(f in search_text for f in relevant_fields)
    job_mentions_cs = any(f in job_lower for f in relevant_fields)

    if field_match and job_mentions_cs:
        score += 35  # Relevant field aligned with job
    elif field_match:
        score += 25  # Has relevant field, job doesn't specify
    elif degree_level >= 2:
        score += 15  # Has a degree in an unspecified field
    else:
        score += 5

    # C) Certifications & qualifications mentioned in job that appear in resume (35 pts max)
    cert_patterns = [
        r"(?:aws|azure|gcp|google\s+cloud)\s+certif",
        r"(?:pmp|scrum\s+master|csm|cissp|ceh|ccna|ccnp)",
        r"(?:certified|certification|certificate)\s+\w+",
        r"(?:tensorflow|kubernetes|docker)\s+certif",
    ]
    cert_score = 0
    for pat in cert_patterns:
        if re.search(pat, job_lower) and re.search(pat, full_lower):
            cert_score += 12

    score += min(35, cert_score)

    return int(min(100, max(0, score)))


# ── Projects & Practical Portfolio Scoring ───────────────────────────────────

def extract_projects_text(resume_text: str) -> str:
    """
    Extracts the projects or portfolio section from resume text.
    """
    if not resume_text:
        return ""
    patterns = [
        r"(?:^|\n)\s*(?:academic\s+projects?|personal\s+projects?|key\s+projects?|featured\s+projects?|projects?|portfolio)\s*:?\s*\n(.*?)(?=\n\s*(?:education|experience|work\s+history|skills|certifications|awards|publications|languages)\s*:?|\Z)",
    ]
    for pat in patterns:
        m = re.search(pat, resume_text, re.IGNORECASE | re.DOTALL)
        if m:
            content = m.group(1).strip()
            if len(content) > 20:
                return content[:2500]
    return ""


def extract_job_responsibilities(job_description: str) -> str:
    """
    Extracts the day-to-day duties/responsibilities section from a job description.
    """
    if not job_description:
        return ""
    patterns = [
        r"(?:^|\n)\s*(?:responsibilities|duties|what\s+you(?:'ll)?\s+do|key\s+responsibilities|day\s+to\s+day|your\s+role|role\s+overview|what\s+you'll\s+be\s+doing)\s*:?\s*\n(.*?)(?=\n\s*(?:requirements?|qualifications?|skills|what\s+we\s+offer|benefits|about\s+us|who\s+you\s+are)\s*:?|\Z)",
    ]
    for pat in patterns:
        m = re.search(pat, job_description, re.IGNORECASE | re.DOTALL)
        if m:
            content = m.group(1).strip()
            if len(content) > 20:
                return content[:2500]
    return job_description[:1200]


def project_portfolio_score(
    resume_text: str,
    job_description: str,
    projects_text: str = "",
    job_skills: list[str] = None,
    is_internship_seeking: bool = False,
) -> tuple[int, str]:
    """
    Evaluates practical implementation experience from projects, portfolio, and GitHub work.
    Returns (score 0-100, rationale).
    """
    proj = projects_text.strip() if projects_text else extract_projects_text(resume_text)
    full_lower = (resume_text or "").lower()
    proj_lower = proj.lower() if proj else full_lower
    job_lower = (job_description or "").lower()

    score = 0
    reasons = []

    # 1. Evidence of practical projects / GitHub portfolio
    has_proj_section = bool(proj)
    has_github = bool(re.search(r"\bgithub\.com/[a-zA-Z0-9_\-\.]+", resume_text or "", re.IGNORECASE))
    has_demo_links = bool(re.search(r"https?://[a-zA-Z0-9_\-\.]+", proj))

    if has_proj_section:
        score += 30
        reasons.append("Structured project portfolio demonstrated in resume")
    elif re.search(r"\b(project|portfolio|built|developed|implemented)\b", full_lower):
        score += 20
        reasons.append("Practical implementation details found across work history")
    else:
        score += 10

    if has_github or has_demo_links:
        score += 15
        reasons.append("Verifiable code repository / live project demonstration links provided")

    # 2. Technology overlap inside project descriptions
    matched_proj_skills = []
    if job_skills:
        for s in job_skills:
            if len(s) > 2 and re.search(r"\b" + re.escape(s.lower()) + r"\b", proj_lower):
                matched_proj_skills.append(s)

    if matched_proj_skills:
        skill_pts = min(40, len(matched_proj_skills) * 10)
        score += skill_pts
        reasons.append(f"Projects demonstrate hands-on implementation of {', '.join(matched_proj_skills[:4])}")
    else:
        tech_words = re.findall(r"\b[a-zA-Z]{4,}\b", job_lower)
        tech_overlap = [w for w in set(tech_words) if len(w) > 3 and w in proj_lower]
        if len(tech_overlap) >= 5:
            score += 25
            reasons.append("Relevant technical problem solving reflected in projects")
        else:
            score += 10

    # 3. Action and outcome orientation
    action_verbs = [
        "built", "developed", "implemented", "designed", "created", "deployed",
        "integrated", "architected", "optimized", "trained", "scaled", "automated"
    ]
    actions_found = [v for v in action_verbs if re.search(r"\b" + v + r"\b", proj_lower)]
    if len(actions_found) >= 3:
        score += 15
        reasons.append(f"Action-oriented execution demonstrated ({', '.join(actions_found[:3])})")
    elif len(actions_found) >= 1:
        score += 10

    # Early career / internship candidate credit: academic/capstone projects count as qualifying evidence
    if is_internship_seeking and has_proj_section:
        score = max(score, 82)
        reasons.append("Academic / capstone projects count as qualifying technical evidence")

    final_score = min(100, max(15, score))
    rationale = "; ".join(reasons) if reasons else "Practical project implementations evaluated."
    return final_score, rationale


def responsibilities_alignment_score(
    resume_text: str,
    job_description: str,
    experience_text: str = "",
    projects_text: str = "",
) -> tuple[int, str]:
    """
    Evaluates day-to-day job responsibilities vs candidate past achievements and duties.
    Returns (score 0-100, rationale).
    """
    resp_text = extract_job_responsibilities(job_description)
    cand_text = f"{experience_text}\n{projects_text}" if (experience_text or projects_text) else resume_text

    if not resp_text.strip() or not cand_text.strip():
        return 50, "Standard day-to-day role responsibility fit."

    clean_resp = _strip_boilerplate(resp_text, _JOB_BOILERPLATE_PATTERNS)
    clean_cand = _strip_boilerplate(cand_text, _RESUME_BOILERPLATE_PATTERNS)

    emb_resp = _get_embedding(clean_resp[:1200])
    emb_cand = _get_embedding(clean_cand[:1500])

    if emb_resp is not None and emb_cand is not None:
        raw_sim = float(cosine_similarity([emb_resp], [emb_cand])[0][0])
        sim_score = int(round(max(0.1, min(1.0, raw_sim)) * 100))
    else:
        try:
            vec = TfidfVectorizer(stop_words="english")
            tfidf = vec.fit_transform([clean_resp, clean_cand])
            sim_score = int(round(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100))
        except Exception:
            sim_score = 45

    task_verbs = [
        "develop", "build", "design", "maintain", "collaborate", "test",
        "deploy", "analyze", "lead", "manage", "optimize", "deliver"
    ]
    resp_l = clean_resp.lower()
    cand_l = clean_cand.lower()
    shared_actions = [v for v in task_verbs if v in resp_l and v in cand_l]

    if shared_actions:
        sim_score = min(98, max(sim_score, 45 + len(shared_actions) * 10))
        rationale = f"Demonstrated past execution in key job duties ({', '.join(shared_actions[:4])})"
    else:
        rationale = "General alignment with day-to-day role responsibilities"

    return sim_score, rationale

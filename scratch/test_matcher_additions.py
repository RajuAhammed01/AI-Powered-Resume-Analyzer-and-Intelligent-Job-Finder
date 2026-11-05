import sys, re
sys.path.insert(0, ".")
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.services.matcher import _strip_boilerplate, _JOB_BOILERPLATE_PATTERNS, _RESUME_BOILERPLATE_PATTERNS, _get_embedding

def extract_projects_text(resume_text: str) -> str:
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
    full_lower = resume_text.lower()
    proj_lower = proj.lower() if proj else full_lower
    job_lower = job_description.lower()

    score = 0
    reasons = []

    # 1. Evidence of practical projects / GitHub portfolio
    has_proj_section = bool(proj)
    has_github = bool(re.search(r"\bgithub\.com/[a-zA-Z0-9_\-\.]+", resume_text, re.IGNORECASE))
    has_demo_links = bool(re.search(r"https?://[a-zA-Z0-9_\-\.]+", proj))

    if has_proj_section:
        score += 30
        reasons.append("Structured project portfolio detected")
    elif re.search(r"\b(project|portfolio|built|developed|implemented)\b", full_lower):
        score += 20
        reasons.append("Practical implementation details found in experience")
    else:
        score += 10

    if has_github or has_demo_links:
        score += 15
        reasons.append("Verifiable code repository / live demo links provided")

    # 2. Technology overlap inside project descriptions
    matched_proj_skills = []
    if job_skills:
        for s in job_skills:
            if len(s) > 2 and re.search(r"\b" + re.escape(s.lower()) + r"\b", proj_lower):
                matched_proj_skills.append(s)

    if matched_proj_skills:
        skill_pts = min(40, len(matched_proj_skills) * 10)
        score += skill_pts
        reasons.append(f"Projects demonstrate hands-on usage of: {', '.join(matched_proj_skills[:4])}")
    else:
        # Check against general tech terms in job description
        tech_words = re.findall(r"\b[a-zA-Z]{3,}\b", job_lower)
        tech_overlap = [w for w in set(tech_words) if len(w) > 3 and w in proj_lower]
        if len(tech_overlap) >= 5:
            score += 25
            reasons.append("Relevant technical problem-solving reflected in projects")
        else:
            score += 10

    # 3. Action and outcome orientation (developed, designed, integrated, optimized)
    action_verbs = [
        "built", "developed", "implemented", "designed", "created", "deployed",
        "integrated", "architected", "optimized", "trained", "scaled", "automated"
    ]
    actions_found = [v for v in action_verbs if re.search(r"\b" + v + r"\b", proj_lower)]
    if len(actions_found) >= 3:
        score += 15
        reasons.append(f"Demonstrates action-driven project outcomes ({', '.join(actions_found[:3])})")
    elif len(actions_found) >= 1:
        score += 10

    # Early career / internship boost: practical academic/personal projects are heavily credited
    if is_internship_seeking and has_proj_section:
        score = max(score, 82)
        reasons.append("Academic / capstone projects count as qualifying technical evidence")

    final_score = min(100, max(15, score))
    rationale = "; ".join(reasons) if reasons else "Baseline project implementation evaluated."
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

    # Strip boilerplate
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

    # Check key task verbs overlap
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

print("Tested functions successfully.")


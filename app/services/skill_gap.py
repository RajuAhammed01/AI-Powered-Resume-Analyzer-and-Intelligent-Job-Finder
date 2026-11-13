"""
JobSnap — Realistic Multi-Signal Job Match Scoring & Skill Gap Engine
====================================================================
Calculates realistic match scores based on 6 core dimensions:
  1. Technical Skill Overlap (35%): Direct verified matches, related/transferable
     frameworks, and missing competencies with priority ranking.
  2. Required Qualifications & Education (15%): Degree level, academic discipline,
     and matching professional certifications.
  3. Professional Experience (15%): Tenure vs minimum requirement, domain keyword
     density, and seniority alignment.
  4. Projects & Practical Implementation (15%): Hands-on project portfolio, GitHub
     evidence, and technology stack execution in projects.
  5. Job Responsibilities & Task Alignment (10%): Day-to-day duties from the job
     matched against candidate action statements via semantic similarity.
  6. Career Relevance & Domain Compatibility (10% + Gate): Career discipline
     alignment, strictly penalizing unrelated roles (score capped <= 18%).
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple

from app.services.matcher import (
    education_qualification_score,
    experience_relevance_score,
    extract_job_responsibilities,
    extract_projects_text,
    focused_semantic_score,
    project_portfolio_score,
    responsibilities_alignment_score,
    tfidf_cosine_score,
    title_alignment_score,
)
from app.services.profile_detector import (
    DOMAIN_TAXONOMY,
    classify_job_domain,
    classify_job_seniority,
    detect_candidate_profile,
    is_job_domain_compatible,
)


# ── Skill importance classification ──────────────────────────────────────────

# Soft / generic skills that are common across many roles and contribute
# less discriminating signal than hard technical skills.
SOFT_SKILL_KEYWORDS = {
    "leadership", "communication", "teamwork", "collaboration", "problem solving",
    "problem-solving", "time management", "critical thinking", "creativity",
    "adaptability", "flexibility", "project management", "agile", "scrum",
    "mentoring", "presentation", "negotiation", "decision making",
    "decision-making", "interpersonal", "conflict resolution", "multitasking",
    "strategic thinking", "analytical", "detail-oriented", "self-motivated",
    "organization", "planning", "management", "stakeholder management",
    "customer service", "relationship building", "emotional intelligence",
    "writing", "public speaking", "active listening", "delegation",
    "risk management", "change management",
}


def _is_soft_skill(skill_name: str) -> bool:
    """Return True if the skill is a generic / soft skill."""
    return skill_name.lower().strip() in SOFT_SKILL_KEYWORDS


def _is_core_domain_skill(skill_name: str, domain_cfg: dict = None) -> bool:
    """Return True if the skill is a primary technical competency in the career domain."""
    if not domain_cfg:
        return False
    s_clean = skill_name.lower().strip()
    core = domain_cfg.get("core_skills", set())
    return s_clean in core or any(cs in s_clean for cs in core if len(cs) > 3)


# Comprehensive related skill clusters for partial matching & transferable foundations
RELATED_SKILL_MAP = {
    "kubernetes": {
        "related": ["Docker", "Containerization", "DevOps"],
        "reason": "Candidate has verified Docker container experience; Kubernetes represents advanced cluster orchestration.",
    },
    "docker": {
        "related": ["Kubernetes", "DevOps", "CI/CD", "Linux"],
        "reason": "Candidate has orchestration or containerized infrastructure workflow familiarity.",
    },
    "typescript": {
        "related": ["JavaScript", "React", "Node.js"],
        "reason": "Candidate has solid JavaScript proficiency; TypeScript is a strongly typed superset of JavaScript.",
    },
    "javascript": {
        "related": ["TypeScript"],
        "reason": "Candidate has TypeScript knowledge; JavaScript is the foundational web runtime.",
    },
    "fastapi": {
        "related": ["Flask", "Django", "Python", "REST API"],
        "reason": "Candidate has Python backend framework expertise and asynchronous API familiarity.",
    },
    "flask": {
        "related": ["FastAPI", "Django", "Python", "REST API"],
        "reason": "Candidate has Python backend micro-framework development experience.",
    },
    "django": {
        "related": ["Flask", "FastAPI", "Python", "PostgreSQL"],
        "reason": "Candidate has Python full-featured web application development experience.",
    },
    "aws": {
        "related": ["GCP", "Azure", "Cloud Computing", "DevOps", "Docker"],
        "reason": "Candidate has cloud infrastructure experience on an alternative major cloud provider.",
    },
    "gcp": {
        "related": ["AWS", "Azure", "Cloud Computing"],
        "reason": "Candidate has enterprise cloud infrastructure and deployment experience.",
    },
    "azure": {
        "related": ["AWS", "GCP", "Cloud Computing"],
        "reason": "Candidate has enterprise cloud infrastructure and deployment experience.",
    },
    "postgresql": {
        "related": ["SQL", "MySQL", "SQLite", "Relational Database"],
        "reason": "Candidate has relational database schema design and SQL querying proficiency.",
    },
    "mysql": {
        "related": ["SQL", "PostgreSQL", "SQLite"],
        "reason": "Candidate has relational database management and querying skills.",
    },
    "mongodb": {
        "related": ["PostgreSQL", "SQL", "Redis", "NoSQL"],
        "reason": "Candidate has database design background; MongoDB uses NoSQL document collection patterns.",
    },
    "deep learning": {
        "related": ["Machine Learning", "PyTorch", "TensorFlow", "scikit-learn"],
        "reason": "Candidate has machine learning foundations and statistical modeling background.",
    },
    "pytorch": {
        "related": ["TensorFlow", "Keras", "Deep Learning", "Machine Learning"],
        "reason": "Candidate has neural network framework experience with alternative deep learning libraries.",
    },
    "tensorflow": {
        "related": ["PyTorch", "Keras", "Deep Learning", "Machine Learning"],
        "reason": "Candidate has neural network modeling experience with deep learning tools.",
    },
    "graphql": {
        "related": ["REST API", "Backend API"],
        "reason": "Candidate has client-server API design, schema structuring, and endpoint integration skills.",
    },
    "ci/cd": {
        "related": ["Git", "GitHub Actions", "Docker", "DevOps"],
        "reason": "Candidate has source control workflows and automated build/pipeline familiarity.",
    },
    "tailwind css": {
        "related": ["CSS", "Bootstrap", "HTML5", "Sass"],
        "reason": "Candidate has modern responsive frontend styling and component design experience.",
    },
    "react": {
        "related": ["Vue.js", "Angular", "Next.js", "Frontend"],
        "reason": "Candidate has modern component-based reactive UI framework experience.",
    },
    "next.js": {
        "related": ["React", "JavaScript", "TypeScript"],
        "reason": "Candidate has React foundations; Next.js is a server-side rendered framework built on React.",
    },
    "vue.js": {
        "related": ["React", "Angular", "JavaScript", "TypeScript"],
        "reason": "Candidate has modern component-driven reactive UI framework experience.",
    },
    "vue": {
        "related": ["React", "Angular", "JavaScript", "TypeScript"],
        "reason": "Candidate has modern component-driven reactive UI framework experience.",
    },
    "angular": {
        "related": ["React", "TypeScript", "JavaScript", "Vue.js"],
        "reason": "Candidate has enterprise single-page application framework experience.",
    },
    "redis": {
        "related": ["PostgreSQL", "SQL", "MongoDB", "Backend"],
        "reason": "Candidate has backend data management and in-memory caching familiarity.",
    },
    "node.js": {
        "related": ["Express", "JavaScript", "TypeScript", "Backend API"],
        "reason": "Candidate has server-side JavaScript execution environment proficiency.",
    },
    "express": {
        "related": ["Node.js", "JavaScript", "FastAPI", "REST API"],
        "reason": "Candidate has backend web server and routing framework experience.",
    },
    "pandas": {
        "related": ["NumPy", "Python", "SQL", "Data Analysis"],
        "reason": "Candidate has tabular data analysis and manipulation proficiency.",
    },
    "numpy": {
        "related": ["Pandas", "Python", "SciPy"],
        "reason": "Candidate has Python array computing and numerical processing foundations.",
    },
    "scikit-learn": {
        "related": ["Machine Learning", "Python", "Pandas", "Data Science"],
        "reason": "Candidate has statistical modeling and classic machine learning background.",
    },
    "rest api": {
        "related": ["FastAPI", "Flask", "GraphQL", "Backend API"],
        "reason": "Candidate has client-server communication and endpoint integration skills.",
    },
    "power bi": {
        "related": ["Tableau", "Excel", "Data Visualization", "SQL"],
        "reason": "Candidate has business intelligence dashboard and visualization tool experience with Tableau/Excel.",
    },
    "tableau": {
        "related": ["Power BI", "Excel", "Data Visualization", "SQL"],
        "reason": "Candidate has enterprise dashboard and data visualization experience.",
    },
    "sql": {
        "related": ["PostgreSQL", "MySQL", "SQLite", "Data Analysis"],
        "reason": "Candidate has relational database querying and schema manipulation foundations.",
    },
    "excel": {
        "related": ["Spreadsheets", "Data Analysis", "Tableau", "Power BI"],
        "reason": "Candidate has quantitative reporting and tabular data calculation skills.",
    },
    "nlp": {
        "related": ["Natural Language Processing", "Machine Learning", "Transformers", "Python"],
        "reason": "Candidate has linguistic text modeling and computational language processing foundations.",
    },
    "machine learning": {
        "related": ["Deep Learning", "scikit-learn", "Data Science", "Python", "Artificial Intelligence"],
        "reason": "Candidate has statistical modeling and algorithmic prediction foundations.",
    },
}


# ── Weight Configuration (Must sum to 1.00) ──────────────────────────────────
WEIGHT_SKILLS           = 0.35  # Technical Skill Overlap
WEIGHT_QUALIFICATIONS   = 0.15  # Education & Required Qualifications
WEIGHT_EXPERIENCE       = 0.15  # Professional Experience Tenure & Seniority
WEIGHT_PROJECTS         = 0.15  # Practical Projects & Portfolio Implementation
WEIGHT_RESPONSIBILITIES = 0.10  # Day-to-Day Job Responsibilities Alignment
WEIGHT_DOMAIN           = 0.10  # Career Relevance & Discipline Alignment

# Within skill overlap scoring:
CORE_SKILL_EXACT_PTS    = 1.00
CORE_SKILL_PARTIAL_PTS  = 0.60
CORE_SKILL_MAX_PTS      = 1.00

TECH_SKILL_EXACT_PTS    = 0.85
TECH_SKILL_PARTIAL_PTS  = 0.50
TECH_SKILL_MAX_PTS      = 0.85

SOFT_SKILL_EXACT_PTS    = 0.35
SOFT_SKILL_PARTIAL_PTS  = 0.15
SOFT_SKILL_MAX_PTS      = 0.35


def analyze_job_skill_gap(
    resume_skills: list[str],
    job_skills: list[str],
    resume_text: str = "",
    job_description: str = "",
    candidate_title: str = "",
    job_title: str = "",
    experience_text: str = "",
    education_text: str = "",
    projects_text: str = "",
    candidate_domain: str = "",
    is_internship_seeking: bool = False,
    employment_type: str = "",
) -> dict:
    """
    Calculates realistic match scores based on technical skill overlap,
    required qualifications, professional experience, projects, job responsibilities,
    and career relevance.

    Clearly distinguishes between strong, partial, and missing skill matches.
    Prevents unrelated jobs from receiving artificially high scores.
    Displays transparent reasons behind every match score.
    """
    resume_skills_clean = [s.strip() for s in (resume_skills or []) if s.strip()]
    job_skills_clean = [s.strip() for s in (job_skills or []) if s.strip()]

    # Infer candidate profile domain and title if missing
    cand_profile = None
    if not candidate_domain or not candidate_title:
        cand_profile = detect_candidate_profile(resume_skills_clean, resume_text, candidate_title)
        if not candidate_domain:
            candidate_domain = cand_profile["primary_domain"]
        if not candidate_title:
            candidate_title = cand_profile["recommended_role"]

    # Classify job's career domain and seniority level
    job_info = classify_job_domain(job_title, job_description, job_skills_clean)
    is_compatible, domain_mult, domain_expl = is_job_domain_compatible(candidate_domain, job_info["domain"])
    seniority_info = classify_job_seniority(job_title, job_description, employment_type=employment_type)
    is_internship = seniority_info["is_internship"]
    is_entry_level = seniority_info["is_entry_level"]

    domain_cfg = DOMAIN_TAXONOMY.get(candidate_domain, {})
    core_domain_skills = domain_cfg.get("core_skills", set())

    resume_set_lower = {s.lower(): s for s in resume_skills_clean}
    job_set_lower = {}
    for s in job_skills_clean:
        if s.lower() not in job_set_lower:
            job_set_lower[s.lower()] = s

    # Three-Tier Skill Lists
    strong_skills = []
    partial_skills = []
    missing_skills_detailed = []

    matched_skills = []   # string list for backward compatibility
    missing_skills = []   # string list for backward compatibility

    earned_points = 0.0
    max_possible_points = 0.0

    # ── 1. Evaluate Every Required Job Skill ──────────────────────────────
    for j_lower, j_original in job_set_lower.items():
        is_soft = _is_soft_skill(j_original)
        is_core = _is_core_domain_skill(j_original, domain_cfg)
        category = "Soft Skill" if is_soft else ("Core Technical" if is_core else "Technical Skill")

        if is_soft:
            exact_pts = SOFT_SKILL_EXACT_PTS
            partial_pts = SOFT_SKILL_PARTIAL_PTS
            max_pts = SOFT_SKILL_MAX_PTS
        elif is_core:
            exact_pts = CORE_SKILL_EXACT_PTS
            partial_pts = CORE_SKILL_PARTIAL_PTS
            max_pts = CORE_SKILL_MAX_PTS
        else:
            exact_pts = TECH_SKILL_EXACT_PTS
            partial_pts = TECH_SKILL_PARTIAL_PTS
            max_pts = TECH_SKILL_MAX_PTS

        max_possible_points += max_pts

        # A. Strong / Exact Match (Verified directly in CV)
        if j_lower in resume_set_lower:
            matched_name = resume_set_lower[j_lower]
            matched_skills.append(matched_name)
            strong_skills.append({
                "skill": j_original,
                "matched_via": matched_name,
                "category": category,
                "type": "strong",
                "strength": "Strong Match",
                "reason": "Directly verified in your resume.",
                "points_earned": exact_pts,
                "max_points": max_pts,
            })
            earned_points += exact_pts
            continue

        # Check canonical or substring alias match
        exact_found = False
        for r_lower, r_orig in resume_set_lower.items():
            if j_lower == r_lower or (len(j_lower) > 3 and (j_lower in r_lower or r_lower in j_lower)):
                matched_skills.append(j_original)
                strong_skills.append({
                    "skill": j_original,
                    "matched_via": r_orig,
                    "category": category,
                    "type": "strong",
                    "strength": "Strong Match",
                    "reason": f"Directly matches verified competency in '{r_orig}'.",
                    "points_earned": exact_pts,
                    "max_points": max_pts,
                })
                earned_points += exact_pts
                exact_found = True
                break

        if exact_found:
            continue

        # B. Partial Match (Related / Transferable Technology)
        partial_found = False
        cluster_info = RELATED_SKILL_MAP.get(j_lower)
        if cluster_info:
            related_terms = cluster_info["related"]
            for rel in related_terms:
                if rel.lower() in resume_set_lower:
                    matched_via = resume_set_lower[rel.lower()]
                    partial_item = {
                        "skill": j_original,
                        "matched_via": matched_via,
                        "category": category,
                        "type": "partial",
                        "strength": "Partial Match",
                        "reason": cluster_info["reason"],
                        "points_earned": partial_pts,
                        "max_points": max_pts,
                    }
                    partial_skills.append(partial_item)
                    earned_points += partial_pts
                    partial_found = True
                    break

        if partial_found:
            continue

        # C. Missing Skill (Absent from CV)
        priority = "High Priority" if is_core else ("Low Priority" if is_soft else "Medium Priority")
        missing_skills.append(j_original)
        missing_skills_detailed.append({
            "skill": j_original,
            "category": category,
            "type": "missing",
            "strength": "Missing Skill",
            "priority": priority,
            "impact": "Required core competency for role" if is_core else "Beneficial competency",
        })

    # Verify if matched skills contain domain-specific core technical competencies
    has_domain_skill_match = any(
        s.lower().strip() in core_domain_skills or
        any(cs in s.lower() for cs in core_domain_skills if len(cs) > 3)
        for s in matched_skills
    )

    # ── 2. Component Scores (6 Core Realistic Signals) ─────────────────────

    # A) Technical Skill Overlap (35%)
    if max_possible_points > 0:
        skill_coverage_pct = min(100, int(round((earned_points / max_possible_points) * 100)))
        # PENALTY GATE: If only generic soft skills matched without any core technical skill,
        # cap technical skill coverage to <= 20%
        if not has_domain_skill_match and candidate_domain in DOMAIN_TAXONOMY:
            skill_coverage_pct = min(20, skill_coverage_pct)
    else:
        skill_coverage_pct = 40

    # Fast-path for incompatible career categories: bypass expensive neural calculations
    if not is_compatible:
        qualifications_pct = 20
        experience_pct = 20
        projects_pct, projects_rationale = 15, "No domain project alignment."
        responsibilities_pct, responsibilities_rationale = 20, "Unrelated job duties."
    else:
        # B) Required Qualifications & Education (15%)
        qualifications_pct = education_qualification_score(
            resume_text, job_description, education_text=education_text
        ) if (resume_text and job_description) else 70

        # C) Professional Experience Relevance (15%)
        experience_pct = experience_relevance_score(
            resume_text, job_description, experience_text=experience_text
        ) if (resume_text and job_description) else 70

        # D) Practical Projects & Portfolio Implementation (15%)
        projects_pct, projects_rationale = project_portfolio_score(
            resume_text=resume_text,
            job_description=job_description,
            projects_text=projects_text,
            job_skills=job_skills_clean,
            is_internship_seeking=is_internship_seeking,
        ) if (resume_text and job_description) else (70, "Relevant technical skills in candidate profile.")

        # E) Job Responsibilities & Day-to-Day Tasks (10%)
        responsibilities_pct, responsibilities_rationale = responsibilities_alignment_score(
            resume_text=resume_text,
            job_description=job_description,
            experience_text=experience_text,
            projects_text=projects_text,
        ) if (resume_text and job_description) else (70, "Role duties align with declared candidate profile.")

    # F) Career Relevance & Domain Compatibility (10%)
    title_domain_pct = title_alignment_score(
        candidate_title, job_title, candidate_domain, job_info["domain"]
    )

    # Adjustments for early-career / internship candidates applying for compatible positions
    if is_compatible and is_internship_seeking and is_internship:
        experience_pct = max(82, experience_pct)
        qualifications_pct = max(88, qualifications_pct)
        projects_pct = max(85, projects_pct)
        title_domain_pct = max(90, title_domain_pct)
    elif is_compatible and is_internship_seeking and is_entry_level:
        experience_pct = max(72, experience_pct)
        qualifications_pct = max(82, qualifications_pct)
        projects_pct = max(80, projects_pct)
        title_domain_pct = max(85, title_domain_pct)

    # ── 3. Final Composite Realistic Score Calculation ────────────────────
    raw_score = (
        skill_coverage_pct * WEIGHT_SKILLS
        + qualifications_pct * WEIGHT_QUALIFICATIONS
        + experience_pct * WEIGHT_EXPERIENCE
        + projects_pct * WEIGHT_PROJECTS
        + responsibilities_pct * WEIGHT_RESPONSIBILITIES
        + title_domain_pct * WEIGHT_DOMAIN
    )

    # If role is in an unrelated career category, downscale heavily so it never receives artificially high scores
    if not is_compatible:
        skill_coverage_pct = min(15, skill_coverage_pct)
        final_score = int(round(raw_score * domain_mult))
        final_score = max(5, min(18, final_score))

        skill_contrib = int(round(skill_coverage_pct * WEIGHT_SKILLS * domain_mult))
        qual_contrib = int(round(qualifications_pct * WEIGHT_QUALIFICATIONS * domain_mult))
        exp_contrib = int(round(experience_pct * WEIGHT_EXPERIENCE * domain_mult))
        proj_contrib = int(round(projects_pct * WEIGHT_PROJECTS * domain_mult))
        resp_contrib = int(round(responsibilities_pct * WEIGHT_RESPONSIBILITIES * domain_mult))
        domain_contrib = int(round(title_domain_pct * WEIGHT_DOMAIN * domain_mult))
    else:
        final_score = int(round(raw_score))
        final_score = max(8, min(98, final_score))

        skill_contrib = int(round(skill_coverage_pct * WEIGHT_SKILLS))
        qual_contrib = int(round(qualifications_pct * WEIGHT_QUALIFICATIONS))
        exp_contrib = int(round(experience_pct * WEIGHT_EXPERIENCE))
        proj_contrib = int(round(projects_pct * WEIGHT_PROJECTS))
        resp_contrib = int(round(responsibilities_pct * WEIGHT_RESPONSIBILITIES))
        domain_contrib = int(round(title_domain_pct * WEIGHT_DOMAIN))

    # ── 4. Transparent Diagnostic Reasons Generation ──────────────────────
    strong_reasons = []
    gap_reasons = []

    if not is_compatible:
        cand_name = domain_cfg.get('name', candidate_domain)
        verdict = f"Unrelated Category ({job_info['domain_name']})"
        summary_explanation = (
            f"⚠️ Unrelated Career Category ({job_info['domain_name']} vs {cand_name}): "
            f"This opening is outside your verified discipline. Generic overlaps (such as common tools) "
            f"cannot qualify as a high match. Score penalized to {final_score}%."
        )
        gap_reasons.append(f"Position belongs to {job_info['domain_name']}, which does not align with your verified discipline ({cand_name}).")
        gap_reasons.append(f"Match score heavily penalized to {final_score}% to ensure irrelevant openings are demoted.")
        actionable_advice = f"Focus on positions categorized under {cand_name} to maximize your response rate."
    elif is_internship:
        verdict = "Relevant Internship Match"
        summary_explanation = (
            f"🎓 Relevant Internship Match ({final_score}%): "
            f"Technical Skills {skill_coverage_pct}% ({skill_contrib} pts) + "
            f"Qualifications {qualifications_pct}% ({qual_contrib} pts) + "
            f"Experience {experience_pct}% ({exp_contrib} pts) + "
            f"Projects & Portfolio {projects_pct}% ({proj_contrib} pts) + "
            f"Responsibilities {responsibilities_pct}% ({resp_contrib} pts) + "
            f"Career Fit {title_domain_pct}% ({domain_contrib} pts)."
        )
        if strong_skills:
            strong_names = [s["skill"] for s in strong_skills]
            strong_reasons.append(f"Verified {len(strong_skills)} direct skill requirement(s): {', '.join(strong_names[:4])}.")
        if partial_skills:
            partial_names = [f"{p['skill']} (via {p['matched_via']})" for p in partial_skills]
            strong_reasons.append(f"Transferable proficiency in {len(partial_skills)} tech cluster(s): {', '.join(partial_names[:3])}.")
        strong_reasons.append("Academic projects and coursework count as high qualifying fit for this internship.")
        if projects_pct >= 75:
            strong_reasons.append(f"Practical projects demonstrate relevant implementation: {projects_rationale.split(';')[0]}.")

        high_prio_missing = [m["skill"] for m in missing_skills_detailed if m["priority"] == "High Priority"]
        if high_prio_missing:
            gap_reasons.append(f"Missing {len(high_prio_missing)} core competency/competencies: {', '.join(high_prio_missing[:3])}.")
            actionable_advice = f"To raise your score, prioritize gaining verified experience in: {', '.join(high_prio_missing[:3])}."
        else:
            gap_reasons.append("Excellent foundational fit for internship responsibilities.")
            actionable_advice = "Outstanding candidate profile for this internship opportunity."
    else:
        if final_score >= 80:
            verdict = "Strong Match — Highly Suitable"
        elif final_score >= 65:
            verdict = "Competitive Match — Good Skill Overlap"
        elif final_score >= 45:
            verdict = "Partial Fit — Noticeable Skill Gaps"
        else:
            verdict = "Low Fit — Missing Core Requirements"

        summary_explanation = (
            f"Your {final_score}% match is scored across 6 dimensions: "
            f"Technical Skills {skill_coverage_pct}% ({skill_contrib} pts) + "
            f"Qualifications {qualifications_pct}% ({qual_contrib} pts) + "
            f"Experience {experience_pct}% ({exp_contrib} pts) + "
            f"Projects & Portfolio {projects_pct}% ({proj_contrib} pts) + "
            f"Responsibilities {responsibilities_pct}% ({resp_contrib} pts) + "
            f"Career Fit {title_domain_pct}% ({domain_contrib} pts)."
        )

        if strong_skills:
            strong_names = [s["skill"] for s in strong_skills]
            strong_reasons.append(f"Verified {len(strong_skills)} direct skill requirement(s): {', '.join(strong_names[:4])}.")
        if partial_skills:
            partial_names = [f"{p['skill']} (via {p['matched_via']})" for p in partial_skills]
            strong_reasons.append(f"Transferable proficiency in {len(partial_skills)} tech cluster(s): {', '.join(partial_names[:3])}.")
        if qualifications_pct >= 70:
            strong_reasons.append("Educational qualifications satisfy degree and field requirements.")
        if projects_pct >= 70:
            strong_reasons.append(f"Practical project portfolio demonstrates relevant technical execution ({projects_rationale.split(';')[0]}).")
        if experience_pct >= 70:
            strong_reasons.append("Professional experience tenure and seniority align well with target level.")

        high_prio_missing = [m["skill"] for m in missing_skills_detailed if m["priority"] == "High Priority"]
        med_prio_missing = [m["skill"] for m in missing_skills_detailed if m["priority"] == "Medium Priority"]

        if high_prio_missing:
            gap_reasons.append(f"Missing {len(high_prio_missing)} critical core skill(s): {', '.join(high_prio_missing[:4])}.")
        if med_prio_missing:
            gap_reasons.append(f"Missing {len(med_prio_missing)} auxiliary competency/competencies: {', '.join(med_prio_missing[:3])}.")
        if experience_pct < 65:
            gap_reasons.append("Experience tenure or seniority depth is below typical position threshold.")
        if projects_pct < 60:
            gap_reasons.append("Limited project evidence demonstrating this specific technology stack in action.")

        if not gap_reasons:
            gap_reasons.append("All primary technical and professional requirements are satisfied.")

        if high_prio_missing:
            actionable_advice = f"Prioritize gaining verified experience and building portfolio projects in: {', '.join(high_prio_missing[:3])}."
        elif med_prio_missing:
            actionable_advice = f"Familiarize yourself with {', '.join(med_prio_missing[:2])} to further elevate your candidate profile."
        else:
            actionable_advice = "Outstanding profile! You satisfy all core technical competencies required for this position."

    return {
        "final_score": final_score,
        "is_unrelated_domain": not is_compatible,

        # 6 Component Scores (0-100)
        "skill_coverage_score": skill_coverage_pct,
        "qualifications_score": qualifications_pct,
        "experience_score": experience_pct,
        "projects_score": projects_pct,
        "responsibilities_score": responsibilities_pct,
        "domain_alignment_score": title_domain_pct,

        # Backward-compatible score keys
        "semantic_score": responsibilities_pct,
        "title_score": title_domain_pct,
        "education_score": qualifications_pct,

        # Backward-compatible skill points breakdown
        "skill_points": {
            "exact_count": len(strong_skills),
            "exact_points": sum(s["points_earned"] for s in strong_skills),
            "partial_count": len(partial_skills),
            "partial_points": sum(p["points_earned"] for p in partial_skills),
            "missing_count": len(missing_skills_detailed),
            "total_required": len(strong_skills) + len(partial_skills) + len(missing_skills_detailed),
            "total_points_earned": earned_points,
            "max_possible_points": max_possible_points,
            "skill_contribution_pts": skill_contrib,
            "qualifications_contribution_pts": qual_contrib,
            "experience_contribution_pts": exp_contrib,
            "projects_contribution_pts": proj_contrib,
            "responsibilities_contribution_pts": resp_contrib,
            "title_contribution_pts": domain_contrib,
        },

        # Three-Tier Skill Matches
        "strong_skills": strong_skills,
        "partial_skills": partial_skills,
        "missing_skills_detailed": missing_skills_detailed,

        # Flat lists for backward compatibility
        "matched_skills": sorted(matched_skills),
        "missing_skills": sorted(missing_skills),

        # Diagnostic Details & Transparent Reasons
        "summary_explanation": summary_explanation,
        "actionable_advice": actionable_advice,
        "detailed_diagnostic": {
            "verdict": verdict,
            "strong_reasons": strong_reasons,
            "gap_reasons": gap_reasons,
            "actionable_steps": actionable_advice,
            "projects_rationale": projects_rationale,
            "responsibilities_rationale": responsibilities_rationale,
        },

        # Detailed Mathematical Breakdown
        "score_breakdown": {
            "formula": "Final = Technical Skills×35% + Qualifications×15% + Experience×15% + Projects×15% + Responsibilities×10% + Career Fit×10%",
            "skill_coverage_pct": skill_coverage_pct,
            "skill_coverage_pts": skill_contrib,
            "qualifications_pct": qualifications_pct,
            "qualifications_pts": qual_contrib,
            "experience_score_pct": experience_pct,
            "experience_pts": exp_contrib,
            "projects_pct": projects_pct,
            "projects_pts": proj_contrib,
            "responsibilities_pct": responsibilities_pct,
            "responsibilities_pts": resp_contrib,
            "title_score_pct": title_domain_pct,
            "title_pts": domain_contrib,
            "domain_multiplier": domain_mult,
            "total_score": final_score,
        },

        # Seniority & Domain Metadata
        "seniority_level": seniority_info["level"],
        "is_internship": seniority_info["is_internship"],
        "is_entry_level": seniority_info["is_entry_level"],
        "is_experienced": seniority_info["is_experienced"],
        "display_seniority": seniority_info["display_seniority"],
        "badge_color": seniority_info["badge_color"],
        "badge_bg": seniority_info["badge_bg"],
        "domain_info": job_info,
        "domain_explanation": domain_expl,
    }


def get_skill_gap(resume_skills: list[str], job_skills: list[str]) -> tuple[list[str], list[str]]:
    """Legacy helper returning (matched, missing) for backward compatibility."""
    analysis = analyze_job_skill_gap(resume_skills, job_skills)
    matched = analysis["matched_skills"]
    missing = analysis["missing_skills"] + [p["skill"] for p in analysis["partial_skills"]]
    return matched, missing


def suggest_learning(missing_skills: list[str]) -> list[dict]:
    """Provide verified, high-quality learning resources for missing competencies."""
    resources_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "learning_resources.json")
    suggestions = []
    try:
        if os.path.exists(resources_path):
            with open(resources_path, "r", encoding="utf-8") as f:
                resources = json.load(f)
            for skill in missing_skills:
                skill_clean = skill.strip()
                if skill_clean.lower() in resources:
                    suggestions.extend(resources[skill_clean.lower()])
                else:
                    suggestions.append({
                        "title": f"Mastering {skill_clean} for Production",
                        "provider": "Coursera / Udemy",
                        "url": f"https://www.coursera.org/search?query={skill_clean}",
                        "level": "Intermediate",
                        "cost": "Free & Paid Options",
                    })
    except Exception:
        pass

    if not suggestions and missing_skills:
        return [
            {
                "title": f"Official {skill} Documentation & Certification Guide",
                "provider": "Official Docs",
                "url": f"https://www.google.com/search?q={skill}+official+documentation+tutorial",
                "level": "All Levels",
                "cost": "Free",
            }
            for skill in missing_skills
        ]

    return suggestions

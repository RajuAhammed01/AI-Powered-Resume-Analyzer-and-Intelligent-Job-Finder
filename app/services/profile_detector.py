"""
JobSnap — Candidate Profile & Career Domain Intelligence Engine
==============================================================
Identifies candidate professional domains (e.g. Frontend Development,
Data Science & Machine Learning, Backend, DevOps, etc.) from verified
skills, resume text, and structure.

Ensures job recommendations strictly align with the candidate's actual
career category, prioritizing relevant roles (e.g. Frontend & React Developer
for frontend resumes; Data Analyst, Machine Learning Engineer, and AI Engineer
for data science/ML resumes) and avoiding unrelated career categories.
"""

import re
from typing import Dict, List, Optional, Tuple

# Domain definitions with identifying skills, titles, and negative indicators
DOMAIN_TAXONOMY = {
    "frontend": {
        "domain_id": "frontend",
        "name": "Frontend Development",
        "primary_roles": [
            "Frontend Developer",
            "React Developer",
            "UI Developer",
            "Frontend Engineer",
            "Web Developer",
            "Vue Developer",
            "Angular Developer",
            "JavaScript Developer",
        ],
        "search_queries": [
            "Frontend Developer",
            "React Developer",
            "UI Developer",
        ],
        "core_skills": {
            "react", "react.js", "javascript", "typescript", "html", "html5",
            "css", "css3", "sass", "scss", "tailwind", "tailwind css", "bootstrap",
            "vue", "vue.js", "angular", "redux", "next.js", "web development",
            "responsive design", "webpack", "vite", "jquery", "ui/ux", "frontend",
            "front-end", "dom", "graphql", "figma",
        },
        "strong_title_keywords": [
            "frontend", "front-end", "react", "vue", "angular", "ui developer",
            "web developer", "ui engineer", "client-side", "javascript developer",
        ],
        "unrelated_domains": ["writing_content", "networking_it", "data_ml", "devops_cloud", "sales_marketing", "hr_recruiting", "finance_accounting"],
    },
    "data_ml": {
        "domain_id": "data_ml",
        "name": "Data Science & Machine Learning",
        "primary_roles": [
            "Machine Learning Engineer",
            "Data Scientist",
            "AI Engineer",
            "Data Analyst",
            "Deep Learning Engineer",
            "NLP Engineer",
            "Computer Vision Engineer",
            "BI Analyst",
        ],
        "search_queries": [
            "Machine Learning Engineer",
            "Data Scientist",
            "Data Analyst",
            "AI Engineer",
        ],
        "core_skills": {
            "python", "machine learning", "deep learning", "data science",
            "data analysis", "pandas", "numpy", "scikit-learn", "tensorflow",
            "pytorch", "keras", "sql", "tableau", "power bi", "statistics",
            "nlp", "natural language processing", "computer vision", "opencv",
            "hugging face", "llm", "generative ai", "data visualization",
            "matplotlib", "seaborn", "scipy", "r", "spark", "bigquery",
            "analytics", "predictive modeling", "feature engineering",
        },
        "strong_title_keywords": [
            "machine learning", "data scientist", "data analyst", "ai engineer",
            "artificial intelligence", "deep learning", "nlp engineer", "ml engineer",
            "bi analyst", "business intelligence", "computer vision", "analytics",
        ],
        "unrelated_domains": ["writing_content", "networking_it", "frontend", "sales_marketing", "hr_recruiting", "finance_accounting", "mobile"],
    },
    "backend": {
        "domain_id": "backend",
        "name": "Backend Development",
        "primary_roles": [
            "Backend Developer",
            "Backend Engineer",
            "Python Developer",
            "Java Developer",
            "Go Developer",
            "Node.js Developer",
            "Software Engineer",
            "API Engineer",
        ],
        "search_queries": [
            "Backend Developer",
            "Python Developer",
            "Software Engineer",
            "Java Developer",
        ],
        "core_skills": {
            "python", "java", "golang", "go", "c#", ".net", "node.js", "express",
            "django", "flask", "fastapi", "spring boot", "postgresql", "mysql",
            "mongodb", "redis", "graphql", "rest api", "microservices", "kafka",
            "rabbitmq", "sql", "orm", "backend", "back-end", "database",
        },
        "strong_title_keywords": [
            "backend", "back-end", "server-side", "api engineer", "python developer",
            "java developer", "golang developer", "backend engineer",
        ],
        "unrelated_domains": ["sales_marketing", "hr_recruiting", "finance_accounting"],
    },
    "devops_cloud": {
        "domain_id": "devops_cloud",
        "name": "DevOps & Cloud Engineering",
        "primary_roles": [
            "DevOps Engineer",
            "Cloud Engineer",
            "Site Reliability Engineer",
            "Platform Engineer",
            "Infrastructure Engineer",
            "AWS Solutions Architect",
        ],
        "search_queries": [
            "DevOps Engineer",
            "Cloud Engineer",
            "Site Reliability Engineer",
        ],
        "core_skills": {
            "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "ansible",
            "ci/cd", "jenkins", "github actions", "linux", "helm", "prometheus",
            "grafana", "cloudformation", "devops", "cloud computing", "sre",
            "site reliability", "infrastructure as code", "bash", "shell scripting",
        },
        "strong_title_keywords": [
            "devops", "cloud engineer", "site reliability", "sre", "platform engineer",
            "infrastructure engineer", "systems administrator", "sysadmin",
        ],
        "unrelated_domains": ["frontend", "data_ml", "sales_marketing", "hr_recruiting", "finance_accounting"],
    },
    "fullstack": {
        "domain_id": "fullstack",
        "name": "Full Stack Development",
        "primary_roles": [
            "Full Stack Developer",
            "Full Stack Engineer",
            "Software Engineer",
        ],
        "search_queries": [
            "Full Stack Developer",
            "Full Stack Engineer",
            "Software Engineer",
        ],
        "core_skills": {
            "full stack", "fullstack", "react", "node.js", "javascript", "typescript",
            "python", "django", "sql", "postgresql", "mongodb", "rest api", "html",
            "css", "docker", "git",
        },
        "strong_title_keywords": [
            "full stack", "fullstack", "full-stack",
        ],
        "unrelated_domains": ["sales_marketing", "hr_recruiting", "finance_accounting"],
    },
    "mobile": {
        "domain_id": "mobile",
        "name": "Mobile App Development",
        "primary_roles": [
            "Mobile Developer",
            "Android Developer",
            "iOS Developer",
            "Flutter Developer",
            "React Native Developer",
        ],
        "search_queries": [
            "Mobile Developer",
            "Android Developer",
            "iOS Developer",
            "Flutter Developer",
        ],
        "core_skills": {
            "android", "ios", "swift", "kotlin", "flutter", "react native",
            "mobile", "xcode", "android studio", "dart", "mobile app",
        },
        "strong_title_keywords": [
            "android", "ios", "mobile developer", "flutter", "react native",
        ],
        "unrelated_domains": ["writing_content", "networking_it", "data_ml", "devops_cloud", "sales_marketing", "hr_recruiting", "finance_accounting"],
    },
    "data_engineering": {
        "domain_id": "data_engineering",
        "name": "Data Engineering",
        "primary_roles": [
            "Data Engineer",
            "Big Data Engineer",
            "ETL Developer",
            "Data Platform Engineer",
        ],
        "search_queries": [
            "Data Engineer",
            "Big Data Engineer",
            "ETL Developer",
        ],
        "core_skills": {
            "spark", "apache spark", "airflow", "hadoop", "kafka", "snowflake",
            "databricks", "sql", "etl", "data warehouse", "bigquery", "redshift",
            "python", "data pipeline", "dbt",
        },
        "strong_title_keywords": [
            "data engineer", "big data", "etl developer", "data platform",
        ],
        "unrelated_domains": ["frontend", "sales_marketing", "hr_recruiting", "finance_accounting"],
    },
    "qa_testing": {
        "domain_id": "qa_testing",
        "name": "QA & Test Automation",
        "primary_roles": [
            "QA Engineer",
            "Software Test Engineer",
            "Automation QA Engineer",
            "SDET",
        ],
        "search_queries": [
            "QA Engineer",
            "Software Test Engineer",
            "SDET",
        ],
        "core_skills": {
            "qa", "testing", "selenium", "cypress", "playwright", "test automation",
            "unit testing", "pytest", "junit", "postman", "quality assurance", "sdet",
        },
        "strong_title_keywords": [
            "qa", "test engineer", "automation engineer", "sdet", "quality assurance",
        ],
        "unrelated_domains": ["sales_marketing", "hr_recruiting", "finance_accounting"],
    },
    "writing_content": {
        "domain_id": "writing_content",
        "name": "Writing & Content Creation",
        "primary_roles": [
            "Content Writer",
            "Freelance Writer",
            "Copywriter",
            "Technical Writer",
            "Blog Writer",
            "Editor",
        ],
        "search_queries": [
            "Content Writer",
            "Technical Writer",
            "Copywriter",
        ],
        "core_skills": {
            "writing", "copywriting", "content writing", "editing", "proofreading",
            "creative writing", "blogging", "articles", "seo writing", "journalism",
            "technical writing", "documentation",
        },
        "strong_title_keywords": [
            "writer", "copywriter", "content writer", "freelance writer",
            "technical writer", "editor", "blog writer", "author", "proofreader",
        ],
        "unrelated_domains": [
            "frontend", "backend", "data_ml", "devops_cloud", "fullstack",
            "mobile", "data_engineering", "qa_testing", "networking_it",
        ],
    },
    "networking_it": {
        "domain_id": "networking_it",
        "name": "IT & Network Engineering",
        "primary_roles": [
            "Network Engineer",
            "Network Administrator",
            "Systems Administrator",
            "IT Support Specialist",
            "Infrastructure Support",
            "Cisco Network Engineer",
        ],
        "search_queries": [
            "Network Engineer",
            "Network Administrator",
            "Systems Administrator",
        ],
        "core_skills": {
            "networking", "cisco", "lan", "wan", "routing", "switching", "firewalls",
            "vpn", "tcp/ip", "dns", "dhcp", "subnets", "active directory",
            "ccna", "ccnp", "network administration", "it support", "hardware",
        },
        "strong_title_keywords": [
            "network engineer", "network administrator", "systems administrator",
            "network specialist", "it support", "helpdesk", "cisco", "sysadmin",
        ],
        "unrelated_domains": [
            "frontend", "data_ml", "mobile", "writing_content",
        ],
    },
}

# Non-tech and completely unrelated job categories to filter out
UNRELATED_NON_TECH_KEYWORDS = [
    "accountant", "accounting", "auditor", "bookkeeper", "sales representative",
    "sales manager", "account executive", "account manager", "real estate",
    "customer support", "customer service", "customer success", "receptionist",
    "call center", "telemarketer", "cashier", "nurse", "medical assistant",
    "driver", "warehouse", "delivery", "chef", "cook", "waiter", "bartender",
    "janitor", "security guard", "human resources", "hr generalist", "recruiter",
    "talent acquisition", "content writer", "copywriter", "freelance writer",
    "writer", "editor", "proofreader", "author", "journalist", "blogger",
    "office assistant", "virtual assistant", "administrative assistant",
    "executive assistant", "academic dean", "teacher", "professor", "tutor",
    "instructor", "clerk", "social media manager", "community manager",
    "paralegal", "legal assistant",
]

# Core technical title markers that any tech job must possess
TECH_TITLE_INDICATORS = [
    "developer", "engineer", "programmer", "architect", "scientist",
    "analyst", "devops", "sre", "webmaster", "coder", "sdet", "technologist",
    "frontend", "front-end", "backend", "back-end", "fullstack", "full-stack",
    "software", "data", "cloud", "mobile", "ios", "android", "machine learning",
    "artificial intelligence", "deep learning", "ui", "ux", "qa",
]


def detect_candidate_profile(
    skills: List[str],
    resume_text: str = "",
    declared_title: str = "",
) -> dict:
    """
    Intelligently analyzes candidate's verified skills, resume text, and declared title
    to deduce their primary technical domain and recommended job roles.

    Returns:
        dict: {
            "primary_domain": "frontend" | "data_ml" | "backend" | ...,
            "domain_name": "Frontend Development",
            "recommended_role": "Frontend Developer",
            "alternative_roles": ["React Developer", "UI Developer"],
            "search_queries": ["Frontend Developer", "React Developer"],
            "domain_scores": {domain: score, ...},
            "is_confident": bool,
        }
    """
    skills_clean = [s.strip().lower() for s in (skills or []) if s.strip()]
    skills_set = set(skills_clean)
    text_lower = (resume_text or "").lower()
    title_lower = (declared_title or "").lower()

    domain_scores = {d: 0.0 for d in DOMAIN_TAXONOMY}

    for domain_id, config in DOMAIN_TAXONOMY.items():
        score = 0.0

        # 1. Skill overlap (each matching core skill gives high weight)
        core_skills = config["core_skills"]
        for skill in skills_clean:
            if skill in core_skills:
                score += 3.0
            else:
                for cs in core_skills:
                    if len(cs) > 3 and (cs in skill or skill in cs):
                        score += 1.5
                        break

        # 2. Declared title alignment (gives heavy anchor weight)
        for tk in config["strong_title_keywords"]:
            if tk in title_lower:
                score += 8.0
                break

        # 3. Resume text occurrences of strong keywords
        for tk in config["strong_title_keywords"]:
            count = len(re.findall(r"\b" + re.escape(tk) + r"\b", text_lower))
            if count > 0:
                score += min(5.0, count * 1.0)

        domain_scores[domain_id] = score

    # Sort domains by score
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    top_domain, top_score = sorted_domains[0]
    runner_up_domain, runner_up_score = sorted_domains[1] if len(sorted_domains) > 1 else ("", 0.0)

    # Specific fine-tuning for prominent sub-specializations:
    # E.g. Frontend with strong React -> "React Developer" or "Frontend Developer"
    # E.g. Data ML with strong Python/ML/AI -> "Machine Learning Engineer" or "Data Analyst"
    config = DOMAIN_TAXONOMY.get(top_domain, DOMAIN_TAXONOMY["backend"])
    recommended_role = config["primary_roles"][0]
    search_queries = list(config["search_queries"])

    if top_domain == "frontend":
        if "react" in skills_set or "react.js" in skills_set or "react" in title_lower:
            recommended_role = "Frontend Developer"
            # Prioritize React & Frontend Developer as explicitly requested
            search_queries = ["Frontend Developer", "React Developer", "Frontend"]
        elif "vue" in skills_set or "vue.js" in skills_set:
            recommended_role = "Vue Developer"
            search_queries = ["Vue Developer", "Frontend Developer"]
        else:
            recommended_role = "Frontend Developer"
            search_queries = ["Frontend Developer", "Web Developer"]

    elif top_domain == "data_ml":
        has_deep_learning = any(k in skills_set for k in ["deep learning", "pytorch", "tensorflow", "keras"])
        has_analytics_only = any(k in skills_set for k in ["data analysis", "tableau", "power bi", "bi", "excel"]) and not has_deep_learning
        has_ai_llm = any(k in skills_set for k in ["llm", "generative ai", "nlp", "computer vision", "artificial intelligence"])

        if has_ai_llm:
            recommended_role = "AI Engineer"
            search_queries = ["AI Engineer", "Machine Learning Engineer", "Data Scientist"]
        elif has_deep_learning or "machine learning" in skills_set or "machine learning" in title_lower:
            recommended_role = "Machine Learning Engineer"
            search_queries = ["Machine Learning Engineer", "Data Scientist", "AI Engineer"]
        elif has_analytics_only or "data analyst" in title_lower:
            recommended_role = "Data Analyst"
            search_queries = ["Data Analyst", "Business Intelligence", "Data Scientist"]
        else:
            recommended_role = "Data Scientist"
            search_queries = ["Data Scientist", "Machine Learning Engineer", "Data Analyst"]

    elif top_domain == "backend":
        if "python" in skills_set and any(k in skills_set for k in ["django", "flask", "fastapi"]):
            recommended_role = "Python Developer"
            search_queries = ["Python Developer", "Backend Developer", "Software Engineer"]
        elif "java" in skills_set or "spring boot" in skills_set:
            recommended_role = "Java Developer"
            search_queries = ["Java Developer", "Backend Engineer", "Software Engineer"]
        else:
            recommended_role = "Backend Developer"
            search_queries = ["Backend Developer", "Software Engineer"]

    is_confident = top_score >= 4.0

    return {
        "primary_domain": top_domain,
        "domain_name": config["name"],
        "recommended_role": recommended_role,
        "alternative_roles": config["primary_roles"][1:4],
        "search_queries": search_queries,
        "domain_scores": domain_scores,
        "is_confident": is_confident,
    }


def classify_job_domain(
    job_title: str,
    job_description: str = "",
    job_skills: Optional[List[str]] = None,
) -> dict:
    """
    Classifies a job opening into its primary domain and checks if it's
    a non-tech or unrelated role.
    """
    title_lower = (job_title or "").lower().strip()
    desc_lower = (job_description or "").lower()[:800]
    skills_lower = [s.lower().strip() for s in (job_skills or [])]

    # Check for completely unrelated non-tech jobs
    for non_tech in UNRELATED_NON_TECH_KEYWORDS:
        if re.search(r"\b" + re.escape(non_tech) + r"\b", title_lower):
            return {
                "domain": "unrelated_non_tech",
                "domain_name": "Non-Technical / Unrelated",
                "is_tech": False,
                "confidence": 0.95,
            }

    scores = {d: 0.0 for d in DOMAIN_TAXONOMY}

    for domain_id, config in DOMAIN_TAXONOMY.items():
        score = 0.0
        # Title matching (strongest signal for jobs)
        for tk in config["strong_title_keywords"]:
            if tk in title_lower:
                score += 10.0
                break

        # Job skills
        core_skills = config["core_skills"]
        for js in skills_lower:
            if js in core_skills:
                score += 2.0

        # Description keywords
        for tk in config["strong_title_keywords"]:
            if tk in desc_lower:
                score += 1.5

        scores[domain_id] = score

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_domain, top_score = sorted_scores[0]

    # If domain score is low, verify whether title even has technical role indicators
    has_tech_indicator = any(re.search(r"\b" + re.escape(ti) + r"\b", title_lower) for ti in TECH_TITLE_INDICATORS)
    if not has_tech_indicator and top_score < 4.0:
        return {
            "domain": "unrelated_non_tech",
            "domain_name": "Non-Technical / Unrelated",
            "is_tech": False,
            "confidence": 0.90,
        }

    if top_score < 2.0:
        return {
            "domain": "general_tech",
            "domain_name": "General Technology",
            "is_tech": True,
            "confidence": 0.3,
        }

    return {
        "domain": top_domain,
        "domain_name": DOMAIN_TAXONOMY[top_domain]["name"],
        "is_tech": True,
        "confidence": min(1.0, top_score / 12.0),
    }


def is_job_domain_compatible(candidate_domain: str, job_domain: str) -> Tuple[bool, float, str]:
    """
    Evaluates whether a job's domain is compatible with the candidate's domain.

    Returns:
        (is_compatible, alignment_multiplier, explanation)
    """
    if not candidate_domain or candidate_domain == "general_tech":
        return True, 1.0, "General technical compatibility."

    if job_domain == "unrelated_non_tech":
        return False, 0.05, "Unrelated career category (non-technical opening)."

    if job_domain == candidate_domain:
        return True, 1.0, f"Direct domain match ({DOMAIN_TAXONOMY.get(candidate_domain, {}).get('name', 'Technical')})."

    # Fullstack candidates are compatible with frontend and backend
    if candidate_domain == "fullstack" and job_domain in ["frontend", "backend"]:
        return True, 0.85, "Compatible adjacent discipline for Full Stack profile."

    if job_domain == "fullstack" and candidate_domain in ["frontend", "backend"]:
        return True, 0.80, "Compatible adjacent discipline (Full Stack opening)."

    # Data Science and Data Engineering overlap
    if candidate_domain == "data_ml" and job_domain == "data_engineering":
        return True, 0.75, "Related data discipline (Data Engineering)."

    if candidate_domain == "data_engineering" and job_domain == "data_ml":
        return True, 0.75, "Related data discipline (Data Science / ML)."

    # Backend and DevOps overlap
    if candidate_domain == "backend" and job_domain == "devops_cloud":
        return True, 0.60, "Related infrastructure & backend discipline."

    if candidate_domain == "devops_cloud" and job_domain == "backend":
        return True, 0.60, "Related systems & backend discipline."

    # Check explicit unrelated domains list in both directions
    cand_config = DOMAIN_TAXONOMY.get(candidate_domain)
    job_config = DOMAIN_TAXONOMY.get(job_domain)

    if (cand_config and job_domain in cand_config.get("unrelated_domains", [])) or        (job_config and candidate_domain in job_config.get("unrelated_domains", [])):
        cand_name = cand_config["name"] if cand_config else candidate_domain
        job_name = job_config["name"] if job_config else job_domain
        multiplier = 0.05 if job_domain in ["writing_content", "unrelated_non_tech"] else 0.10
        return False, multiplier, f"Unrelated career category ({job_name} vs {cand_name})."

    # Neutral fallback for general tech
    return True, 0.60, "General cross-discipline role."


# ── Seniority Classification & Tiered Recommendation Engine ──────────────

SENIORITY_INTERNSHIP = "internship"
SENIORITY_ENTRY_LEVEL = "entry_level"
SENIORITY_EXPERIENCED = "experienced"

INTERNSHIP_TITLE_REGEX = re.compile(
    r"\b(intern|internship|trainee|co[\s\-]op|coop|working[\s\-]student|werkstudent|praktikant)\b",
    re.IGNORECASE,
)

ENTRY_LEVEL_TITLE_REGEX = re.compile(
    r"\b(junior|jr\.?|entry[\s\-]level|associate|graduate|fresher|l1)\b",
    re.IGNORECASE,
)

EXPERIENCED_TITLE_REGEX = re.compile(
    r"\b(senior|sr\.?|lead|principal|staff|architect|director|head of|manager|tech lead|mid[\s\-]level|experienced)\b",
    re.IGNORECASE,
)

STUDENT_INTENT_PATTERNS = [
    r"\b(seeking|looking for|open to|applying for)\b.{0,40}\b(intern|internship|co[\s\-]op|trainee|summer position)\b",
    r"\b(internship candidate|internship applicant|aspiring intern)\b",
    r"\b(undergraduate|bachelor student|masters student|graduate student|current student|phd student|university student|college student)\b",
    r"\b(pursuing\s+(a\s+)?(bachelor|master|b\.?s|m\.?s|b\.?tech|b\.?sc|m\.?sc|ph\.?d|degree|diploma))\b",
    r"\b(candidate for (bachelor|master|b\.?s|m\.?s|b\.?tech|degree))\b",
    r"\b(expected graduation|expected to graduate|graduation year:?\s*202[4-9]|class of 202[4-9]|graduation:?\s*(may|june|dec|december|spring|summer|fall|winter)?\s*202[4-9])\b",
    r"\b(student at|studying at|currently studying)\b",
]


def classify_job_seniority(
    job_title: str,
    job_description: str = "",
    employment_type: str = "",
) -> Dict[str, any]:
    """
    Classifies a job posting into seniority tiers: 'internship', 'entry_level', or 'experienced'.
    """
    t_clean = (job_title or "").strip()
    emp_clean = (employment_type or "").lower().strip()
    desc_clean = (job_description or "").lower()

    is_intern = bool(
        INTERNSHIP_TITLE_REGEX.search(t_clean)
        or emp_clean in ["intern", "internship", "trainee"]
        or "internship" in emp_clean
        or re.search(r"\b(internship opportunity|intern position|internship program|summer intern)\b", desc_clean[:600])
    )

    if is_intern:
        return {
            "level": SENIORITY_INTERNSHIP,
            "is_internship": True,
            "is_entry_level": False,
            "is_experienced": False,
            "display_seniority": "Internship",
            "badge_color": "#166534",
            "badge_bg": "#f0fdf4",
        }

    is_entry = bool(
        ENTRY_LEVEL_TITLE_REGEX.search(t_clean)
        or re.search(r"\b(entry[\s\-]level|junior developer|junior engineer|fresher|new grad|0[\s\-]1 years?|0[\s\-]2 years?|no experience required)\b", desc_clean[:600])
    )

    if is_entry:
        return {
            "level": SENIORITY_ENTRY_LEVEL,
            "is_internship": False,
            "is_entry_level": True,
            "is_experienced": False,
            "display_seniority": "Entry Level",
            "badge_color": "#854d0e",
            "badge_bg": "#fefce8",
        }

    return {
        "level": SENIORITY_EXPERIENCED,
        "is_internship": False,
        "is_entry_level": False,
        "is_experienced": True,
        "display_seniority": "Experienced",
        "badge_color": "#1e40af",
        "badge_bg": "#eff6ff",
    }


def detect_candidate_seniority_intent(
    resume_text: str = "",
    declared_title: str = "",
    experience_level_pref: str = "",
    job_type_pref: str = "",
    education_text: str = "",
) -> Dict[str, any]:
    """
    Detects whether a candidate is seeking internships or entry-level positions based on
    explicit preferences, declared title, and resume education/student indicators.
    """
    exp_pref = (experience_level_pref or "").lower().strip()
    type_pref = (job_type_pref or "").lower().strip()
    title = (declared_title or "").lower().strip()

    is_internship_seeking = False
    is_entry_level_seeking = False

    # 1. Check explicit user preferences
    if "intern" in exp_pref or "intern" in type_pref:
        is_internship_seeking = True
    if "entry" in exp_pref or "junior" in exp_pref or "fresh" in exp_pref:
        is_entry_level_seeking = True

    # 2. Check declared job title
    if INTERNSHIP_TITLE_REGEX.search(title) or "student" in title:
        is_internship_seeking = True
    elif ENTRY_LEVEL_TITLE_REGEX.search(title):
        is_entry_level_seeking = True

    # 3. Check resume and education text for student/internship indicators
    full_text = f"{resume_text} {education_text}".lower()
    for pattern in STUDENT_INTENT_PATTERNS:
        if re.search(pattern, full_text, re.IGNORECASE):
            is_internship_seeking = True
            break

    # Internship seekers are also naturally qualified for entry-level positions
    if is_internship_seeking:
        is_entry_level_seeking = True

    preferred_seniority = (
        SENIORITY_INTERNSHIP if is_internship_seeking
        else (SENIORITY_ENTRY_LEVEL if is_entry_level_seeking else SENIORITY_EXPERIENCED)
    )

    return {
        "is_internship_seeking": is_internship_seeking,
        "is_entry_level_seeking": is_entry_level_seeking,
        "preferred_seniority": preferred_seniority,
    }


def get_job_ordering_tuple(
    job: dict,
    is_internship_seeking: bool = False,
    is_entry_level_seeking: bool = False,
) -> Tuple[int, float]:
    """
    Calculates the ordering tuple (tier, -score) for candidate job recommendations.
    Ensures internships come first for internship-seeking candidates,
    followed by entry-level, then experienced positions.
    Unrelated career categories are always demoted to the bottom tier.
    """
    is_unrelated = job.get("is_unrelated_domain", False)
    score = float(job.get("combined_score", job.get("final_score", job.get("match_score", 0))))

    # Incompatible career category: always put at bottom (Tier 3)
    if is_unrelated:
        return (3, -score)

    is_intern = job.get("is_internship", False)
    is_entry = job.get("is_entry_level", False)

    if is_internship_seeking:
        # Tier 0: Relevant Internships (sorted by match score descending)
        # Tier 1: Suitable Entry-Level / Junior positions (sorted by match score descending)
        # Tier 2: Experienced positions (sorted by match score descending)
        if is_intern:
            tier = 0
        elif is_entry:
            tier = 1
        else:
            tier = 2
        return (tier, -score)

    if is_entry_level_seeking:
        # Tier 0: Entry-Level positions
        # Tier 1: Relevant Internships
        # Tier 2: Experienced positions
        if is_entry:
            tier = 0
        elif is_intern:
            tier = 1
        else:
            tier = 2
        return (tier, -score)

    # Experienced / general seekers: professional/experienced positions first (Tier 0), internships lower (Tier 1)
    tier = 1 if is_intern else 0
    return (tier, -score)

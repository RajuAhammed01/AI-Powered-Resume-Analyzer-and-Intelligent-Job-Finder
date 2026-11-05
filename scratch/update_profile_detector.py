import os

detector_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\services\profile_detector.py"

with open(detector_path, "r", encoding="utf-8") as f:
    content = f.read()

seniority_code = '''

# ── Seniority Classification & Tiered Recommendation Engine ──────────────

SENIORITY_INTERNSHIP = "internship"
SENIORITY_ENTRY_LEVEL = "entry_level"
SENIORITY_EXPERIENCED = "experienced"

INTERNSHIP_TITLE_REGEX = re.compile(
    r"\\b(intern|internship|trainee|co[\\s\\-]op|coop|working[\\s\\-]student|werkstudent|praktikant)\\b",
    re.IGNORECASE,
)

ENTRY_LEVEL_TITLE_REGEX = re.compile(
    r"\\b(junior|jr\\.?|entry[\\s\\-]level|associate|graduate|fresher|l1)\\b",
    re.IGNORECASE,
)

EXPERIENCED_TITLE_REGEX = re.compile(
    r"\\b(senior|sr\\.?|lead|principal|staff|architect|director|head of|manager|tech lead|mid[\\s\\-]level|experienced)\\b",
    re.IGNORECASE,
)

STUDENT_INTENT_PATTERNS = [
    r"\\b(seeking|looking for|open to|applying for)\\b.{0,40}\\b(intern|internship|co[\\s\\-]op|trainee|summer position)\\b",
    r"\\b(internship candidate|internship applicant|aspiring intern)\\b",
    r"\\b(undergraduate|bachelor student|masters student|graduate student|current student|phd student|university student|college student)\\b",
    r"\\b(pursuing\\s+(a\\s+)?(bachelor|master|b\\.?s|m\\.?s|b\\.?tech|b\\.?sc|m\\.?sc|ph\\.?d|degree|diploma))\\b",
    r"\\b(candidate for (bachelor|master|b\\.?s|m\\.?s|b\\.?tech|degree))\\b",
    r"\\b(expected graduation|expected to graduate|graduation year:?\\s*202[4-9]|class of 202[4-9]|graduation:?\\s*(may|june|dec|december|spring|summer|fall|winter)?\\s*202[4-9])\\b",
    r"\\b(student at|studying at|currently studying)\\b",
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
        or re.search(r"\\b(internship opportunity|intern position|internship program|summer intern)\\b", desc_clean[:600])
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
        or re.search(r"\\b(entry[\\s\\-]level|junior developer|junior engineer|fresher|new grad|0[\\s\\-]1 years?|0[\\s\\-]2 years?|no experience required)\\b", desc_clean[:600])
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

    # Experienced / general seekers: normal score ranking (Tier 0)
    return (0, -score)
'''

if "classify_job_seniority" not in content:
    with open(detector_path, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + "\n" + seniority_code)
    print("Successfully added seniority functions to profile_detector.py")
else:
    print("Already exists in profile_detector.py")


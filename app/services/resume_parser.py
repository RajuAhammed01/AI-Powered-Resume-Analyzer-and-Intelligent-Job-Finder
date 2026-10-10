import re

import pdfplumber
from docx import Document


def extract_text(filepath):
    try:
        if filepath.lower().endswith(".pdf"):
            return extract_pdf(filepath)
        if filepath.lower().endswith(".docx"):
            return extract_docx(filepath)
    except Exception as e:
        print(f"Error extracting text from {filepath}: {e}")
    return ""


def extract_pdf(filepath):
    pages = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
    except Exception as e:
        print(f"PDF extraction error: {e}")
    return "\n".join(pages)


def extract_docx(filepath):
    try:
        document = Document(filepath)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as e:
        print(f"DOCX extraction error: {e}")
        return ""


# Magic-byte validation (called BEFORE saving the file)
def is_valid_pdf(file_stream) -> bool:
    try:
        header = file_stream.read(4)
        file_stream.seek(0)
        return header == b"%PDF"
    except Exception:
        return False


def is_valid_docx(file_stream) -> bool:
    try:
        header = file_stream.read(4)
        file_stream.seek(0)
        return header == b"PK\x03\x04"
    except Exception:
        return False


def validate_upload(file, filename: str) -> bool:
    """Return True if the file's magic bytes match its declared extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return is_valid_pdf(file.stream)
    if ext == "docx" or ext == "doc":
        return is_valid_docx(file.stream) or is_valid_pdf(file.stream)
    return False


# ── Section keywords (case-insensitive) ────────────────────────────────────────
EDUCATION_KEYWORDS = [
    "education", "academic", "degree", "qualification", "university",
    "college", "school", "studies", "bachelor", "master", "phd",
]
EXPERIENCE_KEYWORDS = [
    "experience", "work history", "employment", "career", "professional",
    "job history", "positions held", "work experience",
]
SKILLS_KEYWORDS = ["skills", "technical skills", "competencies", "proficiencies"]
PROJECTS_KEYWORDS = ["projects", "portfolio", "achievements", "accomplishments"]


def _matches_section(line: str, keywords: list) -> bool:
    lower = line.lower().strip()
    return any(kw in lower for kw in keywords) and len(lower) < 60


def calculate_ats_score(text: str, structure: dict, skills: list) -> int:
    if not text or not text.strip():
        return 0
    score = 0
    # 1. Contact Info check (20 pts)
    contact = structure.get("contact_info", "")
    if "@" in contact:
        score += 10
    if re.search(r"\d{3}", contact):
        score += 10

    # 2. Key sections present (30 pts)
    if structure.get("education", "").strip():
        score += 15
    if structure.get("experience", "").strip():
        score += 15

    # 3. Skills density (25 pts)
    num_skills = len(skills) if skills else 0
    if num_skills >= 6:
        score += 25
    elif num_skills >= 3:
        score += 18
    elif num_skills >= 1:
        score += 10

    # 4. Content length and formatting (25 pts)
    words = len(text.split())
    if 150 <= words <= 1200:
        score += 25
    elif words > 50:
        score += 15
    else:
        score += 5

    return min(max(score, 15), 98)


def extract_structure(text: str) -> dict:
    if not text:
        return {
            "contact_info": "",
            "education": "",
            "experience": "",
            "completeness_score": 0,
        }

    email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    phone_pattern = r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"

    emails = re.findall(email_pattern, text)
    phones = re.findall(phone_pattern, text)
    contact = []
    if emails:
        contact.append(emails[0])
    if phones:
        contact.append(phones[0])

    lines = text.split("\n")
    education = []
    experience = []

    current_section = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if _matches_section(stripped, EDUCATION_KEYWORDS):
            current_section = "education"
            continue
        elif _matches_section(stripped, EXPERIENCE_KEYWORDS):
            current_section = "experience"
            continue
        elif _matches_section(stripped, SKILLS_KEYWORDS + PROJECTS_KEYWORDS):
            current_section = None
            continue

        if current_section == "education":
            education.append(stripped)
        elif current_section == "experience":
            experience.append(stripped)

    score = 0
    if emails:
        score += 25
    if phones:
        score += 15
    if education:
        score += min(30, max(15, len(education) * 5))
    if experience:
        score += min(30, max(15, len(experience) * 4))

    return {
        "contact_info": ", ".join(contact),
        "education": "\n".join(education[:5]),
        "experience": "\n".join(experience[:10]),
        "completeness_score": min(max(score, 0), 100),
    }

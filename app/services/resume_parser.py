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


def extract_structure(text: str) -> dict:
    if not text:
        return {
            "contact_info": "",
            "education": "",
            "experience": "",
            "completeness_score": 50,
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
        score += 20
    if phones:
        score += 20
    score += min(30, len(education) * 6)
    score += min(30, len(experience) * 3)

    return {
        "contact_info": ", ".join(contact),
        "education": "\n".join(education[:5]),
        "experience": "\n".join(experience[:10]),
        "completeness_score": min(max(score, 60), 100),
    }

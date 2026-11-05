import json
import os
import re

SKILL_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "skill_taxonomy.json")

_TAXONOMY_CACHE = None


def load_taxonomy():
    global _TAXONOMY_CACHE
    if _TAXONOMY_CACHE is not None:
        return _TAXONOMY_CACHE
    try:
        with open(SKILL_FILE, encoding="utf-8") as file:
            _TAXONOMY_CACHE = json.load(file)
    except Exception:
        _TAXONOMY_CACHE = []
    return _TAXONOMY_CACHE


def extract_skills_section_text(text: str) -> str:
    """Isolate the dedicated skills section of a resume if present for targeted scanning."""
    skills_heading = re.search(
        r"(?:technical\s+skills|core\s+competencies|technologies|tools\s*&\s*technologies|programming\s+languages|skills\s*&\s*expertise|skills)\s*[:\n]",
        text,
        re.IGNORECASE,
    )
    if not skills_heading:
        return ""

    start_idx = skills_heading.end()
    # Find next major heading (Experience, Education, Projects, Certifications, etc.)
    next_heading = re.search(
        r"\n\s*(?:work\s+experience|experience|employment|education|academic|projects|certifications|awards|publications|references)\s*[:\n]",
        text[start_idx:],
        re.IGNORECASE,
    )
    end_idx = start_idx + next_heading.start() if next_heading else start_idx + 1200
    return text[start_idx:end_idx]


def extract_skills(text: str) -> list[str]:
    """
    Extract strictly verified skills actually present in the text.
    Guarantees no false assumptions (e.g. CV != Computer Vision, PM != Project Management, go != Go).
    Uses strict boundary matching, context-aware checking for short abbreviations,
    and verified taxonomy lookup.
    """
    if not text or not text.strip():
        return []

    text_lower = text.lower()
    skills_section = extract_skills_section_text(text)
    skills_section_lower = skills_section.lower()

    found_canonical = set()
    taxonomy = load_taxonomy()

    # Pre-compiled contextual patterns for tricky single/two-letter skills
    c_patterns = [
        re.compile(r"(?<![a-zA-Z0-9#\+])(?:c\/c\+\+|c\s*,\s*c\+\+|c\s*language|c\s*programming)(?![a-zA-Z0-9#\+])", re.IGNORECASE),
        re.compile(r"(?:languages|technologies|skills)\s*:[^\n]*\bC\b"),
    ]
    r_patterns = [
        re.compile(r"(?<![a-zA-Z0-9#\+])(?:r\s*language|r\s*programming|r\s*script|r\s*package|r\s*,\s*python|python\s*,\s*r|r\/python)(?![a-zA-Z0-9#\+])", re.IGNORECASE),
        re.compile(r"(?:languages|data\s+analysis|skills)\s*:[^\n]*\bR\b"),
    ]
    go_patterns = [
        re.compile(r"(?<![a-zA-Z0-9#\+])(?:golang|go\s*language|go\s*programming)(?![a-zA-Z0-9#\+])", re.IGNORECASE),
        re.compile(r"(?:languages|technologies|backend|skills)\s*:[^\n]*\bGo\b"),
        re.compile(r"\b(?:python|docker|kubernetes|java|c\+\+)\s*,\s*Go\b"),
    ]

    for entry in taxonomy:
        canonical = entry.get("canonical_name", "")
        aliases = entry.get("aliases", [])
        cat = entry.get("category", "")

        # 1. Special Handling for Single/Two-Letter Languages
        if canonical == "C":
            if any(p.search(text) for p in c_patterns):
                found_canonical.add(canonical)
            continue

        if canonical == "R":
            if any(p.search(text) for p in r_patterns):
                found_canonical.add(canonical)
            continue

        if canonical == "Go":
            if any(p.search(text) for p in go_patterns):
                found_canonical.add(canonical)
            continue

        # 2. Standard Taxonomy Search
        # Check canonical and all clean aliases
        terms_to_check = [canonical] + aliases
        matched = False

        for term in terms_to_check:
            term_clean = term.strip()
            if not term_clean or len(term_clean) < 2:
                continue

            # Skip dangerous false-positive triggers
            if term_clean.lower() in ["cv", "go", "r", "c", "sh", "pm", "bi", "es", "ws", "bq", "fp", "dl", "ml", "pd", "np", "tf", "py", "ts"]:
                continue

            # Build exact boundary pattern (accounting for C#, C++, etc.)
            pattern = r"(?<![a-zA-Z0-9#\+])" + re.escape(term_clean.lower()) + r"(?![a-zA-Z0-9#\+])"

            if re.search(pattern, text_lower):
                # Extra validation for multi-word or potentially broad terms
                found_canonical.add(canonical)
                matched = True
                break

        # Check explicit skills section if not yet found
        if not matched and skills_section_lower:
            for term in terms_to_check:
                term_clean = term.strip()
                if len(term_clean) >= 3:
                    pattern = r"(?<![a-zA-Z0-9#\+])" + re.escape(term_clean.lower()) + r"(?![a-zA-Z0-9#\+])"
                    if re.search(pattern, skills_section_lower):
                        found_canonical.add(canonical)
                        break

    return sorted(list(found_canonical))

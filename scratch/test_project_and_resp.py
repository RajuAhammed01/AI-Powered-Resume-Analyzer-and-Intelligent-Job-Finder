import sys, re
sys.path.insert(0, ".")

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

sample_resume = """
John Doe
Frontend Developer
john@example.com

EXPERIENCE
Frontend Developer at Tech Corp (2022 - Present)
- Built interactive web portals using React and JavaScript.
- Collaborated with UX team to design responsive layouts.

PROJECTS
- E-Commerce Storefront: Developed a full-stack e-commerce web application using React, Redux, and Tailwind CSS. Integrated Stripe payments and REST APIs.
- Task Manager Dashboard: Built a responsive Kanban board with React and TypeScript.

EDUCATION
BS in Computer Science, University of California (2018 - 2022)
"""

sample_job = """
Frontend Developer
Hiring a Frontend Developer to join our core product team.

RESPONSIBILITIES:
- Build and optimize responsive web applications using React.
- Collaborate with designers and backend engineers to integrate RESTful APIs.
- Write clean, maintainable, and well-tested JavaScript code.

REQUIREMENTS:
- 2+ years of experience with React and modern JavaScript.
- Bachelor's degree in Computer Science or related field.
- Experience with Redux, Tailwind CSS, or TypeScript is a plus.
"""

proj = extract_projects_text(sample_resume)
resp = extract_job_responsibilities(sample_job)

print("Extracted Projects:", proj)
print("---")
print("Extracted Responsibilities:", resp)


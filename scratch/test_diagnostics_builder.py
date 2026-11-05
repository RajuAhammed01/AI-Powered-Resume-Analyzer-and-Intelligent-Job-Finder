import sys
sys.path.insert(0, ".")

from app.services.skill_gap import analyze_job_skill_gap

fe_skills = ["React", "JavaScript", "HTML5", "CSS3", "Tailwind CSS", "Redux", "Git"]
fe_cv = """
John Doe
Frontend Developer
john@example.com

EXPERIENCE
Frontend Developer at Tech Corp (2022 - Present)
- Built interactive web portals using React and JavaScript.
- Collaborated with UX team to design responsive layouts.

PROJECTS
- E-Commerce Storefront: Developed a full-stack e-commerce web application using React, Redux, and Tailwind CSS.
- Task Manager Dashboard: Built a responsive Kanban board with React.

EDUCATION
BS in Computer Science, University of California (2018 - 2022)
"""

job_desc = """
Frontend Developer
Hiring a Frontend Developer to build modern web applications.

RESPONSIBILITIES:
- Build and optimize responsive web applications using React.
- Collaborate with designers and backend engineers to integrate RESTful APIs.

REQUIREMENTS:
- 2+ years of experience with React and modern JavaScript.
- Bachelor's degree in Computer Science or related field.
- Experience with Next.js or TypeScript is a plus.
"""

job_skills = ["React", "JavaScript", "Next.js", "TypeScript", "Tailwind CSS", "Git", "Communication"]

res = analyze_job_skill_gap(
    resume_skills=fe_skills,
    job_skills=job_skills,
    resume_text=fe_cv,
    job_description=job_desc,
    candidate_title="Frontend Developer",
    job_title="Frontend Developer",
    candidate_domain="frontend",
)

print("Score:", res["final_score"])
print("Matched:", res["matched_skills"])
print("Partial:", res["partial_skills"])
print("Missing:", res["missing_skills"])
print("Explanation:", res["summary_explanation"])


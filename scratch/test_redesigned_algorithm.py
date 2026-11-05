import sys
sys.path.insert(0, ".")

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

from app.services.matcher import (
    education_qualification_score,
    experience_relevance_score,
    project_portfolio_score,
    responsibilities_alignment_score,
    title_alignment_score,
)

qual = education_qualification_score(fe_cv, job_desc)
exp = experience_relevance_score(fe_cv, job_desc)
proj, proj_r = project_portfolio_score(fe_cv, job_desc, job_skills=["React", "JavaScript", "Next.js", "TypeScript"])
resp, resp_r = responsibilities_alignment_score(fe_cv, job_desc)
title = title_alignment_score("Frontend Developer", "Frontend Developer", "frontend", "frontend")

print("Qual score:", qual)
print("Exp score:", exp)
print("Proj score:", proj, proj_r)
print("Resp score:", resp, resp_r)
print("Title score:", title)

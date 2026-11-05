import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app.services.skill_gap import analyze_job_skill_gap

fe_skills = ["React", "JavaScript", "TypeScript", "HTML5", "CSS3", "Tailwind CSS", "Redux", "Git"]
fe_cv = "Experienced Frontend Developer building scalable React web applications with TypeScript, Redux, and modern CSS."
job_skills = ["React", "TypeScript", "Next.js", "CSS3"]
job_desc = "Senior React Developer to build Next.js applications."

res = analyze_job_skill_gap(
    resume_skills=fe_skills,
    job_skills=job_skills,
    resume_text=fe_cv,
    job_description=job_desc,
    candidate_title="Frontend Developer",
    job_title="Senior React Developer",
    candidate_domain="frontend",
)

print("Final score:", res["final_score"])
print("Breakdown:", res["score_breakdown"])


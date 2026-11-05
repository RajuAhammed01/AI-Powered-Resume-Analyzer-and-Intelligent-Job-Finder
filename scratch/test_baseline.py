import sys
sys.path.insert(0, ".")

from app.services.skill_gap import analyze_job_skill_gap

fe_skills = ["React", "JavaScript", "HTML5", "CSS3", "Tailwind CSS", "Redux"]
res_react = analyze_job_skill_gap(
    resume_skills=fe_skills,
    job_skills=["React", "JavaScript", "TypeScript"],
    candidate_title="Frontend Developer",
    job_title="Senior React Developer",
)
print("res_react score:", res_react["final_score"], "is_unrelated:", res_react["is_unrelated_domain"])

res_sales = analyze_job_skill_gap(
    resume_skills=fe_skills,
    job_skills=["Sales", "CRM"],
    candidate_title="Frontend Developer",
    job_title="Sales Manager",
)
print("res_sales score:", res_sales["final_score"], "is_unrelated:", res_sales["is_unrelated_domain"])


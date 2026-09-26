def get_skill_gap(resume_skills, job_skills):
	resume_set = set(resume_skills)
	job_set = set(job_skills)
	return sorted(resume_set & job_set), sorted(job_set - resume_set)


def suggest_learning(missing_skills):
	return [f"Learn {skill} on Coursera or Udemy" for skill in missing_skills]

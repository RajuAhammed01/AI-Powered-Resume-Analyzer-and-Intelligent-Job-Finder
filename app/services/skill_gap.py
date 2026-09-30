import json
import os

def get_skill_gap(resume_skills, job_skills):
	resume_set = set(resume_skills)
	job_set = set(job_skills)
	return sorted(resume_set & job_set), sorted(job_set - resume_set)


def suggest_learning(missing_skills):
	resources_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'learning_resources.json')
	suggestions = []
	try:
		if os.path.exists(resources_path):
			with open(resources_path, 'r', encoding='utf-8') as f:
				resources = json.load(f)
			for skill in missing_skills:
				if skill.lower() in resources:
					suggestions.extend(resources[skill.lower()])
				else:
					suggestions.append({"title": f"Search for {skill} courses", "provider": "Coursera/Udemy", "url": f"https://www.coursera.org/search?query={skill}", "level": "Various", "cost": "Varies"})
	except Exception:
		pass
	
	if not suggestions and missing_skills:
		return [{"title": f"Search for {skill}", "provider": "Google", "url": f"https://www.google.com/search?q={skill}+course", "level": "Various", "cost": "Varies"} for skill in missing_skills]
	
	return suggestions

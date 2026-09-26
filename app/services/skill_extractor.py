import json
import os
import re

SKILL_FILE = os.path.join(os.getcwd(), "data", "skills.json")


def load_skills():
	with open(SKILL_FILE, encoding="utf-8") as file:
		data = json.load(file)
	return [skill for category in data.values() for skill in category]


def extract_skills(text):
	text_lower = text.lower()
	found = []
	for skill in load_skills():
		pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"
		if re.search(pattern, text_lower):
			found.append(skill.lower())
	return sorted(set(found))

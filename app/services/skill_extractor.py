import json
import os
import re

SKILL_FILE = os.path.join(os.getcwd(), "data", "skill_taxonomy.json")

_TAXONOMY_CACHE = None

def load_taxonomy():
	global _TAXONOMY_CACHE
	if _TAXONOMY_CACHE is not None:
		return _TAXONOMY_CACHE
	try:
		with open(SKILL_FILE, encoding="utf-8") as file:
			_TAXONOMY_CACHE = json.load(file)
	except FileNotFoundError:
		_TAXONOMY_CACHE = []
	return _TAXONOMY_CACHE


def extract_skills(text):
	text_lower = text.lower()
	found_canonical = set()
	taxonomy = load_taxonomy()
	
	for entry in taxonomy:
		canonical = entry.get("canonical_name", "")
		aliases = entry.get("aliases", [])
		
		# Check all aliases and canonical name
		terms_to_check = [canonical] + aliases
		for term in terms_to_check:
			pattern = r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)"
			if re.search(pattern, text_lower):
				found_canonical.add(canonical)
				break
				
	return sorted(list(found_canonical))

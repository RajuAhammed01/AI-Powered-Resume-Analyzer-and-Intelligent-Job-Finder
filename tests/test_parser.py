from app.services.skill_extractor import extract_skills


def test_extract_skills():
	text = "I know Python and SQL."
	skills = extract_skills(text)
	skills_lower = [s.lower() for s in skills]
	assert "python" in skills_lower
	assert "sql" in skills_lower

from app.services.skill_extractor import extract_skills


def test_extract_skills():
	text = "I know Python and SQL."
	skills = extract_skills(text)
	assert "python" in skills
	assert "sql" in skills

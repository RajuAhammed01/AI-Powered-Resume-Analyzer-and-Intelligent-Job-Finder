from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def basic_match_score(resume_skills, job_skills):
	if not job_skills:
		return 0
	matched = set(resume_skills) & set(job_skills)
	return int((len(matched) / len(set(job_skills))) * 100)


def tfidf_cosine_score(resume_text, job_description):
	if not resume_text.strip() or not job_description.strip():
		return 0
	vectorizer = TfidfVectorizer(stop_words="english")
	tfidf = vectorizer.fit_transform([resume_text, job_description])
	return int(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100)

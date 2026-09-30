import warnings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from sentence_transformers import SentenceTransformer
    _MODEL = None
except ImportError:
    _MODEL = False

def get_sentence_transformer():
    global _MODEL
    if _MODEL is False:
        return None
    if _MODEL is None:
        try:
            # Load small model for fast CPU inference
            _MODEL = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception:
            _MODEL = False
            return None
    return _MODEL

def basic_match_score(resume_skills, job_skills):
	if not job_skills:
		return 0
	matched = set(resume_skills) & set(job_skills)
	return int((len(matched) / len(set(job_skills))) * 100)

def tfidf_cosine_score(resume_text, job_description):
	if not resume_text.strip() or not job_description.strip():
		return 0
	
	model = get_sentence_transformer()
	if model is not None:
	    embeddings = model.encode([resume_text, job_description])
	    return int(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0] * 100)
	
	# Fallback to TF-IDF
	vectorizer = TfidfVectorizer(stop_words="english")
	tfidf = vectorizer.fit_transform([resume_text, job_description])
	return int(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100)

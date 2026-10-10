import warnings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from sentence_transformers import SentenceTransformer
    _MODEL = None
except ImportError:
    _MODEL = False

_EMBED_CACHE = {}


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


def _get_embedding(text: str):
    model = get_sentence_transformer()
    if model is None:
        return None
    key = (len(text), text[:250])
    if key not in _EMBED_CACHE:
        _EMBED_CACHE[key] = model.encode(text)
    return _EMBED_CACHE[key]


def basic_match_score(resume_skills, job_skills):
    if not job_skills:
        return 0
    matched = set(resume_skills) & set(job_skills)
    return int((len(matched) / len(set(job_skills))) * 100)


def tfidf_cosine_score(resume_text, job_description):
    if not resume_text.strip() or not job_description.strip():
        return 0

    emb_resume = _get_embedding(resume_text)
    if emb_resume is not None:
        emb_job = _get_embedding(job_description)
        if emb_job is not None:
            return int(cosine_similarity([emb_resume], [emb_job])[0][0] * 100)

    # Fallback to TF-IDF
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform([resume_text, job_description])
    return int(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100)

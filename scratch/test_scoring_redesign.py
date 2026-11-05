import re
from app.services.matcher import (
    education_qualification_score,
    experience_relevance_score,
    focused_semantic_score,
    title_alignment_score,
)
from app.services.profile_detector import (
    classify_job_domain,
    is_job_domain_compatible,
)

print("Matcher and profile_detector loaded successfully.")


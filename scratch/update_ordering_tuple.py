path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\services\profile_detector.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

old_tail = """    # Experienced / general seekers: normal score ranking (Tier 0)
    return (0, -score)"""

new_tail = """    # Experienced / general seekers: professional/experienced positions first (Tier 0), internships lower (Tier 1)
    tier = 1 if is_intern else 0
    return (tier, -score)"""

assert old_tail in code, "old_tail not found in profile_detector.py"
code = code.replace(old_tail, new_tail)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("Updated get_job_ordering_tuple in profile_detector.py successfully.")


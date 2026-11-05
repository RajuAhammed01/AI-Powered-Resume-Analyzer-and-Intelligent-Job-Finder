jobs_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\routes\jobs.py"
with open(jobs_path, "r", encoding="utf-8") as f:
    jcode = f.read()

target_str = """        job["badge_bg"] = analysis.get("badge_bg", "#eff6ff")
        job["cache_id"] = index"""

replace_str = """        job["badge_bg"] = analysis.get("badge_bg", "#eff6ff")
        job["qualifications_score"] = analysis.get("qualifications_score", 70)
        job["projects_score"] = analysis.get("projects_score", 70)
        job["responsibilities_score"] = analysis.get("responsibilities_score", 70)
        job["strong_skills"] = analysis.get("strong_skills", [])
        job["missing_skills_detailed"] = analysis.get("missing_skills_detailed", [])
        job["detailed_diagnostic"] = analysis.get("detailed_diagnostic", {})
        job["cache_id"] = index"""

if target_str in jcode:
    jcode = jcode.replace(target_str, replace_str)
    with open(jobs_path, "w", encoding="utf-8") as f:
        f.write(jcode)
    print("jobs.py updated with new diagnostic fields.")
else:
    print("Warning: target_str not found in jobs.py")

main_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\routes\main.py"
with open(main_path, "r", encoding="utf-8") as f:
    mcode = f.read()

if target_str in mcode:
    mcode = mcode.replace(target_str, replace_str)
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(mcode)
    print("main.py updated with new diagnostic fields.")
else:
    print("Warning: target_str not found in main.py")


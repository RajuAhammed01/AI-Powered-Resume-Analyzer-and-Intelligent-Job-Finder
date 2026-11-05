results_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\templates\results.html"

with open(results_path, "r", encoding="utf-8") as f:
    rhtml = f.read()

old_formula_strip = """                    <strong>Why {{ job.combined_score }}%?</strong> Skill (35%): {{ job.score_breakdown.skill_coverage_pts }} pts • Semantic (25%): {{ job.score_breakdown.semantic_pts }} pts • Title & Role (20%): {{ job.score_breakdown.title_pts }} pts • Exp (10%): {{ job.score_breakdown.experience_pts }} pts • Edu (10%): {{ job.score_breakdown.education_pts }} pts"""

new_formula_strip = """                    <strong>Why {{ job.combined_score }}%?</strong> Skills (35%): {{ job.score_breakdown.skill_coverage_pts }} pts • Quals (15%): {{ job.score_breakdown.qualifications_pts or job.score_breakdown.education_pts }} pts • Exp (15%): {{ job.score_breakdown.experience_pts }} pts • Projects (15%): {{ job.score_breakdown.projects_pts or 0 }} pts • Tasks (10%): {{ job.score_breakdown.responsibilities_pts or job.score_breakdown.semantic_pts }} pts • Career (10%): {{ job.score_breakdown.title_pts }} pts"""

if old_formula_strip in rhtml:
    rhtml = rhtml.replace(old_formula_strip, new_formula_strip)
    with open(results_path, "w", encoding="utf-8") as f:
        f.write(rhtml)
    print("results.html updated successfully.")
else:
    print("Warning: old_formula_strip not matched in results.html")


skill_gap_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\services\skill_gap.py"

with open(skill_gap_path, "r", encoding="utf-8") as f:
    text = f.read()

target_return = """        # Three-Tier Skill Matches
        "strong_skills": strong_skills,"""

replace_return = """        # Backward-compatible skill points breakdown
        "skill_points": {
            "exact_count": len(strong_skills),
            "exact_points": sum(s["points_earned"] for s in strong_skills),
            "partial_count": len(partial_skills),
            "partial_points": sum(p["points_earned"] for p in partial_skills),
            "missing_count": len(missing_skills_detailed),
            "total_required": len(strong_skills) + len(partial_skills) + len(missing_skills_detailed),
            "total_points_earned": earned_points,
            "max_possible_points": max_possible_points,
            "skill_contribution_pts": skill_contrib,
            "qualifications_contribution_pts": qual_contrib,
            "experience_contribution_pts": exp_contrib,
            "projects_contribution_pts": proj_contrib,
            "responsibilities_contribution_pts": resp_contrib,
            "title_contribution_pts": domain_contrib,
        },

        # Three-Tier Skill Matches
        "strong_skills": strong_skills,"""

if target_return in text:
    text = text.replace(target_return, replace_return)
    with open(skill_gap_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("skill_gap.py updated with skill_points.")
else:
    print("Warning: target_return not found in skill_gap.py")


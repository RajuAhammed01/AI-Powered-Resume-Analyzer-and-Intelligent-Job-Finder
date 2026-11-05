import pytest
from app.services.skill_gap import analyze_job_skill_gap
from app.services.matcher import (
    project_portfolio_score,
    responsibilities_alignment_score,
    extract_projects_text,
    extract_job_responsibilities,
)


def test_three_tier_skill_distinction():
    """
    Clearly distinguish between strong, partial, and missing skill matches.
    """
    resume_skills = ["React", "JavaScript", "HTML5", "CSS3", "Git"]
    job_skills = ["React", "JavaScript", "TypeScript", "Next.js", "Docker", "Communication"]

    resume_text = """
    Alice Smith
    Frontend Engineer
    alice@example.com

    EXPERIENCE
    Frontend Engineer at WebStudio (2021 - Present)
    - Developed web interfaces using React and JavaScript.
    - Utilized Git for version control and collaborated with team members.

    PROJECTS
    - React Portfolio: Built single page responsive web app with React and CSS.

    EDUCATION
    BS in Computer Science (2017 - 2021)
    """

    job_desc = """
    Frontend Developer
    Responsibilities:
    - Build modern user interfaces using React and modern JavaScript.
    - Integrate REST APIs and collaborate with backend developers.
    Requirements:
    - Proven experience in React and JavaScript.
    - Familiarity with TypeScript and Next.js is preferred.
    - Docker containerization is a plus.
    """

    res = analyze_job_skill_gap(
        resume_skills=resume_skills,
        job_skills=job_skills,
        resume_text=resume_text,
        job_description=job_desc,
        candidate_title="Frontend Engineer",
        job_title="Frontend Developer",
        candidate_domain="frontend",
    )

    # 1. Strong / verified matches
    assert "React" in res["matched_skills"]
    assert "JavaScript" in res["matched_skills"]
    assert any(s["skill"] == "React" and s["strength"] == "Strong Match" for s in res["strong_skills"])
    assert any(s["skill"] == "JavaScript" and s["strength"] == "Strong Match" for s in res["strong_skills"])

    # 2. Partial matches via transferable foundations
    partial_names = [p["skill"] for p in res["partial_skills"]]
    assert "Next.js" in partial_names, "Next.js should be partially matched via React"
    assert "TypeScript" in partial_names, "TypeScript should be partially matched via JavaScript"
    next_partial = next(p for p in res["partial_skills"] if p["skill"] == "Next.js")
    assert next_partial["matched_via"] == "React"
    assert "Next.js is a server-side rendered framework built on React" in next_partial["reason"]

    # 3. Missing skills with priority
    missing_names = [m["skill"] for m in res["missing_skills_detailed"]]
    assert "Docker" in missing_names
    docker_missing = next(m for m in res["missing_skills_detailed"] if m["skill"] == "Docker")
    assert docker_missing["type"] == "missing"
    assert docker_missing["strength"] == "Missing Skill"


def test_realistic_scoring_six_dimensions():
    """
    Verifies that match scores are calculated realistically across 6 dimensions:
    technical skill overlap, qualifications, experience, projects, responsibilities, and career relevance.
    """
    resume_skills = ["React", "JavaScript", "HTML5", "CSS3", "Tailwind CSS", "Redux", "Git"]
    resume_text = """
    Bob Developer
    Frontend Developer
    bob@example.com | https://github.com/bobdev

    EXPERIENCE
    Frontend Developer at AppCo (2021 - Present)
    - Developed high-performance single page web applications using React.
    - Integrated backend RESTful services and styled UI with Tailwind CSS.

    PROJECTS
    - E-Commerce Web Store: Built end-to-end online store using React, Redux, and Tailwind CSS.
    - Analytics Dashboard: Designed responsive charting platform using React and JavaScript.

    EDUCATION
    Bachelor of Science in Computer Science, State University (2017 - 2021)
    """

    job_desc = """
    Frontend Developer
    RESPONSIBILITIES:
    - Build and maintain modern user interfaces using React.
    - Collaborate with backend engineers to consume RESTful endpoints.
    - Write clean, maintainable frontend code and perform code reviews.
    REQUIREMENTS:
    - 2+ years of experience with React and modern JavaScript.
    - Bachelor's degree in Computer Science or related technical discipline.
    - Familiarity with Tailwind CSS and Redux is a plus.
    """

    job_skills = ["React", "JavaScript", "Tailwind CSS", "Redux", "REST API", "Git"]

    res = analyze_job_skill_gap(
        resume_skills=resume_skills,
        job_skills=job_skills,
        resume_text=resume_text,
        job_description=job_desc,
        candidate_title="Frontend Developer",
        job_title="Frontend Developer",
        candidate_domain="frontend",
    )

    # Candidate satisfies core technical skills, degree, projects, and responsibilities
    assert res["is_unrelated_domain"] is False
    assert res["final_score"] >= 80, f"Expected realistic high score (>=80), got {res['final_score']}"

    # Verify score breakdown contains all 6 dimensions
    bd = res["score_breakdown"]
    assert "skill_coverage_pct" in bd
    assert "qualifications_pct" in bd
    assert "experience_score_pct" in bd
    assert "projects_pct" in bd
    assert "responsibilities_pct" in bd
    assert "title_score_pct" in bd

    # Verify transparent diagnostic reasons
    diag = res["detailed_diagnostic"]
    assert diag["verdict"].startswith("Strong Match")
    assert len(diag["strong_reasons"]) >= 2
    assert "actionable_steps" in diag


def test_unrelated_jobs_cannot_receive_high_scores():
    """
    Ensure unrelated jobs (e.g. Freelance Writer, Copywriter, Network Engineer, Medical Nurse)
    cannot receive artificially high scores even if a few generic keywords overlap.
    """
    fe_skills = ["React", "JavaScript", "HTML5", "CSS3", "Tailwind CSS", "Git", "Communication", "Problem Solving"]
    fe_text = "Frontend Developer with React, JavaScript, HTML, CSS, Git, and Communication."

    unrelated_roles = [
        ("Freelance Writer", "Write engaging articles, research topics, proofread text, use Git and communication.", ["Writing", "Research", "Git", "Communication"]),
        ("Content Writer", "Produce marketing content and blog posts with strong English communication.", ["Content", "Communication", "English", "Proofreading"]),
        ("Network Engineer", "Configure Cisco switches, routers, TCP/IP, Linux servers, and networking protocols.", ["Cisco", "TCP/IP", "Linux", "Networking", "Git", "Communication"]),
        ("Registered Nurse", "Provide acute patient care, monitor vital signs, and maintain electronic health records.", ["Patient Care", "Nursing", "Healthcare", "Communication"]),
        ("Senior Sales Account Executive", "Drive enterprise SaaS sales, outbound prospecting, and CRM management.", ["Sales", "CRM", "Cold Calling", "Communication", "Negotiation"]),
    ]

    for title, desc, skills in unrelated_roles:
        res = analyze_job_skill_gap(
            resume_skills=fe_skills,
            job_skills=skills,
            resume_text=fe_text,
            job_description=desc,
            candidate_title="Frontend Developer",
            job_title=title,
            candidate_domain="frontend",
        )

        assert res["is_unrelated_domain"] is True, f"{title} must be flagged as unrelated domain"
        assert res["final_score"] <= 18, f"{title} score must be <= 18%, got {res['final_score']}%"
        assert "Unrelated Career Category" in res["summary_explanation"]
        assert "Unrelated Category" in res["detailed_diagnostic"]["verdict"]


def test_project_portfolio_and_responsibilities_extraction():
    """
    Verifies that projects and job responsibilities are correctly extracted and scored.
    """
    resume_text = """
    Software Developer
    PROJECTS:
    - Smart Home Dashboard: Developed IoT home automation portal using React and Python.
    - Cloud File Storage: Implemented secure file sharing system with AWS S3 and Flask.
    """

    job_text = """
    Software Engineer
    RESPONSIBILITIES:
    - Develop scalable web applications using React.
    - Implement REST APIs and secure cloud integrations.
    """

    proj_text = extract_projects_text(resume_text)
    assert "Smart Home Dashboard" in proj_text
    assert "Cloud File Storage" in proj_text

    resp_text = extract_job_responsibilities(job_text)
    assert "Develop scalable web applications" in resp_text
    assert "Implement REST APIs" in resp_text

    proj_score, proj_rationale = project_portfolio_score(resume_text, job_text, job_skills=["React", "Python", "Flask"])
    assert proj_score >= 60
    assert "React" in proj_rationale or "projects" in proj_rationale.lower()

    resp_score, resp_rationale = responsibilities_alignment_score(resume_text, job_text)
    assert resp_score >= 50


detail_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\templates\job_detail.html"

with open(detail_path, "r", encoding="utf-8") as f:
    text = f.read()

old_section = """        <!-- Transparent Score Explanation Section -->
        <div style="margin-bottom: 2rem; background: #f8fafc; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <h3 style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 800; color: var(--text-main); margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fa-solid fa-calculator" style="color: var(--primary);"></i> Why is your match score {{ job.get('combined_score', 80) }}%?
                </h3>
                <span class="badge-pill badge-match-high" style="font-size: 0.8rem;">
                    Transparent AI Evaluation
                </span>
            </div>

            <!-- Mathematical Breakdown Formula Grid: 5 Core Dimensions -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.75rem; margin-bottom: 1rem;">
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Skill Coverage (35%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #047857;">{{ job.get('score_breakdown', {}).get('skill_coverage_pct', job.get('match_score', 0)) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #047857;">{{ job.get('score_breakdown', {}).get('skill_coverage_pts', 0) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Tech skills carry higher weight than soft skills
                    </div>
                </div>

                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Semantic Alignment (25%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #2563eb;">{{ job.get('score_breakdown', {}).get('semantic_score_pct', job.get('cosine_score', 0)) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #2563eb;">{{ job.get('score_breakdown', {}).get('semantic_pts', 0) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Focused experience signal via Sentence-BERT
                    </div>
                </div>

                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Title & Role Match (20%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #7c3aed;">{{ job.get('score_breakdown', {}).get('title_score_pct', 80) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #7c3aed;">{{ job.get('score_breakdown', {}).get('title_pts', 16) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Career domain and role hierarchy fit
                    </div>
                </div>

                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Experience Fit (10%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #ea580c;">{{ job.get('score_breakdown', {}).get('experience_score_pct', 70) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #ea580c;">{{ job.get('score_breakdown', {}).get('experience_pts', 7) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Seniority & domain work history alignment
                    </div>
                </div>

                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Education & Quals (10%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #0891b2;">{{ job.get('score_breakdown', {}).get('education_score_pct', 80) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #0891b2;">{{ job.get('score_breakdown', {}).get('education_pts', 8) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Degree level & discipline qualification match
                    </div>
                </div>
            </div>

            <!-- Detailed Explanation Text -->
            <div style="font-size: 0.88rem; color: var(--text-main); line-height: 1.6; background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.85rem 1rem; margin-bottom: 0.75rem;">
                <i class="fa-solid fa-circle-info" style="color: var(--primary); margin-right: 0.35rem;"></i>
                {{ job.get('score_explanation', 'Your match score combines skill coverage and semantic experience overlap.') }}
            </div>

            <div style="font-size: 0.85rem; color: #166534; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: var(--radius-sm); padding: 0.65rem 0.85rem;">
                <i class="fa-solid fa-lightbulb" style="color: #16a34a; margin-right: 0.35rem;"></i>
                <strong>Next Step to Boost Score:</strong> {{ job.get('actionable_advice', 'Review required competencies to optimize your compatibility.') }}
            </div>
        </div>

        <!-- Section 2: Detailed 3-Tier Skill Gap Breakdown -->
        <div style="margin-bottom: 2rem;">
            <h3 style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 700; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                <i class="fa-solid fa-list-check" style="color: var(--primary);"></i> Three-Tier Skill Compatibility Analysis
            </h3>
            
            <!-- 1. Exact Matched Skills -->
            <div style="margin-bottom: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="font-weight: 700; font-size: 0.88rem; color: #166534;">
                        <i class="fa-solid fa-circle-check" style="color: var(--success); margin-right: 0.35rem;"></i> Verified in Your Resume ({{ job.get('matched_skills', [])|length }})
                    </div>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">Earns 1.0 pt each</span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
                    {% for skill in job.get('matched_skills', []) %}
                        <span class="badge-pill badge-skill-extracted" style="font-size: 0.82rem; padding: 0.3rem 0.7rem;">
                            <i class="fa-solid fa-check" style="margin-right: 4px;"></i> {{ skill }}
                        </span>
                    {% else %}
                        <span style="font-size: 0.82rem; color: var(--text-muted); font-style: italic;">No direct skill keyword matches detected in CV.</span>
                    {% endfor %}
                </div>
            </div>

            <!-- 2. Partially Matched Skills -->
            {% if job.get('partial_skills') %}
            <div style="margin-bottom: 1.25rem; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: var(--radius-sm); padding: 0.85rem 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="font-weight: 700; font-size: 0.88rem; color: #1e40af;">
                        <i class="fa-solid fa-circle-half-stroke" style="color: #2563eb; margin-right: 0.35rem;"></i> Partially Matched via Related Skills ({{ job.get('partial_skills', [])|length }})
                    </div>
                    <span style="font-size: 0.75rem; color: #1e3a8a;">Earns 0.5 pt each</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    {% for p in job.get('partial_skills', []) %}
                    <div style="background: white; border: 1px solid #dbeafe; border-radius: 6px; padding: 0.5rem 0.75rem; font-size: 0.82rem;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.2rem;">
                            <strong style="color: #1e40af;">{{ p.skill }}</strong>
                            <span style="color: #2563eb; font-weight: 600;">Matched via your verified skill: <u>{{ p.matched_via }}</u></span>
                        </div>
                        <div style="color: var(--text-muted); font-size: 0.78rem;">
                            {{ p.reason }}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            <!-- 3. Missing Skills -->
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="font-weight: 700; font-size: 0.88rem; color: #991b1b;">
                        <i class="fa-solid fa-triangle-exclamation" style="color: var(--danger); margin-right: 0.35rem;"></i> Missing Competencies ({{ job.get('missing_skills', [])|length }})
                    </div>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">Required for 100% fit</span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
                    {% for skill in job.get('missing_skills', []) %}
                        <span class="badge-pill badge-skill-missing" style="font-size: 0.82rem; padding: 0.3rem 0.7rem;">
                            <i class="fa-solid fa-xmark" style="margin-right: 4px;"></i> {{ skill }}
                        </span>
                    {% else %}
                        <span class="badge-pill badge-match-high">All required skills matched!</span>
                    {% endfor %}
                </div>
            </div>
        </div>"""

new_section = """        <!-- Transparent Score Explanation Section -->
        <div style="margin-bottom: 2rem; background: #f8fafc; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem;">
                <h3 style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 800; color: var(--text-main); margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fa-solid fa-calculator" style="color: var(--primary);"></i> Why is your match score {{ job.get('combined_score', 80) }}%?
                </h3>
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    {% if job.get('is_unrelated_domain') %}
                    <span class="badge-pill" style="background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; font-size: 0.8rem; font-weight: 700;">
                        <i class="fa-solid fa-triangle-exclamation"></i> Unrelated Category Penalty Applied
                    </span>
                    {% else %}
                    <span class="badge-pill badge-match-high" style="font-size: 0.8rem;">
                        <i class="fa-solid fa-circle-check"></i> Realistic 6-Dimension Score
                    </span>
                    {% endif %}
                </div>
            </div>

            <!-- Mathematical Breakdown Formula Grid: 6 Core Realistic Dimensions -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(135px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem;">
                <!-- 1. Technical Skill Overlap -->
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Technical Skills (35%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #047857;">{{ job.get('score_breakdown', {}).get('skill_coverage_pct', job.get('match_score', 0)) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #047857;">{{ job.get('score_breakdown', {}).get('skill_coverage_pts', 0) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Core technical vs transferable vs soft skills
                    </div>
                </div>

                <!-- 2. Required Qualifications & Education -->
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Qualifications (15%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #0891b2;">{{ job.get('score_breakdown', {}).get('qualifications_pct', job.get('education_score', 75)) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #0891b2;">{{ job.get('score_breakdown', {}).get('qualifications_pts', 11) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Degree level, academic field, certifications
                    </div>
                </div>

                <!-- 3. Professional Experience -->
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Experience (15%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #ea580c;">{{ job.get('score_breakdown', {}).get('experience_score_pct', job.get('experience_score', 70)) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #ea580c;">{{ job.get('score_breakdown', {}).get('experience_pts', 10) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Tenure years & seniority depth fit
                    </div>
                </div>

                <!-- 4. Projects & Portfolio -->
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Projects & Works (15%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #7c3aed;">{{ job.get('score_breakdown', {}).get('projects_pct', job.get('projects_score', 75)) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #7c3aed;">{{ job.get('score_breakdown', {}).get('projects_pts', 11) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Practical implementation & GitHub evidence
                    </div>
                </div>

                <!-- 5. Job Responsibilities -->
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Responsibilities (10%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #2563eb;">{{ job.get('score_breakdown', {}).get('responsibilities_pct', job.get('cosine_score', 70)) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #2563eb;">{{ job.get('score_breakdown', {}).get('responsibilities_pts', 7) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Daily duties & execution actions overlap
                    </div>
                </div>

                <!-- 6. Career Relevance & Domain Fit -->
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 0.75rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Career Fit (10%)
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.25rem;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: {% if job.get('is_unrelated_domain') %}#dc2626{% else %}#059669{% endif %};">{{ job.get('score_breakdown', {}).get('title_score_pct', 80) }}%</span>
                        <span style="font-size: 0.75rem; font-weight: 700; color: {% if job.get('is_unrelated_domain') %}#dc2626{% else %}#059669{% endif %};">{{ job.get('score_breakdown', {}).get('title_pts', 8) }} pts</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.35rem;">
                        Career domain compatibility & title alignment
                    </div>
                </div>
            </div>

            <!-- Transparent Diagnostics: Verdict, Strengths & Deductions -->
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: var(--radius-sm); padding: 1rem; margin-bottom: 0.75rem;">
                <div style="font-weight: 700; font-size: 0.92rem; color: var(--text-main); margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between;">
                    <span><i class="fa-solid fa-clipboard-check" style="color: var(--primary); margin-right: 0.35rem;"></i> Diagnostic Evaluation Verdict:</span>
                    <span style="font-size: 0.82rem; font-weight: 700; color: {% if job.get('is_unrelated_domain') %}#dc2626{% elif job.get('combined_score', 0) >= 80 %}#166534{% elif job.get('combined_score', 0) >= 65 %}#1e40af{% else %}#b45309{% endif %};">
                        {{ job.get('detailed_diagnostic', {}).get('verdict', 'Evaluated Match') }}
                    </span>
                </div>
                
                <div style="font-size: 0.85rem; color: var(--text-main); line-height: 1.5; margin-bottom: 0.75rem;">
                    {{ job.get('score_explanation', 'Your match score is calculated transparently across verified technical skills, qualifications, experience, and projects.') }}
                </div>

                {% if job.get('detailed_diagnostic', {}).get('strong_reasons') %}
                <div style="margin-bottom: 0.6rem;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #166534; margin-bottom: 0.25rem;">
                        <i class="fa-solid fa-arrow-up" style="color: #16a34a;"></i> Key Positive Fit Factors:
                    </div>
                    <ul style="margin: 0; padding-left: 1.25rem; font-size: 0.8rem; color: #1f2937; line-height: 1.45;">
                        {% for r in job.detailed_diagnostic.strong_reasons %}
                        <li>{{ r }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}

                {% if job.get('detailed_diagnostic', {}).get('gap_reasons') %}
                <div>
                    <div style="font-size: 0.78rem; font-weight: 700; color: #991b1b; margin-bottom: 0.25rem;">
                        <i class="fa-solid fa-circle-exclamation" style="color: #dc2626;"></i> Areas with Score Deductions / Gaps:
                    </div>
                    <ul style="margin: 0; padding-left: 1.25rem; font-size: 0.8rem; color: #4b5563; line-height: 1.45;">
                        {% for g in job.detailed_diagnostic.gap_reasons %}
                        <li>{{ g }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}
            </div>

            <!-- Actionable Next Step -->
            <div style="font-size: 0.85rem; color: #166534; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: var(--radius-sm); padding: 0.65rem 0.85rem;">
                <i class="fa-solid fa-lightbulb" style="color: #16a34a; margin-right: 0.35rem;"></i>
                <strong>Next Step to Boost Score:</strong> {{ job.get('actionable_advice', 'Review required competencies to optimize your compatibility.') }}
            </div>
        </div>

        <!-- Section 2: Detailed 3-Tier Skill Gap Breakdown -->
        <div style="margin-bottom: 2rem;">
            <h3 style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 700; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                <i class="fa-solid fa-list-check" style="color: var(--primary);"></i> Three-Tier Skill Compatibility Analysis
            </h3>
            
            <!-- 1. Strong / Verified Matched Skills -->
            <div style="margin-bottom: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="font-weight: 700; font-size: 0.88rem; color: #166534;">
                        <i class="fa-solid fa-circle-check" style="color: var(--success); margin-right: 0.35rem;"></i> Strong / Verified Matches ({{ job.get('matched_skills', [])|length }})
                    </div>
                    <span style="font-size: 0.75rem; color: #166534; font-weight: 600;">Full Credit (100%)</span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
                    {% for skill in job.get('matched_skills', []) %}
                        <span class="badge-pill badge-skill-extracted" style="font-size: 0.82rem; padding: 0.3rem 0.7rem;" title="Directly verified in your resume">
                            <i class="fa-solid fa-check" style="margin-right: 4px;"></i> {{ skill }}
                        </span>
                    {% else %}
                        <span style="font-size: 0.82rem; color: var(--text-muted); font-style: italic;">No direct skill matches detected in CV.</span>
                    {% endfor %}
                </div>
            </div>

            <!-- 2. Partially Matched Skills (Transferable Frameworks & Tools) -->
            {% if job.get('partial_skills') %}
            <div style="margin-bottom: 1.25rem; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: var(--radius-sm); padding: 0.85rem 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="font-weight: 700; font-size: 0.88rem; color: #1e40af;">
                        <i class="fa-solid fa-circle-half-stroke" style="color: #2563eb; margin-right: 0.35rem;"></i> Partially Matched via Transferable Skills ({{ job.get('partial_skills', [])|length }})
                    </div>
                    <span style="font-size: 0.75rem; color: #1e3a8a; font-weight: 600;">Partial Credit (50% - 60%)</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    {% for p in job.get('partial_skills', []) %}
                    <div style="background: white; border: 1px solid #dbeafe; border-radius: 6px; padding: 0.5rem 0.75rem; font-size: 0.82rem;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.2rem; flex-wrap: wrap; gap: 0.25rem;">
                            <strong style="color: #1e40af;"><i class="fa-solid fa-arrow-right-arrow-left" style="font-size: 0.75rem;"></i> {{ p.skill }}</strong>
                            <span class="badge-pill" style="background: #dbeafe; color: #1e40af; font-size: 0.72rem; padding: 0.1rem 0.45rem;">
                                Matched via your verified skill: <strong>{{ p.matched_via }}</strong>
                            </span>
                        </div>
                        <div style="color: var(--text-muted); font-size: 0.78rem;">
                            {{ p.reason }}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            <!-- 3. Missing Skills with Priority Ranking -->
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="font-weight: 700; font-size: 0.88rem; color: #991b1b;">
                        <i class="fa-solid fa-triangle-exclamation" style="color: var(--danger); margin-right: 0.35rem;"></i> Missing Competencies ({{ job.get('missing_skills', [])|length }})
                    </div>
                    <span style="font-size: 0.75rem; color: #991b1b; font-weight: 600;">Zero Credit</span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
                    {% for item in job.get('missing_skills_detailed', []) %}
                        <span class="badge-pill badge-skill-missing" style="font-size: 0.82rem; padding: 0.3rem 0.7rem;" title="{{ item.impact }}">
                            <i class="fa-solid fa-xmark" style="margin-right: 4px;"></i> {{ item.skill }}
                            {% if item.priority == 'High Priority' %}
                            <span style="background: #fee2e2; color: #991b1b; border-radius: 4px; padding: 0.05rem 0.3rem; font-size: 0.68rem; margin-left: 4px; font-weight: 700;">Core</span>
                            {% endif %}
                        </span>
                    {% else %}
                        {% for skill in job.get('missing_skills', []) %}
                        <span class="badge-pill badge-skill-missing" style="font-size: 0.82rem; padding: 0.3rem 0.7rem;">
                            <i class="fa-solid fa-xmark" style="margin-right: 4px;"></i> {{ skill }}
                        </span>
                        {% else %}
                        <span class="badge-pill badge-match-high">All required competencies matched!</span>
                        {% endfor %}
                    {% endfor %}
                </div>
            </div>
        </div>"""

if old_section in text:
    text = text.replace(old_section, new_section)
    with open(detail_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("job_detail.html updated successfully with redesigned scoring and diagnostics.")
else:
    print("Warning: old_section not found in job_detail.html")


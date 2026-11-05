results_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\templates\results.html"
with open(results_path, "r", encoding="utf-8") as f:
    results_html = f.read()

# 1. Add internship seeker banner in header if is_internship_seeking
old_profile_banner = """                <span class="badge-pill" style="background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; font-size: 0.8rem; font-weight: 600; padding: 0.2rem 0.65rem;">
                    <i class="fa-solid fa-crosshairs"></i> Target Roles: {{ candidate_profile.search_queries|join(' • ') }}
                </span>
            </div>
            {% endif %}"""

new_profile_banner = """                <span class="badge-pill" style="background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; font-size: 0.8rem; font-weight: 600; padding: 0.2rem 0.65rem;">
                    <i class="fa-solid fa-crosshairs"></i> Target Roles: {{ candidate_profile.search_queries|join(' • ') }}
                </span>
                {% if is_internship_seeking %}
                <span class="badge-pill" style="background: #ecfdf5; color: #065f46; border: 1px solid #6ee7b7; font-size: 0.8rem; font-weight: 700; padding: 0.2rem 0.65rem;">
                    <i class="fa-solid fa-graduation-cap"></i> Internship Seeker Mode Active (Prioritizing Relevant Internships & Entry-Level)
                </span>
                {% endif %}
            </div>
            {% endif %}"""

if old_profile_banner in results_html:
    results_html = results_html.replace(old_profile_banner, new_profile_banner)
else:
    print("Warning: old_profile_banner not found in results.html")

# 2. Add Seniority badges on job cards in results.html
old_card_badges = """                            {% elif job.get('domain_info') and job.get('domain_info', {}).get('is_tech') %}
                            <span class="badge-pill" style="background: #eff6ff; color: #1e40af; border: 1px solid #dbeafe; font-size: 0.72rem; padding: 0.15rem 0.5rem;">
                                <i class="fa-solid fa-tag"></i> {{ job.domain_info.domain_name }}
                            </span>
                            {% endif %}"""

new_card_badges = """                            {% elif job.get('domain_info') and job.get('domain_info', {}).get('is_tech') %}
                            <span class="badge-pill" style="background: #eff6ff; color: #1e40af; border: 1px solid #dbeafe; font-size: 0.72rem; padding: 0.15rem 0.5rem;">
                                <i class="fa-solid fa-tag"></i> {{ job.domain_info.domain_name }}
                            </span>
                            {% endif %}
                            {% if job.get('is_internship') %}
                            <span class="badge-pill" style="background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; font-size: 0.72rem; padding: 0.15rem 0.55rem; font-weight: 700;">
                                <i class="fa-solid fa-graduation-cap"></i> Internship
                            </span>
                            {% elif job.get('is_entry_level') %}
                            <span class="badge-pill" style="background: #fefce8; color: #854d0e; border: 1px solid #fef08a; font-size: 0.72rem; padding: 0.15rem 0.55rem; font-weight: 600;">
                                <i class="fa-solid fa-seedling"></i> Entry Level
                            </span>
                            {% endif %}"""

if old_card_badges in results_html:
    results_html = results_html.replace(old_card_badges, new_card_badges)
else:
    print("Warning: old_card_badges not found in results.html")

with open(results_path, "w", encoding="utf-8") as f:
    f.write(results_html)
print("results.html updated successfully.")


# 3. Update dashboard.html
dashboard_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\templates\dashboard.html"
with open(dashboard_path, "r", encoding="utf-8") as f:
    dash_html = f.read()

old_dash_badges = """                                        <span class="badge-pill" style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 0.68rem; padding: 0.1rem 0.4rem;">
                                            <i class="fa-solid fa-bolt" style="color: #10b981;"></i> {{ job.get('source', 'Live') }}
                                        </span>
                                    </div>"""

new_dash_badges = """                                        <span class="badge-pill" style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 0.68rem; padding: 0.1rem 0.4rem;">
                                            <i class="fa-solid fa-bolt" style="color: #10b981;"></i> {{ job.get('source', 'Live') }}
                                        </span>
                                        {% if job.get('is_internship') %}
                                        <span class="badge-pill" style="background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; font-size: 0.68rem; padding: 0.1rem 0.45rem; font-weight: 700;">
                                            <i class="fa-solid fa-graduation-cap"></i> Internship
                                        </span>
                                        {% elif job.get('is_entry_level') %}
                                        <span class="badge-pill" style="background: #fefce8; color: #854d0e; border: 1px solid #fef08a; font-size: 0.68rem; padding: 0.1rem 0.45rem; font-weight: 600;">
                                            <i class="fa-solid fa-seedling"></i> Entry Level
                                        </span>
                                        {% endif %}
                                    </div>"""

if old_dash_badges in dash_html:
    dash_html = dash_html.replace(old_dash_badges, new_dash_badges)
else:
    print("Warning: old_dash_badges not found in dashboard.html")

with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(dash_html)
print("dashboard.html updated successfully.")


# 4. Update job_detail.html
detail_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\templates\job_detail.html"
with open(detail_path, "r", encoding="utf-8") as f:
    detail_html = f.read()

old_detail_badge = """                    <span class="badge-pill" style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 0.75rem;">
                        <i class="fa-solid fa-bolt" style="color: #10b981;"></i> {{ job.get('source', 'Live Web Opening') }}
                    </span>"""

new_detail_badge = """                    <span class="badge-pill" style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 0.75rem;">
                        <i class="fa-solid fa-bolt" style="color: #10b981;"></i> {{ job.get('source', 'Live Web Opening') }}
                    </span>
                    {% if job.get('is_internship') %}
                    <span class="badge-pill" style="background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.6rem;">
                        <i class="fa-solid fa-graduation-cap"></i> Internship Position
                    </span>
                    {% elif job.get('is_entry_level') %}
                    <span class="badge-pill" style="background: #fefce8; color: #854d0e; border: 1px solid #fef08a; font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.6rem;">
                        <i class="fa-solid fa-seedling"></i> Entry Level Position
                    </span>
                    {% endif %}"""

if old_detail_badge in detail_html:
    detail_html = detail_html.replace(old_detail_badge, new_detail_badge)
else:
    print("Warning: old_detail_badge not found in job_detail.html")

with open(detail_path, "w", encoding="utf-8") as f:
    f.write(detail_html)
print("job_detail.html updated successfully.")


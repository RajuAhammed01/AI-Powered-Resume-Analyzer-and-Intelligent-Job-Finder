import re

# 1. Update results.html
results_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\templates\results.html"
with open(results_path, "r", encoding="utf-8") as f:
    res = f.read()

# Replace links in job list card
res = res.replace(
    """<a href="{{ url_for('jobs.job_detail', index=job.get('cache_id', loop.index0)) }}" style="text-decoration: none; color: inherit;">""",
    """<a href="{{ url_for('jobs.job_detail', index=job.get('job_id', job.get('cache_id', loop.index0))) }}" style="text-decoration: none; color: inherit;">"""
)

res = res.replace(
    """<a href="{{ url_for('jobs.job_detail', index=job.get('cache_id', loop.index0)) }}" class="btn btn-outline btn-sm">""",
    """<a href="{{ url_for('jobs.job_detail', index=job.get('job_id', job.get('cache_id', loop.index0))) }}" class="btn btn-outline btn-sm">"""
)

res = res.replace(
    """<a href="{{ url_for('jobs.apply_redirect', index=job.get('cache_id', loop.index0)) }}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm btn-pill" title="Apply on {{ job.get('source', 'Original Portal') }}">""",
    """<a href="{{ url_for('jobs.apply_redirect', index=job.get('job_id', job.get('cache_id', loop.index0))) }}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm btn-pill" title="Apply on {{ job.get('source', 'Original Portal') }}">"""
)

# Update Save Job hidden input on card
card_save_old = """                    <form method="POST" action="{{ url_for('jobs.save_job') }}" style="display: inline;">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                        <input type="hidden" name="job_title" value="{{ job.get('job_title', '') }}">"""

card_save_new = """                    <form method="POST" action="{{ url_for('jobs.save_job') }}" style="display: inline;">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                        <input type="hidden" name="job_id" value="{{ job.get('job_id', '') }}">
                        <input type="hidden" name="job_title" value="{{ job.get('job_title', '') }}">"""

res = res.replace(card_save_old, card_save_new)

# Replace right sidebar preview apply and detail links
res = res.replace(
    """<a href="{{ url_for('jobs.apply_redirect', index=active_job.get('cache_id', 0)) }}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm" style="flex: 1;">""",
    """<a href="{{ url_for('jobs.apply_redirect', index=active_job.get('job_id', active_job.get('cache_id', 0))) }}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm" style="flex: 1;">"""
)

sidebar_save_old = """            <form method="POST" action="{{ url_for('jobs.save_job') }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <input type="hidden" name="job_title" value="{{ active_job.get('job_title', '') }}">"""

sidebar_save_new = """            <form method="POST" action="{{ url_for('jobs.save_job') }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <input type="hidden" name="job_id" value="{{ active_job.get('job_id', '') }}">
                <input type="hidden" name="job_title" value="{{ active_job.get('job_title', '') }}">"""

res = res.replace(sidebar_save_old, sidebar_save_new)

res = res.replace(
    """<a href="{{ url_for('jobs.job_detail', index=0) }}" class="btn btn-outline btn-sm" style="font-size: 0.78rem; width: 100%;">""",
    """<a href="{{ url_for('jobs.job_detail', index=active_job.get('job_id', active_job.get('cache_id', 0))) }}" class="btn btn-outline btn-sm" style="font-size: 0.78rem; width: 100%;">"""
)

with open(results_path, "w", encoding="utf-8") as f:
    f.write(res)
print("Updated results.html successfully.")


# 2. Update dashboard.html
dash_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\templates\dashboard.html"
with open(dash_path, "r", encoding="utf-8") as f:
    dash = f.read()

old_dash_btn = """                            <a href="{{ url_for('jobs.job_detail', index=job.cache_id) }}" class="btn btn-outline btn-sm">View Details</a>"""

new_dash_btn = """                            <div style="display: flex; gap: 0.5rem; align-items: center;">
                                <a href="{{ url_for('jobs.job_detail', index=job.get('job_id', job.cache_id)) }}" class="btn btn-outline btn-sm">View Details</a>
                                <a href="{{ url_for('jobs.apply_redirect', index=job.get('job_id', job.cache_id)) }}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm btn-pill" title="Apply on {{ job.get('source', 'Original Portal') }}">
                                    Apply Now <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 0.68rem; margin-left: 0.2rem;"></i>
                                </a>
                            </div>"""

dash = dash.replace(old_dash_btn, new_dash_btn)

with open(dash_path, "w", encoding="utf-8") as f:
    f.write(dash)
print("Updated dashboard.html successfully.")


# 3. Update job_detail.html
detail_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\templates\job_detail.html"
with open(detail_path, "r", encoding="utf-8") as f:
    detail = f.read()

detail = detail.replace(
    """<a href="{{ url_for('jobs.apply_redirect', index=index) }}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-pill" id="primaryApplyBtn">""",
    """<a href="{{ url_for('jobs.apply_redirect', index=job.get('job_id', index)) }}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-pill" id="primaryApplyBtn">"""
)

detail_save_old = """                <form method="POST" action="{{ url_for('jobs.save_job') }}">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <input type="hidden" name="job_title" value="{{ job.get('job_title', '') }}">"""

detail_save_new = """                <form method="POST" action="{{ url_for('jobs.save_job') }}">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <input type="hidden" name="job_id" value="{{ job.get('job_id', index) }}">
                    <input type="hidden" name="job_title" value="{{ job.get('job_title', '') }}">"""

detail = detail.replace(detail_save_old, detail_save_new)

# In similar jobs cards
detail = detail.replace(
    """<a href="{{ url_for('jobs.job_detail', index=sim.cache_id) }}" style="color: inherit; text-decoration: none;">""",
    """<a href="{{ url_for('jobs.job_detail', index=sim.get('job_id', sim.get('cache_id', loop.index0))) }}" style="color: inherit; text-decoration: none;">"""
)

# In quick apply modal form
modal_form_old = """        <form method="POST" action="{{ url_for('jobs.apply_job') }}" style="padding: 1.5rem;">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <input type="hidden" name="job_title" value="{{ job.get('job_title', '') }}">"""

modal_form_new = """        <form method="POST" action="{{ url_for('jobs.apply_job') }}" style="padding: 1.5rem;">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <input type="hidden" name="job_id" value="{{ job.get('job_id', index) }}">
            <input type="hidden" name="job_title" value="{{ job.get('job_title', '') }}">"""

detail = detail.replace(modal_form_old, modal_form_new)

with open(detail_path, "w", encoding="utf-8") as f:
    f.write(detail)
print("Updated job_detail.html successfully.")


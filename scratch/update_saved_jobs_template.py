saved_jobs_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\templates\saved_jobs.html"
with open(saved_jobs_path, "r", encoding="utf-8") as f:
    sj = f.read()

old_sj_link = """            <a href="{{ job.apply_link if job.apply_link else '#' }}" target="_blank" class="btn btn-primary btn-sm btn-pill">"""
new_sj_link = """            <a href="{{ url_for('jobs.apply_redirect', index=job.job_id or job.id) }}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm btn-pill">"""

assert old_sj_link in sj
sj = sj.replace(old_sj_link, new_sj_link)

with open(saved_jobs_path, "w", encoding="utf-8") as f:
    f.write(sj)
print("Updated saved_jobs.html successfully.")


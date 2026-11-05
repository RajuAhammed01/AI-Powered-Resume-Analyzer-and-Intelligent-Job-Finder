import os
import re

patterns = [r"job_detail", r"apply_redirect", r"apply_job", r"USER_JOBS_CACHE"]

for root, _, files in os.walk("."):
    if "venv" in root or ".git" in root or ".gemini" in root:
        continue
    for f in files:
        if f.endswith((".py", ".html", ".js")):
            p = os.path.join(root, f)
            with open(p, "r", encoding="utf-8", errors="ignore") as file:
                lines = file.readlines()
            for idx, line in enumerate(lines):
                for pat in patterns:
                    if re.search(pat, line):
                        print(f"{p}:{idx+1}: {line.strip()}")


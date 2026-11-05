scraper_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\services\job_scraper.py"

with open(scraper_path, "r", encoding="utf-8") as f:
    text = f.read()

old_block = '''        r_lower = (role or "").lower()
        tag = ""
        if "react" in r_lower:'''

new_block = '''        r_lower = (role or "").lower()
        tag = ""
        if "intern" in r_lower:
            tag = "internship"
        elif "react" in r_lower:'''

if old_block in text:
    text = text.replace(old_block, new_block)
    with open(scraper_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("job_scraper.py updated with intern tag successfully.")
else:
    print("old_block not found in job_scraper.py")


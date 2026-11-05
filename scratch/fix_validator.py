path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\services\job_validator.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

old_block = """    # If relative path starting with '/', resolve against default domain
    if u.startswith("/"):
        if default_domain:
            clean_domain = default_domain.rstrip("/")
            u = f"{clean_domain}{u}"
        else:
            return ""

    # If lacks scheme but has protocol-relative or www
    if not u.startswith("http://") and not u.startswith("https://"):
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("www."):
            u = "https://" + u"""

new_block = """    # Protocol-relative URLs (e.g. //domain.com/path)
    if u.startswith("//"):
        u = "https:" + u
    # If relative path starting with single '/', resolve against default domain
    elif u.startswith("/"):
        if default_domain:
            clean_domain = default_domain.rstrip("/")
            u = f"{clean_domain}{u}"
        else:
            return ""
    # If lacks scheme but has www.
    elif not u.startswith("http://") and not u.startswith("https://"):
        if u.startswith("www."):
            u = "https://" + u"""

assert old_block in code, "old_block not found in job_validator.py"
code = code.replace(old_block, new_block)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("Updated job_validator.py successfully.")


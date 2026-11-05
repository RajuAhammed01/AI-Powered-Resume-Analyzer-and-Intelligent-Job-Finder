path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\services\skill_gap.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

old_end = """    "rest api": {
        "related": ["FastAPI", "Flask", "GraphQL", "Backend API"],
        "reason": "Candidate has client-server communication and endpoint integration skills.",
    },
}"""

new_end = """    "rest api": {
        "related": ["FastAPI", "Flask", "GraphQL", "Backend API"],
        "reason": "Candidate has client-server communication and endpoint integration skills.",
    },
    "power bi": {
        "related": ["Tableau", "Excel", "Data Visualization", "SQL"],
        "reason": "Candidate has business intelligence dashboard and visualization tool experience with Tableau/Excel.",
    },
    "tableau": {
        "related": ["Power BI", "Excel", "Data Visualization", "SQL"],
        "reason": "Candidate has enterprise dashboard and data visualization experience.",
    },
    "sql": {
        "related": ["PostgreSQL", "MySQL", "SQLite", "Data Analysis"],
        "reason": "Candidate has relational database querying and schema manipulation foundations.",
    },
    "excel": {
        "related": ["Spreadsheets", "Data Analysis", "Tableau", "Power BI"],
        "reason": "Candidate has quantitative reporting and tabular data calculation skills.",
    },
    "nlp": {
        "related": ["Natural Language Processing", "Machine Learning", "Transformers", "Python"],
        "reason": "Candidate has linguistic text modeling and computational language processing foundations.",
    },
    "machine learning": {
        "related": ["Deep Learning", "scikit-learn", "Data Science", "Python", "Artificial Intelligence"],
        "reason": "Candidate has statistical modeling and algorithmic prediction foundations.",
    },
}"""

assert old_end in code, "old_end not found in skill_gap.py"
code = code.replace(old_end, new_end)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("Updated RELATED_SKILL_MAP in skill_gap.py successfully.")


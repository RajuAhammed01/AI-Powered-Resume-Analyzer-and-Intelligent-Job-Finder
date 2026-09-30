# AI Resume Job Finder

A Flask application that extracts skills from resumes and helps users find matching jobs.

## Setup

1. Create and activate a virtual environment:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Configure `.env` in the project root:

   ```dotenv
   FLASK_APP=run.py
   FLASK_DEBUG=1
   SECRET_KEY=replace-with-a-random-secret
   JSEARCH_API_KEY=your-rapidapi-key
   ADZUNA_APP_ID=your-adzuna-app-id
   ADZUNA_APP_KEY=your-adzuna-app-key
   ```

   Keep `.env` local. It is excluded by `.gitignore`.

4. Start the development server:

   ```powershell
   python run.py
   ```

5. Open http://127.0.0.1:5000 in a browser.

## Tests

Install the test runner if needed, then run:

```powershell
pip install pytest
pytest
```

## Security notes

- Passwords are stored as Werkzeug password hashes.
- Resume filenames are sanitized and prefixed with a unique identifier.
- Only PDF and DOCX uploads are accepted.
- Uploads are limited to 5 MB.
- Secrets and local databases are excluded from Git.


## 🔧 Important Setup Notes
1. Copy .env.example to .env and fill in your API keys.
2. Run pip install -r requirements.txt to install all dependencies including sentence-transformers, spacy, and Flask-WTF.
3. The first time you run the application, it will download the Sentence-BERT model (ll-MiniLM-L6-v2, ~80MB) for accurate semantic matching.
4. If you face database schema errors, delete instance/database.db to let the app recreate the latest schema.
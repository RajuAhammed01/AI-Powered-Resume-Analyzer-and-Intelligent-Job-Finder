# 🚀 Deploying JobSnap to Vercel (Production & Actual Developments)

This guide walks you through deploying **JobSnap** to [Vercel](https://vercel.com) using Vercel Serverless Functions and connecting a production cloud database (Neon, Supabase, or Vercel Postgres).

---

## 🏗 Architecture Overview

| Component | Local Development | Vercel Serverless Deployment |
|---|---|---|
| **Entry Point** | `run.py` (`python run.py`) | `api/index.py` (`app = app`) |
| **Routing & Builds** | Handled by Flask | `vercel.json` with `@vercel/python` |
| **Filesystem** | Local directory (`uploads/`, `instance/`) | Read-only with `/tmp` writable scratchpad |
| **Database** | SQLite (`instance/database.db`) | External PostgreSQL (`DATABASE_URL`) or `/tmp/database.db` |
| **Bundle Size** | Full dependencies with local ML models | Optimized production requirements (< 250MB limit) |
| **Auth Dataset** | `data/users_auth_dataset.json` | Hashmap indexed in SQL DB + downloadable JSON dataset |

---

## 📋 Prerequisites

1. A [GitHub](https://github.com) account with this repository pushed.
2. A free [Vercel](https://vercel.com) account.
3. (Recommended for production persistence) A free PostgreSQL database from [Neon](https://neon.tech), [Supabase](https://supabase.com), or [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres).

---

## ⚡ Deployment Methods

### Method 1: Deploy via Vercel Web Dashboard (Recommended)

1. Push your repository to GitHub:
   ```bash
   git add .
   git commit -m "Configure Vercel deployment and authentication dataset"
   git push origin main
   ```

2. Go to [vercel.com/new](https://vercel.com/new).
3. Import your GitHub repository.
4. In the **Configure Project** screen:
   - **Framework Preset**: Other
   - **Root Directory**: `./` (default)
5. Expand **Environment Variables** and add:
   - `SECRET_KEY`: A long random string for securing sessions (e.g. `d9f823a7c64e10b89...`)
   - `DATABASE_URL`: Your cloud PostgreSQL connection string (e.g., from Neon or Supabase: `postgresql://user:password@ep-xyz.neon.tech/neondb?sslmode=require`)
   - `JSEARCH_API_KEY`: *(Optional)* Your RapidAPI JSearch API key for real-time job listings.
6. Click **Deploy**. Vercel will install dependencies and deploy the application in under 60 seconds!

---

### Method 2: Deploy via Vercel CLI

1. Install Vercel CLI (if not already installed):
   ```powershell
   npm install -g vercel
   ```

2. Log in to Vercel:
   ```powershell
   vercel login
   ```

3. Deploy preview:
   ```powershell
   vercel
   ```

4. Deploy to production:
   ```powershell
   vercel --prod
   ```

---

## 🔑 Environment Variables Reference

Configure these in the Vercel Project Settings under **Settings > Environment Variables**:

| Variable Name | Description | Example / Default |
|---|---|---|
| `SECRET_KEY` | Flask session and CSRF signing key | `production-secret-key-32chars` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `UPLOAD_FOLDER` | Upload directory path | Automatically set to `/tmp/uploads` on Vercel |
| `JSEARCH_API_KEY` | RapidAPI live job search key | `your_rapidapi_key` |
| `ADZUNA_APP_ID` | Adzuna Jobs App ID | `your_adzuna_id` |
| `ADZUNA_APP_KEY` | Adzuna Jobs App Key | `your_adzuna_key` |

---

## 🗄 Cloud Database Setup (Neon / Supabase / Vercel Postgres)

Because Vercel serverless functions are stateless and ephemeral:
- Local SQLite files in `./instance` are read-only on Vercel.
- The project automatically falls back to `/tmp/database.db` for ephemeral test runs.
- **For actual production developments where signups and logins must persist across sessions, connect an external PostgreSQL database:**

### Neon (Free Serverless Postgres)
1. Go to [neon.tech](https://neon.tech) and create a free project.
2. Copy the **Connection String** (`postgresql://...`).
3. Add it as `DATABASE_URL` in your Vercel Environment Variables.
4. JobSnap will automatically initialize the database schema on first boot!

### Supabase
1. Create a project at [supabase.com](https://supabase.com).
2. Go to **Settings > Database > Connection URI**.
3. Copy the URI and add it as `DATABASE_URL` in Vercel.
*(Note: If the URI starts with `postgres://`, JobSnap's `config.py` automatically normalizes it to `postgresql://` for SQLAlchemy 2.0).*

---

## 🛡 Authentication & Activity Dataset

JobSnap provides complete tracking and export of authentication data:

1. **Email-Indexed Hashmap**:
   Access an in-memory/JSON hashmap of all registered users keyed by email at `/dataset` or `/export-dataset`.
2. **Password Security**:
   Passwords are never stored in plain text; they are secured using Werkzeug cryptographic salted hashes (`scrypt` / `pbkdf2:sha256`).
3. **Session Audit Trail**:
   Every login (success or failed attempt) is recorded with date, timestamp, client IP, and User-Agent.
4. **Data Export**:
   Download the entire authentication dataset as a clean JSON file at `/export-dataset` or via the **Profile > Quick Actions > Download Dataset** button.


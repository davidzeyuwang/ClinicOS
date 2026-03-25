# ClinicOS — Deploy to Vercel + Supabase (POC)

## 1. Supabase — create database

1. Go to https://supabase.com → New project (free tier)
2. Note your project password
3. Open **SQL Editor** → paste the contents of `supabase/schema.sql` → Run
4. Go to **Project Settings → Database → Connection string → URI**
   - Copy the **Transaction pooler** URL (port **6543**)
   - It looks like: `postgresql://postgres:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`

## 2. Vercel — deploy

1. Go to https://vercel.com → New Project → Import `davidzeyuwang/ClinicOS`
2. **Environment Variables** → add:
   - `DATABASE_URL` = *(the Supabase pooler URL from step 1.4)*
3. Click **Deploy**

Vercel will:
- Serve `frontend/index.html` at `/`
- Run the FastAPI backend as a serverless function at `/prototype/*`

## 3. Verify

- Visit `https://clinicos-xxx.vercel.app/` → Ops Board loads
- Visit `https://clinicos-xxx.vercel.app/health` → `{"status":"ok"}`

## Local development (unchanged)

```bash
cd backend
pip install -r ../requirements.txt
uvicorn app.main:app --reload --port 8000
# Open frontend/index.html in browser or http://localhost:8000/ui/index.html
```

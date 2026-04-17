# Replit + Vercel Deployment Guide (Free)

## Backend on Replit (Free)

### Step 1: Fork the repo to Replit
1. Go to https://replit.com
2. Create an account (free, no card needed)
3. Click `+ New Replit` → import from GitHub
4. Paste: `https://github.com/Naveed101633/-finlens-RAG.git`
5. Replit will auto-detect the Python project

### Step 2: Set environment variables on Replit
1. Click the lock icon (Secrets) in the left sidebar
2. Add these secrets:
   - `GOOGLE_API_KEY`: your Google Gemini API key
   - `QDRANT_HOST`: `localhost`
   - `QDRANT_PORT`: `6333`
   - `QDRANT_COLLECTION_NAME`: `finlens_reports`
   - `EMBEDDING_MODEL`: `sentence-transformers/all-MiniLM-L6-v2`
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `GEMINI_FALLBACK_MODEL`: `gemini-3.1-flash-lite-preview`

### Step 3: Start Qdrant in Replit
In the Replit shell (bottom panel), run:
```bash
docker-compose up -d
```

If Docker is not available in Replit, use the Qdrant in-memory mode. Add to `.env`:
```
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### Step 4: Run the backend
Replit will auto-run using the `.replit` file. The URL will be something like:
```
https://your-replit-slug.replit.dev
```

Copy this URL—it's your `BACKEND_URL`.

## Frontend on Vercel (Free)

### Step 1: Deploy to Vercel
1. Go to https://vercel.com
2. Sign up with GitHub (free, no card)
3. Import the same GitHub repo
4. Set root directory to `frontend/`

### Step 2: Set environment variable
Add `NEXT_PUBLIC_API_URL`:
```
https://your-replit-slug.replit.dev
```

### Step 3: Deploy
Click Deploy. Vercel will auto-build and deploy.

## Test the full stack
1. Open the Vercel frontend URL
2. Upload a PDF
3. Ask a question
4. Verify it retrieves and answers with citations

## Key notes
- Replit free tier has limitations (ephemeral storage, ~1GB RAM)
- For production, the data will be lost on restart unless you add persistent storage
- Vercel frontend is permanent; Replit backend goes to sleep after 30 min inactivity
- If you need persistent Qdrant, consider Qdrant Cloud free tier (separate sign-up)

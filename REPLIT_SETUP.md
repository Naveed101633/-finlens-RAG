# Replit Backend + Vercel Frontend Deployment Guide

## Backend on Replit

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

### Step 3: Point the backend at Qdrant
Use a persistent Qdrant instance such as Qdrant Cloud. Replit is not a good place to rely on local Docker storage for this project.

Set these secrets in Replit:
```
QDRANT_HOST=your-qdrant-host
QDRANT_PORT=6333
QDRANT_API_KEY=your-qdrant-api-key
```

### Step 4: Run the backend
Replit will auto-run using the `.replit` file. The URL will be something like:
```
https://your-replit-slug.replit.dev
```

Copy this URL—it's your `BACKEND_URL`.

## Frontend on Vercel

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
- Replit is a good fit for the API layer, not for long-lived local vector storage
- Vercel is the better fit for the Next.js frontend
- Use Qdrant Cloud or another persistent managed Qdrant instance
- Replit backend may sleep on the free tier, so expect a cold start on first request

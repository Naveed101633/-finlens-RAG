# Deployment Guide

This project is best deployed as two services:

- Frontend: Vercel
- Backend: Replit
- Vector store: Qdrant Cloud or another persistent managed Qdrant instance

This split is the recommended setup for this repo: Vercel handles the Next.js UI, while Replit hosts the FastAPI backend.

## 1. Push the current code to GitHub

From the repository root:

```powershell
git add .
git commit -m "Add production deployment support"
git push origin main
```

If you do not want to commit yet, you can still push later. The important part is that the deployment platform sees the changes in GitHub.

## 2. Deploy the backend on Replit

1. Import the repo into Replit.
2. Set the root to the repository folder that contains `backend/`.
3. Add the backend secrets from `.env.example` in Replit Secrets.
4. Set `QDRANT_HOST` to your managed Qdrant endpoint and `QDRANT_API_KEY` if required.
5. Start the FastAPI app from the Replit run command or workflow.
6. Copy the public Replit URL and use it as the frontend API base URL.

## 3. Deploy the frontend on Vercel

1. Import the same GitHub repo into Vercel.
2. Set the root directory to `frontend`.
3. Add `NEXT_PUBLIC_API_URL` pointing to the backend URL.
4. Deploy.

## 4. Required environment variables

Backend:

- `GOOGLE_API_KEY`
- `QDRANT_HOST`
- `QDRANT_PORT`
- `QDRANT_API_KEY`
- `QDRANT_COLLECTION_NAME`
- `EMBEDDING_MODEL`
- `GEMINI_MODEL`
- `GEMINI_FALLBACK_MODEL`

Frontend:

- `NEXT_PUBLIC_API_URL`

If you deploy the frontend on Vercel, keep the default backend CORS entries and the Vercel regex. If you later move the frontend to another host, add that origin to `CORS_ORIGINS` or update `CORS_ORIGIN_REGEX`.

Example:

```text
CORS_ORIGINS=https://your-project.vercel.app,https://your-custom-domain.com
CORS_ORIGIN_REGEX=https://.*\.(vercel\.app|your-custom-domain\.com)
```

## 5. Production recommendation

Keep `gemini-2.5-flash` as the primary model and use `gemini-3.1-flash-lite-preview` as fallback. That preserves answer quality while reducing downtime from temporary model spikes.

Use Qdrant Cloud or another persistent store. Do not keep the production vector store only in local Docker.
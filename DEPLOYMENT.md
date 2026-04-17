# Deployment Guide

This project is best deployed as two services:

- Frontend: Vercel
- Backend: Cloud Run or Render
- Vector store: Qdrant Cloud or another persistent managed Qdrant instance

## 1. Push the current code to GitHub

From the repository root:

```powershell
git add .
git commit -m "Add production deployment support"
git push origin main
```

If you do not want to commit yet, you can still push later. The important part is that the deployment platform sees the changes in GitHub.

## 2. Deploy the backend

### Option A: Cloud Run

1. Create a new Cloud Run service from the GitHub repo.
2. Set the build source to the `backend/` Dockerfile.
3. Use the environment variables from `.env.example`.
4. Set `GOOGLE_API_KEY` in the Cloud Run secret/env settings.
5. Point `QDRANT_HOST` to your managed Qdrant instance.
6. Deploy and copy the backend URL.

### Option B: Render

1. Create a new Web Service from the GitHub repo.
2. Set the root directory to `backend`.
3. Use the Docker runtime and the `backend/Dockerfile`.
4. Add the same environment variables.
5. Deploy and copy the backend URL.

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
- `QDRANT_COLLECTION_NAME`
- `EMBEDDING_MODEL`
- `GEMINI_MODEL`
- `GEMINI_FALLBACK_MODEL`

Frontend:

- `NEXT_PUBLIC_API_URL`

## 5. Production recommendation

Keep `gemini-2.5-flash` as the primary model and use `gemini-3.1-flash-lite-preview` as fallback. That preserves answer quality while reducing downtime from temporary model spikes.

Use Qdrant Cloud or another persistent store. Do not keep the production vector store only in local Docker.
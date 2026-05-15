# Deployment Guide

## GitHub Secrets Required
Go to: GitHub repo → Settings → Secrets → Actions → New secret

Add these secrets:
  RENDER_DEPLOY_HOOK_URL  → Get from Render dashboard → your service → Deploy Hook

## Render Setup
1. Create account at render.com
2. New → Web Service → Connect GitHub repo
3. Set environment variables from .env.example
4. Database: New → PostgreSQL → copy connection string
5. Copy Deploy Hook URL → paste into GitHub secret

## Deploy Command on Render
  Build: pip install -r requirements.txt && alembic upgrade head
  Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT

## First Deploy Checklist
  - [ ] All environment variables set in Render dashboard
  - [ ] PostgreSQL database created and URL copied
  - [ ] Redis service added (Render Redis or Upstash)
  - [ ] RENDER_DEPLOY_HOOK_URL added to GitHub secrets
  - [ ] Push to main branch → CI runs → deploy triggers automatically

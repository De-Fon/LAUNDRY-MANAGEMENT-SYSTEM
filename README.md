# Laundry Management System

FastAPI backend for a laundry management platform that helps students and
laundry owners communicate and transact.

## Project Structure

```text
app/
  main.py
  core/
  apps/
  shared/
tests/
alembic/
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
GET /health
```

## Database

The default database is SQLite:

```text
sqlite:///./laundry.db
```

Update `DATABASE_URL` in `.env` for another database.

Run migrations with:

```bash
alembic upgrade head
```

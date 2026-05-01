# Lost And Found Backend

FastAPI backend for a Lost and Found Management System with:

- registration and login
- lost/found item posting
- public search and filtering
- private claim verification questions
- claim submission and decision workflow
- admin user moderation
- audit logging
- rate limiting
- PostgreSQL persistence

## Tech Stack

- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- AsyncPG
- Alembic

## Project Structure

```text
app/
  main.py
  modules/
    auth/
    lostfound/
  shared/
scripts/
tests/
alembic/
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Copy the env file:

```powershell
Copy-Item .env.example .env
```

4. Update `.env` if needed.

5. Run database migrations:

```powershell
alembic upgrade head
```

6. Seed default users:

```powershell
python scripts/seed_users.py
```

7. Optional demo data:

```powershell
python scripts/seed_demo_data.py
```

8. Start the API:

```powershell
uvicorn app.main:app --reload
```

Docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Default Accounts

- `admin@example.com / 123456`
- `owner@example.com / 123456`
- `finder@example.com / 123456`

## Main Endpoints

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

### Public Item APIs

- `GET /items`
- `GET /items/{item_id}`

### Item Owner / Claimant APIs

- `POST /items`
- `GET /items/{item_id}/claim-questions`
- `POST /items/{item_id}/claims`
- `GET /items/{item_id}/manage`
- `GET /items/{item_id}/claims`
- `POST /claims/{claim_id}/decision`

### Admin APIs

- `GET /admin/users`
- `PATCH /admin/users/{target_user_id}/status`
- `PATCH /admin/users/{target_user_id}/role`
- `GET /admin/audit-logs`
- `DELETE /admin/items/{item_id}`

## Testing

Run the integration test suite:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The tests use the configured PostgreSQL database and create unique records for each run.

## Migrations

Create a new migration:

```powershell
alembic revision --autogenerate -m "describe change"
```

Apply migrations:

```powershell
alembic upgrade head
```

Rollback one migration:

```powershell
alembic downgrade -1
```

## Docker

Start everything with Docker Compose:

```powershell
docker compose up --build
```

This starts:

- PostgreSQL on `localhost:5432`
- FastAPI on `http://localhost:8000`

## Notes

- For local development, startup schema repair and auto-create can be enabled from `.env`.
- For production or Docker Compose, prefer Alembic migrations and disable startup schema repair.

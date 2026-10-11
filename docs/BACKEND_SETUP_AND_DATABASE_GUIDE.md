# Laundry Management System — Backend Setup & Database Guide

This guide documents how to run the FastAPI backend locally and initialize a **separate Neon PostgreSQL database** using existing Alembic migrations.

> **Safety:** The demo environment must use its **own** Neon database and authentication secret. Never run migrations against any production database unless a production change is explicitly intended and approved.

## 1. Technology stack

- Python **3.12** (recommended for this project's pinned dependencies)
- FastAPI and Uvicorn
- SQLAlchemy async engine with `asyncpg`
- Neon PostgreSQL
- Alembic database migrations
- Local Python virtual environment (`venv`)

## 2. Clone and open the backend

```bash
git clone <YOUR-BACKEND-REPOSITORY-URL>
cd LaundryBackend
```

If you already have a clone, just navigate to the folder containing `app/`, `alembic.ini`, and `requirements.txt`.

## 3. Install Python 3.12 (macOS / Homebrew)

The existing dependency versions (including `asyncpg==0.29.0` and `psycopg2-binary==2.9.9`) failed to build with Python 3.14 in the original setup. Use Python 3.12 for this project.

```bash
brew install python@3.12
python3.12 --version
```

## 4. Create and activate a virtual environment

**First-time setup:**

```bash
python3.12 -m venv venv
source venv/bin/activate
python --version
```

**Every new terminal session:**

```bash
cd LaundryBackend
source venv/bin/activate
```

To leave the environment:

```bash
deactivate
```

> If an old `venv` was created with Python 3.14, deactivate it and recreate it with Python 3.12. `rm -rf venv` removes only that folder, but deletes the installed packages inside it. Do **not** run it from an incorrect directory.

## 5. Install backend dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The known dependency file for this backend contains:

```text
fastapi[all]==0.110.0
uvicorn==0.27.1
sqlalchemy[asyncio]==2.0.27
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic-settings==2.2.1
python-multipart==0.0.9
email-validator==2.1.1
bcrypt==4.0.1
```

Keep `requirements.txt` version-controlled. **Do not** regenerate it with `pip freeze` in an incomplete environment.

## 6. Create a separate Neon demo database

1. Open [Neon Console](https://console.neon.tech/).
2. Create a new project for the laundry product demo (for example `laundry-saas-demo`).
3. Copy the **new demo** database connection details. Prefer a direct connection endpoint when running migrations.
4. Keep the original client's database untouched.

## 7. Configure environment variables

Create `.env` in the repository root (next to `alembic.ini`):

```env
DATABASE_URL=postgresql+asyncpg://USERNAME:PASSWORD@YOUR-DEMO-NEON-HOST/neondb?ssl=require
SECRET_KEY=REPLACE_WITH_AN_INDEPENDENT_RANDOM_SECRET
```

Generate a random secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

The backend's `app/core/config.py` uses Pydantic Settings to read `.env` values. The app's database session uses `create_async_engine(settings.DATABASE_URL, ...)`, so use the **asyncpg** driver prefix.

| URL component | Correct for this backend |
| --- | --- |
| Driver prefix | `postgresql+asyncpg://` |
| TLS query parameter | `?ssl=require` |
| Avoid for asyncpg | `?sslmode=require` |

`sslmode=require` caused `TypeError: connect() got an unexpected keyword argument 'sslmode'` with the asyncpg connection in this setup.

Add these entries to `.gitignore` (if not already present):

```gitignore
.env
.env.*
!.env.example
venv/
.venv/
__pycache__/
*.pyc
```

Never commit actual credentials or production connection strings. If a real database URL was previously committed in `alembic.ini`, remove it from source code and rotate that credential.

## 8. Verify which database the app uses

This prints the target without exposing the password:

```bash
python -c "from app.core.config import settings; from sqlalchemy.engine import make_url; u=make_url(settings.DATABASE_URL); print('Driver:', u.drivername); print('Host:', u.host); print('Database:', u.database); print('SSL:', u.query.get('ssl'))"
```

Expected driver: `postgresql+asyncpg`. **Verify the host is the NEW demo Neon project.**

> **Crucial Alembic check:** `alembic/env.py` decides where migration commands connect. It may read the URL from `alembic.ini`, or it may override it from `app.core.config.settings`. Updating FastAPI's `.env` does **not** by itself prove that Alembic uses the same database. Inspect `alembic/env.py` and verify the effective migration target before running `upgrade`.

## 9. Start FastAPI locally

```bash
python -m uvicorn app.main:app --reload --reload-dir app
```

- API root: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Swagger docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- OpenAPI JSON (per `API_V1_STR`): `http://127.0.0.1:8000/api/v1/openapi.json`

`--reload-dir app` avoids unnecessary reloads when site-packages inside `venv/` change.

The root endpoint returning successfully only proves that the app is up; test a database-backed endpoint separately to verify connectivity.

Stop the server with **Ctrl+C**.

## 10. Alembic: recreate schema in the new Neon database

**Before any migration:** verify `alembic/env.py` connects to the **demo** Neon database, not Al Nejoum production. Running an Alembic command on the wrong database can alter its schema.

### Inspect existing migrations (does not apply changes)

```bash
python -m alembic history
python -m alembic heads
```

Current migration chain in this repository:

| Revision | Purpose |
| --- | --- |
| `bcf72847d6c9` | `init_pure_matrix_architecture` |
| `f02deece3554` | `add_hanger_needed_flag` |
| `5ab09e11bf2e` | `add discount_type to offers` |
| `6b49578da67e` | `added_discount_fields` |
| `5dd892621cab` | `change order_items quantity to float` — **head** |

### Check the current database revision

```bash
python -m alembic current
```

A new blank database may show only the PostgreSQL context log lines, with **no revision ID**.

### Apply migrations to the confirmed demo database

```bash
python -m alembic upgrade head
```

This applies each unapplied migration in sequence to create/update the schema.

### Confirm success

```bash
python -m alembic current
```

Verified output after the successful demo setup:

```text
5dd892621cab (head)
```

In the Neon Console, select the demo project and inspect the `public` schema's tables. Alembic also maintains an `alembic_version` table.

### After future changes to SQLAlchemy models

Only after verifying the correct database and reviewing your model changes:

```bash
python -m alembic revision --autogenerate -m "describe schema change"
```

**Review the generated migration file** under `alembic/versions/` before applying it:

```bash
python -m alembic upgrade head
```

Never generate or apply migrations blindly. Do **not** use `alembic stamp head` to create tables: stamping only records the revision, without executing migrations.

## 11. Tables vs. sample demo data

Alembic creates the **schema**: tables, columns, relationships, constraints, and indexes described by the revisions. It does **not** normally add customer accounts, services, prices, or example orders.

For a product demo, prepare a separate **seed script** to insert sanitized and fictional data such as:

- Demo admin and staff accounts
- Example customers and buildings
- Laundry items and services
- Sample orders in different statuses
- Example offers and expenses

Do not copy actual customer personal information from the original client's production database into the demo.

## 12. Troubleshooting

| Error / symptom | Cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'fastapi'` | Dependencies were not installed in the active venv | Activate `venv`, run `python -m pip install -r requirements.txt` |
| `No module named 'pydantic_settings'` | Missing dependency | Install from `requirements.txt` or `python -m pip install pydantic-settings` |
| Failed building wheels for `asyncpg` / `psycopg2-binary` | Project's pinned versions failed under Python 3.14 | Recreate venv with Python 3.12 and reinstall requirements |
| `InvalidRequestError: The loaded 'psycopg2' is not async` | Async SQLAlchemy engine was given a sync PostgreSQL driver URL | Use `postgresql+asyncpg://` in the app's `DATABASE_URL` |
| `TypeError: connect() got an unexpected keyword argument 'sslmode'` | `asyncpg` does not accept that URL argument | Use `?ssl=require` instead |
| `alembic current` shows no revision | Database may be new/unmigrated | Verify migration target and run `alembic upgrade head` |
| Continuous Uvicorn reloading from `venv/...` | Reloader watching dependency files | Run with `--reload-dir app` |

## 13. Everyday quick reference

```bash
# In the LaundryBackend repo
source venv/bin/activate

# Start the API
python -m uvicorn app.main:app --reload --reload-dir app

# Inspect migrations
python -m alembic history
python -m alembic heads
python -m alembic current

# Apply existing migrations (ONLY after verifying target database)
python -m alembic upgrade head

# Stop the server: Ctrl+C
# Leave the environment:
deactivate
```

---

**Setup status:** All five existing migrations were successfully applied to the configured database, and `alembic current` returned `5dd892621cab (head)`. Verify the environment/database target independently when sharing this guide with another developer.

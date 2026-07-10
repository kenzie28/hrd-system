# HRD System — Deployment

Single Docker image: Django API + HR admin UI + employee portal, deployed to Google Cloud Run.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk) (`gcloud auth login`)
- [Docker](https://docs.docker.com/get-docker/) (for local builds)
- A GCP project with billing enabled

## First-time setup

1. Edit `PROJECT_ID` in `one-time-gcloud-setup.sh` and `deploy.sh` (replace `TODO_insert_YOUR_project_ID`).
2. Run one-time GCP setup:

```bash
./one-time-gcloud-setup.sh
```

3. Copy and edit environment file:

```bash
cp .env.example .env
# Set DJANGO_SECRET_KEY and other values
```

4. First deploy:

```bash
./deploy.sh --build --env
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DJANGO_SECRET_KEY` | yes | Random secret string |
| `DJANGO_DEBUG` | no | `false` in production |
| `DJANGO_ALLOWED_HOSTS` | yes | `*` or your Cloud Run hostname |
| `DJANGO_SUPERUSER_USERNAME` | no | Auto-create Django admin on first boot |
| `DJANGO_SUPERUSER_PASSWORD` | no | Password for superuser above |
| `DJANGO_SUPERUSER_EMAIL` | no | Email for superuser (default `admin@example.com`) |
| `PAYROLL_DB_*` | no | Payroll import only (see `.env.example`) |

Loaded via `./deploy.sh --env` from `.env`.

## Production URLs

After deploy, `{SERVICE_URL}` is printed by `deploy.sh`:

| URL | App |
|-----|-----|
| `{SERVICE_URL}/portal/` | Employee portal |
| `{SERVICE_URL}/hr/` | HR admin UI |
| `{SERVICE_URL}/api/` | REST API |
| `{SERVICE_URL}/django-admin/` | Django admin (data management) |

## Deploy commands

| Command | Effect |
|---------|--------|
| `./deploy.sh` | Redeploy existing `latest` image |
| `./deploy.sh --build` | Rebuild and push image, then deploy |
| `./deploy.sh --env` | Deploy with updated `.env` variables |
| `./deploy.sh --build --env` | Full deploy (first time or after code changes) |

## Post-deploy

Run management commands via Cloud Run exec or a one-off job:

```bash
# Create portal logins for employees (default password: 123)
gcloud run jobs execute ...  # or docker exec locally

# Optional demo data
python manage.py seed_demo
```

Locally with Docker:

```bash
docker build -t hrd-system .
docker run -p 8080:8080 --env-file .env hrd-system
# Portal: http://localhost:8080/portal/
# HR Admin: http://localhost:8080/hr/
```

## API endpoints

Base path: `/api/`

| Endpoint | Methods | Notes |
|----------|---------|-------|
| `/api/shifts/` | CRUD | Work shifts |
| `/api/jadwal/` | CRUD | Schedules; `?karyawan=&bulan=YYYY-MM` |
| `/api/jadwal/bulk/` | POST | Bulk schedule creation |
| `/api/absensi/` | CRUD | Attendance records |
| `/api/cuti/` | GET | Daily leave ledger (read-only) |
| `/api/rekap/` | GET | Attendance recap |
| `/api/rekap/process/` | POST | Process recap for date range |
| `/api/karyawan/`, `/api/lokasi/`, `/api/liburan/` | GET | Reference data |
| `/api/portal/login/` | POST | Employee login `{karyawan_id, password}` |
| `/api/portal/me/` | GET | Current employee (token auth) |
| `/api/portal/change-password/` | POST | Change password |
| `/api/portal/gaji/` | GET | Salary breakdown `?bulan=YYYY-MM` |
| `/api/portal/cuti/` | CRUD | Employee leave requests |
| `/api/admin/login/` | POST | HR admin login |
| `/api/admin/me/` | GET | Current admin user |
| `/api/admin/cuti/` | GET/PATCH | Leave approval workflow |

Token auth: `Authorization: Token <token>` header.

## Database note

Production uses **SQLite inside the container**. Data is **lost on image rebuild or redeploy** unless you add persistent storage (Cloud Run volume) or migrate to Cloud SQL later.

## Architecture

```
Browser → nginx :8080
            ├── /api/, /django-admin/, /static/ → gunicorn :8000 (Django)
            ├── /hr/     → admin-frontend static
            └── /portal/ → portal-frontend static
```

Frontends are built with `VITE_API_URL=/api` (same-origin). Local dev is unchanged — see [README.md](README.md).

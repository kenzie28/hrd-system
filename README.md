# HRD System — Attendance Module

HR attendance management with a Django REST API backend and a React (Vite + TypeScript + Ant Design) frontend.

## Features

- **Shift** — full CRUD for work shifts (jam masuk/keluar)
- **Jadwal** — bulk schedule creation for one or many employees over a date range; table/calendar views; edit shift and delete per entry
- **Absensi** — attendance records created via API (`POST /api/absensi/`); frontend supports view, edit (lokasi, jam masuk, durasi with computed jam keluar), and delete
- **Cuti** — leave is split into `PermohonanCuti` (the request: tipe, date range, approval status, supervisor) and `Cuti` (factual daily ledger: one row per leave day, FK to its permohonan). The UI and API expose the daily `Cuti` ledger read-only (no POST endpoint); table/calendar views. The request/approval workflow on `PermohonanCuti` is not implemented yet.
- **Rekap Kehadiran** — attendance recap computed from Jadwal + Absensi + Cuti + Liburan; processable/reprocessable per date range from the UI or a management command; table/calendar views

## Project layout

```
backend/          Django + DRF API (SQLite)
admin-frontend/   Vite + React + TypeScript + Ant Design (HR admin UI)
portal-frontend/  Vite + React + TypeScript + Ant Design (employee self-service portal)
```

## Production deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Docker + Google Cloud Run setup.

## Backend setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo          # optional demo data
.venv/bin/python manage.py runserver          # http://localhost:8000
```

API root: `http://localhost:8000/api/`

### Rekap processing

Rekap rows are built per Jadwal entry in the range (idempotent — reprocessing replaces existing rows):

1. Date is a `Liburan` → **Libur**
2. A daily `Cuti` ledger row exists for the date → **Sakit** / **Izin** / **Cuti** (by the permohonan's tipe)
3. `Absensi` exists → **Terlambat** (late in), **Pulang Cepat** (early out), else **Hadir**
4. Otherwise → **Alpa**

Via management command:

```bash
.venv/bin/python manage.py process_rekap --start 2026-07-01 --end 2026-07-31
```

Or via API / the "Proses Rekap" button in the UI:

```
POST /api/rekap/process/  {"tanggal_mulai": "2026-07-01", "tanggal_selesai": "2026-07-31"}
```

### Key endpoints

| Endpoint | Methods | Notes |
|---|---|---|
| `/api/shifts/` | full CRUD | |
| `/api/jadwal/` | full CRUD | `?karyawan=<id>&bulan=YYYY-MM` filters |
| `/api/jadwal/bulk/` | POST | `{karyawan_ids, shift_id, tanggal_mulai, tanggal_selesai}`; skips existing |
| `/api/absensi/` | full CRUD | `jam_keluar` is computed (jam_masuk + durasi) |
| `/api/cuti/` | GET only | no create/update via API |
| `/api/rekap/` | GET only | plus `POST /api/rekap/process/` |
| `/api/karyawan/`, `/api/lokasi/`, `/api/liburan/` | GET only | reference data |

Karyawan, Lokasi, Liburan, PermohonanCuti, and Cuti records are managed through the Django admin at `/django-admin/` (create a superuser with `manage.py createsuperuser`).

### Employee portal login

Each `Karyawan` has a unique 7-digit `karyawan_id` used as the portal login, a linked Django `User` (which holds the hashed password), and a `must_change_password` flag. The default password is `123`, and employees are forced to change it on first login.

Create/reset portal logins with the management command:

```bash
.venv/bin/python manage.py create_portal_logins        # only Karyawan without a login
.venv/bin/python manage.py create_portal_logins --all  # reset every Karyawan's login/password
```

New `Karyawan` created afterwards get a portal login automatically (via a `post_save` signal).

Portal API endpoints (token auth):

| Endpoint | Methods | Notes |
|---|---|---|
| `/api/portal/login/` | POST | `{karyawan_id, password}` -> `{token, must_change_password, karyawan}` |
| `/api/portal/me/` | GET | current employee (requires `Authorization: Token <token>`) |
| `/api/portal/change-password/` | POST | `{new_password}`; clears `must_change_password`, rotates token |
| `/api/portal/gaji/` | GET | `?bulan=YYYY-MM`; salary breakdown (empty placeholder for now) |

## Frontend setup

Both frontends default the API base URL to `http://localhost:8000/api`; override with a `VITE_API_URL` env var if needed.

### Admin frontend

```bash
cd admin-frontend
npm install
npm run dev                                   # http://localhost:5173
```

The UI is a single page with tabs (Shift, Jadwal, Absensi, Cuti, Rekap Kehadiran). Jadwal, Cuti, and Rekap share a reusable view toggle: **Table** and **Calendar**.

### Employee portal frontend

```bash
cd portal-frontend
npm install
npm run dev                                   # http://localhost:5174
```

Employees log in with their `karyawan_id` + password (default `123`), are prompted to set a new password on first login, then reach a home page with module cards. Currently **Gaji** (pick a month to view the salary breakdown — empty for now) and **Cuti** (placeholder).

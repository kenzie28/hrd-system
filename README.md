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
backend/    Django + DRF API (SQLite)
frontend/   Vite + React + TypeScript + Ant Design
```

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

Karyawan, Lokasi, Liburan, PermohonanCuti, and Cuti records are managed through the Django admin (`/admin/`, create a superuser with `manage.py createsuperuser`).

## Frontend setup

```bash
cd frontend
npm install
npm run dev                                   # http://localhost:5173
```

The API base URL defaults to `http://localhost:8000/api`; override with a `VITE_API_URL` env var if needed.

The UI is a single page with tabs (Shift, Jadwal, Absensi, Cuti, Rekap Kehadiran). Jadwal, Cuti, and Rekap share a reusable view toggle: **Table** and **Calendar**.

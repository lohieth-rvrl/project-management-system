# Project Management System

Organisation-wide project monitoring: projects, tasks, sprints, time tracking, risks,
workload, analytics dashboards and a full audit trail. Built entirely with open-source tools.

## Stack
- **Backend:** Python, Django 5, Django REST Framework, SimpleJWT, drf-spectacular (Swagger),
  django-simple-history (audit), Celery + Redis (background jobs)
- **Frontend:** React 18 (JavaScript), Vite, TanStack Query, React Router, Apache ECharts
- **Database:** PostgreSQL 16 (SQLite fallback for local dev and tests)
- **Infra:** Docker Compose, Nginx, MinIO, Metabase, GitHub Actions CI

## Quick start (Docker)
```bash
cp .env.example .env
docker compose up --build
docker compose exec backend python manage.py seed_demo      # optional demo data
docker compose exec backend python manage.py createsuperuser # or use demo users
```
| Service | URL |
|---|---|
| App (via Nginx) | http://localhost:8080 |
| API docs (Swagger) | http://localhost:8080/api/docs/ |
| Django admin | http://localhost:8080/admin/ |
| Metabase (BI) | http://localhost:3001 |
| MinIO console | http://localhost:9001 |

Demo logins after `seed_demo` (password `demo12345`): `admin`, `meera` (manager), `arun` (lead),
`priya` / `karthik` (members), `divya` (viewer).

## Deploy to Render
See [DEPLOY_RENDER.md](DEPLOY_RENDER.md). The `render.yaml` Blueprint creates the database, API and frontend.

## Run without Docker
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate && python manage.py seed_demo
python manage.py runserver            # http://localhost:8000

cd frontend
npm install && npm run dev            # http://localhost:5173 (proxies /api to :8000)
```

## Tests
```bash
cd backend && python -m pytest -q     # 43 API tests
cd frontend && npm run build
```

## Roles
| Role | Read | Create / edit | Delete | Approve time | Manage users |
|---|---|---|---|---|---|
| Admin, Manager | yes | yes | yes | yes | yes |
| Team Lead | yes | yes | no | yes | no |
| Member | yes | yes | no | no | no |
| Viewer | yes | no | no | no | no |

Members and viewers see only their own time entries; leads and above see everyone's.

## Main API endpoints (`/api/`)
`auth/token/`, `auth/refresh/`, `users/`, `projects/`, `project-members/`, `milestones/`,
`tasks/`, `sprints/`, `task-dependencies/`, `comments/`, `time-entries/` (+ `/approve/`), `risks/`

Analytics (`/api/analytics/`): `overview/`, `projects/<id>/summary/`, `workload/`,
`velocity/`, `overdue/`, `audit/`

## Not built yet
These items from the original plan are not in this version:
- File attachments (MinIO container is provisioned, but no upload endpoint yet)
- Real-time WebSocket notifications and email/Slack notifications
- Configurable workflow engine and Gantt view
- PDF/Excel report export
- Prometheus, Grafana and Sentry wiring
- Elasticsearch-style search (DRF `?search=` covers basic text search)
- Production hardening: HTTPS, backups, secrets management, load tests
- Frontend uses plain CSS and native drag-and-drop rather than Tailwind and dnd-kit

Metabase can already be pointed at the Postgres database for self-service BI. Use a read-only
database user for that connection.

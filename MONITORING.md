# Monitoring

Everything here is optional and off until you configure it.

## 1. Errors: Sentry (free plan available at sentry.io)
1. Create a project on sentry.io (platform: Django) and copy its **DSN**.
2. Backend (Render, `pms-backend`): set `SENTRY_DSN`. Optional: `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE` (0 to 1, default 0).
3. Browser errors: create a second Sentry project (platform: React), set its DSN as `VITE_SENTRY_DSN` on the static site, then redeploy it (Vite bakes it in at build time).
No personal data is sent (`send_default_pii` is off).

## 2. Numbers: Prometheus endpoint
Set `METRICS_TOKEN` on the backend to any long random string. Then `GET /api/metrics/` with the header
`Authorization: Bearer <token>` returns request counts and timings per route plus live counts of tasks by status,
overdue tasks, projects by status, open risks and active users. Without the variable the endpoint returns 404.

## 3. Dashboards: Prometheus + Grafana + Metabase (Docker, run on your own machine or server)
```
cp monitoring/metrics_token.example monitoring/metrics_token   # put your METRICS_TOKEN in it
# edit the target host in monitoring/prometheus.yml
docker compose -f docker-compose.monitoring.yml up -d
```
- Grafana http://localhost:3001 (admin / `GRAFANA_PASSWORD`, default admin): the "Project Management overview" dashboard is preloaded.
- Prometheus http://localhost:9090
- Metabase http://localhost:3002: connect it to the database with the read-only login below.
These containers are not part of the Render deployment (Render's free plan cannot run them), and they have not been run in the build environment; the YAML and JSON were syntax-checked only.

## 4. Read-only database login
`monitoring/readonly_user.sql` creates `pms_readonly`: it can read the `pms` schema, cannot write, and cannot read password hashes.
Tested against a local PostgreSQL 16. Use your own password and database name.

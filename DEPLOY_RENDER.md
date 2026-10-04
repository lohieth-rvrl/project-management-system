# Deploying to Render

The repo includes a Render Blueprint (`render.yaml`) that creates three things:

| Render resource | What it is |
|---|---|
| `pms-db` | PostgreSQL database |
| `pms-backend` | Django REST API (gunicorn), runs migrations on every start |
| `pms-frontend` | React app as a static site |

Redis, the Celery worker, MinIO and Metabase are **not** deployed on Render. Nothing in the app needs them yet (no background tasks or file uploads are built).

## Steps

### 1. Create the Blueprint
1. Sign in at https://render.com with GitHub and allow access to `lohieth-rvrl/project-management-system`.
2. Click **New** then **Blueprint**, pick the repo and the `main` branch.
3. Render reads `render.yaml` and asks for the values marked "sync: false". Enter these for now:
   - `DJANGO_SUPERUSER_PASSWORD`: a strong password (this is your admin login)
   - `DJANGO_SUPERUSER_EMAIL`: your email
   - `CORS_ALLOWED_ORIGINS`: `https://placeholder.onrender.com` (you will fix this in step 3)
   - `VITE_API_URL`: `https://placeholder.onrender.com/api` (you will fix this in step 2)
4. Click **Apply** and wait for `pms-db` and `pms-backend` to finish. The first backend build takes a few minutes.

### 2. Point the frontend at the backend
1. Open `pms-backend` in the dashboard and copy its URL (for example `https://pms-backend.onrender.com`). Render adds a suffix if the name is already taken, so copy the real one.
2. Open `pms-frontend` → **Environment** and set `VITE_API_URL` to `<backend URL>/api`, for example `https://pms-backend.onrender.com/api`.
3. Click **Manual Deploy** → **Clear build cache & deploy**. The value is baked in at build time, so a redeploy is required.

### 3. Allow the frontend to call the backend
1. Copy the `pms-frontend` URL (for example `https://pms-frontend.onrender.com`).
2. Open `pms-backend` → **Environment** and set `CORS_ALLOWED_ORIGINS` to that URL. No trailing slash and no path.
3. Save. The backend restarts by itself.

### 4. Check it works
- `<backend URL>/api/health/` should return `{"status": "ok", "database": "up"}`
- `<backend URL>/api/docs/` shows the Swagger API docs
- Open the frontend URL and sign in as `admin` with the password you set

### 5. Add your team
There is no user management screen yet. Create users at `<backend URL>/admin/` (sign in with the same admin login). Set each person's **Role** under the PMS section.

## Sharing a database with another app
Render allows one free database per workspace. To reuse an existing one, set these on `pms-backend`:
- `DATABASE_URL`: the database's **Internal Database URL** (Render dashboard → the database → Connections)
- `DB_SCHEMA`: `pms`

The app then keeps all its tables in its own `pms` schema and never touches the other app's tables. Both apps still share one database's lifetime and storage, so if a free database expires, both lose their data.

The frontend uses hash URLs (`https://.../#/projects`) so the static site needs no rewrite rule.

## Things to know about the free plan
Check Render's current pricing and limits, because they change.
- **Sleeping:** free web services stop after a period of no traffic. The next request can take a minute to wake the API.
- **Free database:** Render has limited free Postgres to a short lifetime, after which it is deleted unless upgraded. Do not keep irreplaceable data there. Move to a paid database before real use.
- **No demo data:** the database starts empty. The `seed_demo` command needs a shell, which the free plan does not give, and demo accounts with known passwords should not be on a public site anyway.
- **No shell or Redis:** background jobs, file attachments and Metabase need a paid setup or your own server (see `docker-compose.yml`).

## Updating
Push to `main` and Render redeploys the changed services. Migrations run automatically when the backend starts.

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| Login says the request failed | `VITE_API_URL` is wrong or the frontend was not redeployed after changing it |
| Browser console shows a CORS error | `CORS_ALLOWED_ORIGINS` does not exactly match the frontend URL |
| Backend returns 400 "Bad Request" | The hostname is not in `DJANGO_ALLOWED_HOSTS` (default `.onrender.com` covers Render URLs) |
| Backend fails to start with "Set DJANGO_SECRET_KEY" | The secret was not generated; add `DJANGO_SECRET_KEY` manually |
| Page refresh shows "Not Found" | The `/* → /index.html` rewrite is missing from the frontend routes |

# Environment variables (Render)

Where to set them: Render dashboard, then the service, then **Environment**. Saving triggers a redeploy.
`pms-backend` = the Django API. `pms-frontend` = the static website (its variables are baked in at build time, so it is rebuilt automatically when you change one).

Legend: **SET** = already set, **FILL** = placeholder exists, you add the value, **OPTIONAL** = leave unset unless you want the feature.

## pms-backend: already set (do not change unless you know why)
| Variable | Value / meaning |
|---|---|
| `PYTHON_VERSION` | `3.12.7` |
| `DJANGO_DEBUG` | `0` (production mode) |
| `DJANGO_SECRET_KEY` | long random string. Never share it. Changing it logs everyone out. |
| `DJANGO_ALLOWED_HOSTS` | `.onrender.com` |
| `DATABASE_URL` | connection string of the shared BookLifeDB database (set by you) |
| `DB_SCHEMA` | `pms` (keeps this app's tables apart from BookLifeDB's) |
| `CORS_ALLOWED_ORIGINS` | `https://pms-frontend-c1j5.onrender.com` (the website address) |
| `DJANGO_SUPERUSER_USERNAME` | `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | the first admin password. It is only used the first time; change it in the app (My Account) and it stays changed. |
| `FRONTEND_URL` | `https://pms-frontend-c1j5.onrender.com` (used for links in emails) |
| `MAX_UPLOAD_MB` | `10` (largest attachment) |

## pms-backend: email (FILL to get real emails; until then they are only written to the Render logs)
| Variable | What to put | Where to get it |
|---|---|---|
| `EMAIL_HOST` | e.g. `smtp.gmail.com` or `smtp-relay.brevo.com` | your email provider's SMTP page |
| `EMAIL_PORT` | `587` (already set) | usually unchanged |
| `EMAIL_USE_TLS` | `1` (already set) | usually unchanged |
| `EMAIL_HOST_USER` | SMTP login (Gmail: your address) | email provider |
| `EMAIL_HOST_PASSWORD` | SMTP password. Gmail needs an **app password** (Google account, Security, 2-step verification, App passwords) | email provider |
| `DEFAULT_FROM_EMAIL` | sender address, e.g. `pms@yourdomain.com` (Gmail: your own address). **Must be filled when EMAIL_HOST is set.** | you choose |

## pms-backend: file attachments (FILL, otherwise uploaded files vanish at every deploy)
Create a free bucket on Cloudflare R2, Backblaze B2 or AWS S3.
| Variable | What to put |
|---|---|
| `S3_BUCKET` | bucket name |
| `S3_ACCESS_KEY_ID` | access key id from the provider |
| `S3_SECRET_ACCESS_KEY` | secret key from the provider |
| `S3_ENDPOINT_URL` | R2: `https://<account-id>.r2.cloudflarestorage.com`. B2: `https://s3.<region>.backblazeb2.com`. AWS: leave empty. |
| `S3_REGION` | AWS: e.g. `ap-south-1`. R2: `auto`. B2: e.g. `us-west-004`. |

## pms-backend: alerts and monitoring (all OPTIONAL)
| Variable | What to put |
|---|---|
| `NOTIFY_WEBHOOK_URL` | Slack or Microsoft Teams incoming-webhook URL. Blocked tasks and critical risks get posted there. |
| `SENTRY_DSN` | DSN of a free sentry.io project (platform Django). Turns on error tracking. |
| `SENTRY_ENVIRONMENT` | label shown in Sentry, default `production` |
| `SENTRY_TRACES_SAMPLE_RATE` | `0` (default) to `1`; performance sampling |
| `METRICS_TOKEN` | any long random string. Turns on `/api/metrics/` for Prometheus (send it as `Authorization: Bearer <token>`). |

## pms-backend: example project (OPTIONAL)
| Variable | Meaning |
|---|---|
| `SEED_SHOWCASE` | `1` creates the example project **SHOW** and its five team members once (safe on every deploy). Remove it or set `0` afterwards if you like; the data stays. |
| `SHOWCASE_PASSWORDS` | `anita:PASS1,rahul:PASS2,sneha:PASS3,vikram:PASS4,meena:PASS5` (the passwords the team members log in with; only used when the account is first created) |

## pms-backend: rarely needed
| Variable | Meaning |
|---|---|
| `DJANGO_SUPERUSER_EMAIL` | admin's email address |
| `DJANGO_SUPERUSER_FORCE_PASSWORD` | `1` for one deploy resets the admin password to `DJANGO_SUPERUSER_PASSWORD` (use if you are locked out; remove afterwards) |
| `REDIS_URL` | only if you add Redis later (not used on Render today) |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` | alternative to `DATABASE_URL` (Docker setup) |
| `SQLITE_PATH`, `MEDIA_ROOT`, `NOTIFY_SYNC`, `PROMETHEUS_MULTIPROC_DIR` | local development and tests only |

## pms-frontend (static website)
| Variable | What to put |
|---|---|
| `VITE_API_URL` | **SET**: `https://pms-backend-dbgf.onrender.com/api` |
| `NODE_VERSION` | **SET** |
| `VITE_SENTRY_DSN` | OPTIONAL: DSN of a second Sentry project (platform React) for browser errors |

## Things to do outside Render
- Change the admin password in the app (My Account).
- The free BookLifeDB database expires on **2026-10-24**; both apps lose their data then unless you move to a paid or new database.

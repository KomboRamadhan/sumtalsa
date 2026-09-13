# SumTalsa — Render Deployment

The Render Blueprint now provisions both:
1. SumTalsa FastAPI web service
2. Render PostgreSQL database

## Required initial secrets
During initial Blueprint creation, enter:
- BOOTSTRAP_SUPERADMIN_EMAIL — your administrator email
- BOOTSTRAP_SUPERADMIN_PASSWORD — a strong private password
- OPENAI_API_KEY — optional; leave blank if staying in mock AI mode
- OPENAI_MODEL — optional

SECRET_KEY is generated automatically by Render.

## HTTPS
Render provides HTTPS for its public web service URL. SumTalsa also has FORCE_HTTPS enabled.

## Database
DATABASE_URL is populated automatically from the Render PostgreSQL `connectionString`.

## After deployment
1. Open `/api/health` and confirm `{"ok": true}`.
2. Sign in using the bootstrap super-admin credentials.
3. Create/administer schools and curriculum versions.
4. Import and verify individual curriculum subject nodes before marking them verified.
5. Configure live AI only after setting review/usage controls.

## Custom domain
Once a domain is available, add it to the Render web service. Keep HTTPS enabled.

# SumTalsa Production-Ready Pilot

This is the final consolidated SumTalsa full-stack package.

## What is now real
- backend API
- account registration/login
- JWT authentication
- role permissions
- database persistence
- saved resources
- intervention records
- feedback records
- curriculum version records
- school/admin metrics
- AI provider abstraction
- static public website + authenticated app
- Docker deployment files

## Roles
Teacher, Student, Parent, School Admin, Super Admin.

## Quick local start
```bash
python -m venv .venv
# activate the virtual environment
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```
Open http://localhost:8000

## Demo seeded accounts
Run `python seed.py` first.

- teacher@sumtalsa.local / Teacher123!
- student@sumtalsa.local / Student123!
- parent@sumtalsa.local / Parent123!
- admin@sumtalsa.local / Admin123!
- super@sumtalsa.local / Super123!

Change/remove demo accounts before public production.

## Docker
```bash
docker compose up --build
```

## Live AI
Default is `AI_PROVIDER=mock`.

For a live provider, set environment variables:
- `AI_PROVIDER=openai`
- `OPENAI_API_KEY=...`
- `OPENAI_MODEL=...`

The application falls back to safe demo generation if the live provider is unavailable.

## Database
SQLite works for testing. For real multi-user deployment, set `DATABASE_URL` to PostgreSQL.

## Curriculum warning
The included curriculum examples are illustrative only.
Before production, import verified, version-controlled authoritative TIE curriculum data and preserve source references.

## Before public production
1. Use PostgreSQL.
2. Use a strong `SECRET_KEY`.
3. Remove demo accounts.
4. Serve only over HTTPS.
5. Import and review authoritative curriculum sources.
6. Review privacy/consent requirements for learner data.
7. Add backups and monitoring.
8. Configure a live AI provider if desired.
9. Test parent/student relationship permissions before storing real learner data.
10. Conduct the 3–5 school / 20–30 teacher pilot.

## Suggested hosting
The project can run on any Python/Docker web host. `render.yaml`, `Procfile`, `Dockerfile` and `docker-compose.yml` are included for convenience.

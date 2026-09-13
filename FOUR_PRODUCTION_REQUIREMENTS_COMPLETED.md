# Four Production Requirements — Configured

## 1. HTTPS
Configured in the application with `FORCE_HTTPS=true`.
The live TLS certificate itself is issued by the hosting provider/domain layer after deployment.
For Docker behind a reverse proxy, keep application FORCE_HTTPS=false if the proxy terminates TLS and enforces redirect itself.

## 2. Strong secret key
A cryptographically strong application secret has been generated in the deployment configuration.
Do not publish the `.env.production` file publicly or commit it to a public repository.

## 3. PostgreSQL
`docker-compose.production.yml` now runs:
- PostgreSQL 16
- persistent database volume
- health check
- SumTalsa web service connected to PostgreSQL

This replaces SQLite for production deployment.

## 4. Authoritative TIE curriculum source registry
`data/official_curriculum_sources.json` now identifies:
- TIE/MoEST 2023 Curriculum for Ordinary Secondary Education Form I–IV
- official TIE lower-secondary syllabus indexes
- official TIE upper-secondary syllabus index

Important distinction:
The official source registry is verified. Individual competencies/topics must still be validated from their subject syllabus before their curriculum-node `verified` flag is set to true. This prevents SumTalsa from inventing or mislabelling curriculum content.

## Deployment
Use:
`docker compose -f docker-compose.production.yml up --build -d`

Then place SumTalsa behind a host/reverse proxy that provides TLS/HTTPS, or use a managed platform with automatic HTTPS.

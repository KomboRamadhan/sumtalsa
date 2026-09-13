# SumTalsa Final Release

## Release type
Full-stack production-ready pilot package.

## Verified in this build
- Python source compiles.
- Backend API starts.
- Health endpoint responds.
- Seeded user authentication works.
- Static website and app are served by the backend.
- Role-based API protection is implemented.
- Database-backed resources, feedback, interventions and curriculum-version records are implemented.

## Still required before storing real student data
- Deploy behind HTTPS.
- Set a strong SECRET_KEY.
- Prefer PostgreSQL for multi-user production.
- Remove demo users after initial testing.
- Import and verify authoritative TIE curriculum records.
- Complete school-specific privacy/consent review.
- Test parent-to-learner linking before enabling real parent records.
- Configure live AI only after setting usage limits and review controls.

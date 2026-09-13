from pathlib import Path
import secrets

p=Path(".env.production")
if p.exists():
    print(".env.production already exists; refusing to overwrite.")
else:
    secret=secrets.token_urlsafe(64)
    p.write_text(
f'''APP_NAME=SumTalsa
SECRET_KEY={secret}
ACCESS_TOKEN_MINUTES=480
FORCE_HTTPS=true
ALLOWED_HOSTS=*
DATABASE_URL=postgresql+psycopg://sumtalsa:CHANGE_DB_PASSWORD@db:5432/sumtalsa
AI_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_MODEL=
PUBLIC_BASE_URL=https://YOUR-DOMAIN
''', encoding="utf-8")
    print("Created .env.production with a strong generated SECRET_KEY.")
    print("Now replace CHANGE_DB_PASSWORD and YOUR-DOMAIN before deployment.")

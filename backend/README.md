# Form@Prospect Cloud Backend — V1.1-A

Socle serveur de Form@Prospect. L'application Windows ne doit jamais se connecter
directement à PostgreSQL ou utiliser une clé Supabase privilégiée.

## Démarrage local

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r backend/requirements.txt
copy backend/.env.example backend/.env
uvicorn backend.app.main:app --reload
```

## Variables obligatoires en production

- `DATABASE_URL` : connexion PostgreSQL (utilisateur applicatif sans `BYPASSRLS`).
- `SUPABASE_URL` : URL du projet Supabase.
- `SUPABASE_JWT_ISSUER` : émetteur attendu dans les JWT.
- `SUPABASE_JWT_AUDIENCE` : audience attendue, généralement `authenticated`.
- `SUPABASE_JWKS_URL` : endpoint public des clés de signature.
- `ALLOWED_HOSTS` : hôtes publics autorisés.

Le mode `local_test` est réservé aux tests automatisés et ne doit jamais être
activé dans un environnement exposé.


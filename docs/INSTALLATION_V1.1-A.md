# Installation technique V1.1-A

Cette livraison installe le socle serveur ; elle ne bascule pas encore les postes
Windows vers le Cloud.

## Développement local

1. Installer Python 3.12.
2. Créer un environnement virtuel.
3. Installer `backend/requirements.txt`.
4. Copier `backend/.env.example` vers `backend/.env`.
5. Renseigner une base de développement et les paramètres Supabase.
6. Appliquer `alembic -c backend/alembic.ini upgrade head`.
7. Démarrer `uvicorn backend.app.main:app --reload`.

## Production

- utiliser PostgreSQL et jamais SQLite ;
- utiliser un rôle d'exécution distinct du propriétaire des tables, sans
  `BYPASSRLS` ;
- placer FastAPI derrière un reverse proxy HTTPS ;
- conserver les secrets exclusivement dans le gestionnaire de secrets de
  l'hébergeur ;
- ne jamais publier `backend/.env` ;
- déployer d'abord en préproduction et exécuter la recette RLS.


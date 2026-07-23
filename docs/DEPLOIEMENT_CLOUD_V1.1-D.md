# Déploiement Cloud V1.1-D

## Pré-requis

- API V1.1-C opérationnelle sur Render ;
- base Supabase et organisation initiale actives ;
- variables Render `DATABASE_URL` et `MIGRATION_DATABASE_URL` déjà configurées.

## Déploiement

1. Copier le contenu du dossier Cloud V1.1-D à la racine du dépôt GitHub privé `formaprospect-cloud`.
2. Valider le commit `Déploiement Cloud V1.1-D`.
3. Render lance automatiquement le pré-déploiement et `alembic upgrade head`.
4. Le journal doit terminer sans erreur et le service doit être `Live`.
5. Vérifier l'URL `/api/v1/health`.

La migration ajoute une fonction PostgreSQL `SECURITY DEFINER` limitée à la découverte des adhésions actives. Le client Windows ne peut pas choisir arbitrairement une organisation : l'API déduit les organisations autorisées depuis l'identité JWT vérifiée.

## Recette minimale

- connexion administrateur acceptée ;
- mot de passe incorrect refusé ;
- absence de JWT refusée par l'API ;
- compte ou adhésion désactivé(e) refusé(e) ;
- fermeture de session et nouvelle authentification fonctionnelles.

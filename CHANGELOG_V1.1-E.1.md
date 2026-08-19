# Changelog — V1.1-E.1

## Correctifs
- Le déploiement initial importe désormais les prospects SQLite avant le passage du projet en mode Cloud.
- Le fichier `project.json` n'est marqué `deployed` qu'après un import complet sans échec.
- Le client API interprète désormais le contrat backend réel : `created`, `updated`, `ignored`, `errors`, `processed`, `warnings`.
- Un projet déjà déployé peut être synchronisé avec son projet Cloud existant sans création d'un doublon.
- Le bouton du Dashboard devient **Synchroniser** lorsqu'un projet possède déjà une identité Cloud.
- Le message de réussite indique le nombre de prospects importés.
- `last_sync_at` est actualisé après une synchronisation réussie.

## Sécurité fonctionnelle
- En cas d'import incomplet ou comportant des erreurs, un nouveau projet local ne bascule pas en mode Cloud.
- La synchronisation d'un projet existant réutilise strictement son `project_id` et son `organization_id`.

## Périmètre
- Application locale principale uniquement.
- Aucun changement de schéma PostgreSQL.
- Aucune migration Alembic.
- Aucun changement dans `Form@Prospect-cloud-local`.

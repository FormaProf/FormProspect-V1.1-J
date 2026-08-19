# Changelog — Form@Prospect RC-01.3.1

## Objectif

Achever la migration de la page CRM vers `DataSourceResolver`.

## Fichier remplacé

- `ui/pages/prospects_page.py`

## Changements

- Suppression de `CloudRuntime.is_active()` comme critère de sélection Local/Cloud.
- La page CRM partage désormais le même `DataSourceResolver` que `ProspectService`.
- Un projet local fournit son chemin SQLite.
- Un projet déployé utilise le provider Cloud et ne transmet aucun chemin SQLite.
- Les contrôles Export, Scoring et Transformation se basent sur le projet actif, et non sur la simple connexion utilisateur.
- Les signatures et composants visuels existants sont conservés.

## Non modifié

- `services/prospect_service.py`
- `services/prospect_data_provider.py`
- repositories SQLite
- backend FastAPI
- API Cloud

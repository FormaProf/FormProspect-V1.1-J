# Changelog — Form@Prospect RC-01.3

## Objectif

Migrer `ProspectService` vers la résolution de source introduite en RC-01.2.

## Fichiers

### Créé
- `services/prospect_data_provider.py`
- `tests/test_prospect_service_rc_01_3.py`

### Remplacé
- `services/prospect_service.py`

## Changements

- La source Local/Cloud dépend désormais du projet actif via `DataSourceResolver`.
- `CloudRuntime.is_active()` n'est plus utilisé comme critère de sélection.
- La logique SQLite est encapsulée dans `LocalProspectDataProvider`.
- La logique API est encapsulée dans `CloudProspectDataProvider`.
- Les signatures publiques historiques de `ProspectService` sont conservées.
- Le scoring Cloud reste volontairement désactivé.

## Non modifié

- `repositories/prospect_repository.py`
- `services/cloud_runtime.py`
- `services/cloud_api_client.py`
- backend FastAPI

# Form@Prospect — Changelog RC-01.2

## Objet

Introduction du composant central chargé de déterminer si le projet actif
utilise les données locales SQLite ou les données Form@Prospect Cloud.

## Fichier applicatif créé

- `core/datasource_resolver.py`

## Comportement

- La source est déterminée à partir du projet actif et de `project.json`.
- Une session Cloud active ne provoque pas le basculement automatique d'un projet local vers le Cloud.
- Le mode Cloud exige `deployment_status = "deployed"` et un `project_id`.
- Les configurations incohérentes produisent une erreur explicite.
- Aucun service existant n'est encore migré dans ce sprint.

## Compatibilité

Cette RC est additive. Aucun fichier existant n'est remplacé.

## Étape suivante

RC-01.3 : migration contrôlée de `ProspectService` vers `DataSourceResolver`.

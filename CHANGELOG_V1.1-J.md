# Form@Prospect V1.1-J — Correctif CRM Cloud

## Correction principale

- Enregistrement explicite du routeur `prospects` dans le registre FastAPI.
- Conservation des routes CRM complémentaires (`pipeline`, activités et historique).
- Version backend portée à `1.1.0-j`.
- Ajout d'un test anti-régression vérifiant la présence de `/api/v1/prospects`.
- Ajout d'un contrôle de déploiement qui distingue une route absente (`404`) d'une route protégée (`401/403`).

## Cause confirmée

Le client Windows appelle correctement `/api/v1/prospects`. Le dépôt contient également cette route. Le message `Not Found` provient donc d'un backend déployé qui n'a pas chargé le routeur CRM correspondant à la version du dépôt.

## Aucun changement de données

Aucune migration SQL n'est requise. Les 45 134 prospects existants ne sont ni modifiés ni réimportés.

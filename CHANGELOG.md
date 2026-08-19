# V1.1-J3 — Modèle utilisateur Cloud

## Ajouts
- Nouveau package Desktop `models`.
- Nouveau modèle immuable `CloudUser`.
- Validation des données reçues du backend.
- Propriétés `full_name`, `display_name` et `role_label`.
- Indicateurs de rôles et d'éligibilité à l'affectation d'un projet.
- Tests unitaires du modèle.

## Modification
- `CloudAPIClient.list_users()` retourne désormais `list[CloudUser]`.

## Impact
- Aucun changement du backend.
- Aucun changement de base de données.
- Aucun changement visuel à ce stade.

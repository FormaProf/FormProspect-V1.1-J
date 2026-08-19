# Rapport de tests V1.1-J

## Tests ajoutés

- Présence de la route relative `/prospects`.
- Présence de la route détail `/prospects/{prospect_id}`.
- Présence de `/pipeline/stages`.
- Présence de la route finale préfixée `/api/v1/prospects`.
- Contrôle de la version backend `1.1.0-j`.

## Critère de validation en production

- `GET /api/v1/prospects` sans authentification doit retourner `401` ou `403`, jamais `404`.
- Avec une session valide et l'en-tête d'organisation, la requête doit retourner `200` ainsi que `X-Total-Count`.
- L'écran CRM doit afficher la première page et le total de 45 134 prospects.

## Limite de l'environnement de préparation

Les tests d'intégration complets nécessitent les dépendances et la configuration du backend existant ainsi qu'un accès à la base Cloud. Le correctif fournit les tests à exécuter dans le dépôt ou la CI.

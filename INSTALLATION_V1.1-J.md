# Installation V1.1-J

1. Copier les fichiers du correctif dans la racine du dépôt en conservant les chemins.
2. Vérifier que `backend/app/api/router.py`, `backend/app/main.py` et le test V1.1-J sont bien remplacés/ajoutés.
3. Commit et push sur la branche reliée au service backend Render.
4. Relancer un déploiement complet du backend, pas seulement l'application Windows.
5. Contrôler les logs de démarrage et la réponse de `/api/v1/health`.
6. Exécuter `python tools/check_crm_endpoint.py`.
7. Un résultat `401` ou `403` signifie que la route existe et est protégée. Un résultat `404` signifie que Render utilise encore un mauvais dépôt, une mauvaise branche ou un ancien build.
8. Relancer Form@Prospect puis ouvrir le CRM.

## Point de contrôle Render

Le service backend doit être connecté au dépôt/à la branche contenant ce correctif. La commande de démarrage doit charger `backend.app.main:app`.

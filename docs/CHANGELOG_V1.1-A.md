# Form@Prospect — Changelog V1.1-A

Date : 20 juillet 2026

## Ajouts

- Nouveau backend FastAPI autonome sous `backend/`.
- Configuration PostgreSQL/Supabase par variables d'environnement.
- Validation stricte interdisant SQLite et les secrets de test en production.
- Modèle multi-organisation fondé sur des UUID.
- Profils utilisateurs séparés des adhésions aux organisations.
- Cinq rôles : administrateur, manager, commercial, formateur et assistant
  administratif.
- Catalogue centralisé de permissions RBAC.
- Vérification des JWT Supabase par JWKS, audience et émetteur.
- Contrôle de l'état du profil et de l'adhésion à chaque requête authentifiée.
- Identification des appareils et socle de révocation.
- Journal d'audit avec IP, appareil, user-agent et identifiant de requête.
- En-têtes HTTP de sécurité et identifiant de corrélation.
- Migration Alembic `0001_v11a`.
- Politiques PostgreSQL Row Level Security par organisation.
- Dockerfile exécuté avec un utilisateur non privilégié.
- Suite de tests automatisés du backend.

## Compatibilité

- Aucun écran PySide6 existant n'est modifié.
- Aucune base SQLite locale n'est migrée ou supprimée dans ce sprint.
- L'authentification locale V1.0 reste fonctionnelle tant que V1.1-B n'est pas
  validée.

## Prochaine étape

V1.1-B : authentification Cloud complète, connexion/déconnexion, récupération de
mot de passe, renouvellement de session, coffre Windows et révocation distante.


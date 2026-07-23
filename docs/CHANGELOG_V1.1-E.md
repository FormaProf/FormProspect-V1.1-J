# Changelog V1.1-E

## Ajouté

- API `/admin/users` pour lister et inviter les collaborateurs.
- API de modification des rôles et statuts.
- API de réinitialisation de mot de passe par e-mail.
- API `/admin/audit` et affichage du journal dans l'application.
- Client Supabase Admin réservé au backend.
- Tests du cycle d'administration complet.

## Modifié

- Console Windows raccordée aux comptes Cloud réels.
- Version API, installateur et processus de build passés à `1.1.0-e`.
- Configuration de production exigeant la clé secrète serveur Supabase.

## Sécurité

- Contrôle RBAC sur chaque route.
- Cloisonnement systématique par organisation.
- Protection du dernier administrateur actif.
- Journalisation des invitations, changements et réinitialisations.

# Form@Prospect V1.1-E — Administration Cloud des collaborateurs

Date : 21 juillet 2026

## Nouveautés

- invitation d'un collaborateur depuis l'application Windows ;
- attribution des cinq rôles Cloud : administrateur, manager, commercial,
  formateur et assistant administratif ;
- modification centralisée du rôle ;
- activation et désactivation immédiates de l'accès à l'organisation ;
- protection contre la désactivation ou la rétrogradation du dernier
  administrateur actif ;
- envoi d'un lien sécurisé de réinitialisation du mot de passe par e-mail ;
- consultation dans l'application du journal des opérations administratives ;
- messages d'erreur précis renvoyés par l'API.

## Sécurité

La clé `SUPABASE_SERVICE_ROLE_KEY` n'est jamais intégrée à l'application
Windows. Elle doit uniquement être configurée dans les variables secrètes du
serveur Render. L'application utilise le jeton de l'administrateur connecté et
l'API vérifie le rôle, l'organisation et les permissions avant chaque action.

## Compatibilité

Cette version s'installe sur la V1.1-D et ne modifie ni les projets locaux, ni
les prospects, ni les données CRM. Aucune nouvelle table PostgreSQL n'est
nécessaire : la V1.1-E exploite les tables d'identité et d'audit créées par la
fondation Cloud V1.1-A.

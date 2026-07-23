# Form@Prospect V1.1-D — Authentification Cloud Windows

## Objet

La V1.1-D rend la connexion Cloud obligatoire dans l'application Windows. Un compte local ne peut plus ouvrir le logiciel.

## Fonctions livrées

- connexion par e-mail et mot de passe via Supabase Auth ;
- validation du compte, de l'organisation et du rôle par l'API FastAPI ;
- session JWT renouvelée automatiquement ;
- jeton de renouvellement conservé dans le coffre sécurisé Windows ;
- déconnexion locale et révocation de la session distante ;
- arrêt automatique de l'application si le compte ou l'adhésion est désactivé ;
- récupération du mot de passe par le portail sécurisé ;
- rattachement automatique à l'organisation active ;
- conservation d'un identifiant local technique pour la compatibilité des modules V1 existants, sans mot de passe utilisable.

## Ordre d'installation obligatoire

1. Mettre à jour le dépôt Cloud avec le paquet `FormProspect_CLOUD_V1.1-D`.
2. Attendre le déploiement Render réussi et la migration Alembic `0002_v11d`.
3. Vérifier `https://api.forma-prof.fr/api/v1/health`.
4. Installer ou lancer l'application Windows V1.1-D.
5. Se connecter avec le compte administrateur Cloud existant.

## Sécurité

Les mots de passe ne sont jamais stockés par Form@Prospect. Le jeton d'accès reste uniquement en mémoire et le jeton de renouvellement est confié au gestionnaire d'identifiants Windows.

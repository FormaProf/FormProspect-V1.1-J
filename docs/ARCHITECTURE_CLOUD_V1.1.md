# Architecture Cloud Form@Prospect V1.1

## Décision officielle

L'application Windows PySide6 dialogue uniquement avec l'API FastAPI par HTTPS.
FastAPI détient la logique métier et accède à PostgreSQL, Supabase Auth et au
stockage privé. Aucune clé privilégiée et aucun accès direct à PostgreSQL ne
doivent être intégrés dans l'exécutable Windows.

## Séparation multi-organisation

Toutes les données métier Cloud porteront un `organization_id`. Les identités
sont séparées des adhésions : un profil peut rejoindre plusieurs organisations,
avec un rôle et un état distincts dans chacune.

Rôles initiaux : administrateur, manager, commercial, formateur et assistant
administratif. Le super-administrateur de plateforme sera distinct de ces rôles.

## Sécurité

- JWT Supabase vérifiés avec JWKS et contrôle de l'émetteur/audience.
- adhésion active contrôlée à chaque requête ;
- permissions RBAC appliquées dans FastAPI ;
- contexte tenant injecté dans la transaction PostgreSQL ;
- politiques RLS comme seconde barrière ;
- rôle PostgreSQL d'exécution distinct du propriétaire des tables et sans
  attribut `BYPASSRLS` ;
- journal d'audit append-only côté application ;
- configuration `local_test` interdite en production.

## Migration progressive

La V1.0 locale n'est pas modifiée par le Sprint V1.1-A. Les repositories API
seront introduits côté bureau lors des sprints suivants. Les repositories SQLite
resteront disponibles pendant la migration contrôlée et la recette, sans devenir
un mécanisme de partage ou de synchronisation.

## Éléments livrés par V1.1-A

- application FastAPI et endpoints de santé ;
- configuration typée et protégée ;
- modèles organisations, profils, adhésions, appareils et audit ;
- matrice RBAC des cinq rôles ;
- vérification JWT Supabase ;
- migration Alembic initiale ;
- politiques RLS PostgreSQL ;
- image Docker non-root ;
- tests automatisés du socle.


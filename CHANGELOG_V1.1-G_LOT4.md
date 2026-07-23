# Form@Prospect V1.1-G — Lot 4

## Objectif
Fusionner l'application desktop Cloud historique avec le backend Cloud validé du Lot 3.

## Éléments livrés
- Backend Lot 3 intégré comme backend unique du projet.
- Client API Cloud authentifié centralisé.
- URL API et paramètres Supabase configurables par variables d'environnement.
- CRM desktop branché sur l'API Cloud pour la liste, la recherche, les filtres, la pagination et la fiche prospect.
- Déplacement Kanban relié à l'historique de pipeline Cloud.
- Modification de la priorité, de la prochaine action et de sa date via l'API.
- Notes et historique d'activités reliés aux activités Cloud.
- Compatibilité des identifiants UUID dans les signaux Qt.
- Conservation du mode local pour les modules non encore migrés.
- Isolation des données toujours imposée par le backend : administrateur = organisation entière ; commercial = prospects affectés.

## Limites explicites de cette étape
- Import, export Excel, scoring et transformation en client restent locaux et sont désactivés dans la vue Cloud pour éviter des écritures incohérentes.
- La création de prospect depuis le desktop n'était pas présente dans l'écran CRM historique fourni ; elle n'est donc pas ajoutée dans ce correctif.
- L'exécutable Windows doit être reconstruit sur Windows avec `build_release.bat`.

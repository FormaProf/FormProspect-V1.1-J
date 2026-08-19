# Installation — RC-01.3

## Dossier concerné

Uniquement le dossier principal de l'application desktop :

`Form@Prospect`

Ne rien copier dans `Form@Prospect-cloud-local`.

## Avant installation

1. Fermer Form@Prospect.
2. Faire une copie de sauvegarde de :
   - `services/prospect_service.py`
3. Vérifier que RC-01.2 est déjà installée :
   - `core/datasource_resolver.py`

## Fichiers à copier

Depuis l'archive :

- remplacer `services/prospect_service.py`
- ajouter `services/prospect_data_provider.py`

Le dossier `tests` et les fichiers Markdown sont destinés à la validation et à la documentation.

## Validation utilisateur

1. Lancer l'exécutable depuis `release`.
2. Ouvrir un projet local.
3. Ouvrir le CRM Prospects.
4. Vérifier :
   - affichage de la liste ;
   - recherche ;
   - filtres ;
   - ouverture d'une fiche ;
   - modification du pipeline ;
   - modification des coordonnées.
5. Se connecter au Cloud sans déployer un projet local :
   le projet doit continuer à utiliser SQLite.
6. Tester un projet réellement déployé si disponible.

## Retour arrière

Restaurer l'ancien `services/prospect_service.py` et supprimer
`services/prospect_data_provider.py`.

# Installation — RC-01.4-B

## Projet concerné

Application desktop principale `Form@Prospect`.

## Prérequis

RC-01.4-A déjà installée.

## Fichiers à copier

1. Remplacer :

`repositories/prospect_repository.py`

2. Ajouter :

`services/deployment/readers/__init__.py`

`services/deployment/readers/base_reader.py`

`services/deployment/readers/prospect_reader.py`

## Important

Ne rien copier dans le backend Cloud.

## Contrôle manuel

Après copie :

1. lancer Form@Prospect ;
2. ouvrir un projet local ;
3. vérifier que le CRM affiche toujours les prospects ;
4. vérifier que recherche, filtres et changement de pipeline fonctionnent.

Aucun changement visuel n'est attendu.

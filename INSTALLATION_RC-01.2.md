# Installation — RC-01.2

## Projet concerné

Application desktop `Form@Prospect`, et non le dépôt backend Cloud.

## Installation manuelle

1. Fermer Form@Prospect.
2. Sauvegarder le dossier actuel du projet source.
3. Copier `core/datasource_resolver.py` dans `Form@Prospect/core/datasource_resolver.py`.
4. Ne remplacer aucun autre fichier.
5. Relancer l'application et vérifier qu'elle s'ouvre normalement.

Le fichier de test est fourni pour la validation développeur, mais il n'est pas nécessaire au fonctionnement de l'application.

## Tests recommandés

Depuis la racine du projet source :

```bash
python -m unittest tests.test_datasource_resolver -v
```

Puis vérifier manuellement :

- ouverture d'un projet local ;
- connexion Cloud sans déploiement du projet : le projet doit rester local ;
- ouverture d'un projet marqué `deployed` avec un `project_id` valide.

## Retour arrière

Supprimer simplement `core/datasource_resolver.py`.
Aucun fichier existant n'ayant été modifié, le retour arrière est immédiat.

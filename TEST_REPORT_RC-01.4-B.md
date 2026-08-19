# Rapport de tests — RC-01.4-B

## Tests automatisés

- compilation syntaxique de tous les fichiers Python ;
- lecture de 12 prospects en lots 5 / 5 / 2 ;
- lecture via `ProspectDeploymentReader` en lots 4 / 4 / 4 ;
- reprise à l'offset 10 ;
- contrôle du total, des offsets et du dernier lot.

## Résultat

Tous les tests automatisés de la livraison sont passés.

## Validation restant à effectuer dans l'application

- ouverture du logiciel ;
- affichage du CRM local ;
- recherche et filtres ;
- modification du pipeline.

Cette validation est nécessaire car la livraison n'inclut pas l'ensemble du
projet desktop ni son `BaseRepository`.

# Rapport de tests — RC-01.3

## Contrôles exécutés dans l'environnement de livraison

- Compilation Python de `services/prospect_service.py` : OK
- Compilation Python de `services/prospect_data_provider.py` : OK
- Compilation Python du fichier de tests : OK

## Tests unitaires fournis

- sélection du provider local ;
- sélection du provider Cloud ;
- conservation de la validation du pipeline ;
- délégation correcte d'une recherche filtrée.

## Limite de validation

Les tests d'intégration complets avec PySide6, SQLite et le backend Cloud
doivent être exécutés dans le dépôt complet Form@Prospect, qui contient
l'ensemble des dépendances et de la base applicative.

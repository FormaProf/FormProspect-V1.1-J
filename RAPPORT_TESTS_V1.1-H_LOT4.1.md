# Rapport de tests — Form@Prospect V1.1-H Lot 4.1

## Environnement de validation

- Python 3.13
- pytest
- Base SQLite temporaire pour les tests desktop
- Backend FastAPI avec base de test isolée

## Résultats

### Desktop et intégration

Commande :

```bash
python -m pytest tests -q
```

Résultat : **35 tests réussis**.

### Backend

Commande :

```bash
python -m pytest backend/tests -q
```

Résultat : **32 tests réussis**.

### Total

**67 tests réussis, 0 échec.**

## Régression couverte

Le test `test_managed_connection_is_closed_after_context` vérifie que :

1. la transaction SQLite est validée ;
2. la connexion est inutilisable après la sortie du bloc `with` ;
3. le fichier `project.db` peut être renommé puis supprimé immédiatement.

Cette validation cible directement le verrouillage Windows signalé dans le Lot 4.

## Limite de validation

La suite a été exécutée dans l'environnement de construction Linux. Le correctif vise explicitement le comportement de verrouillage Windows, mais le test final doit être relancé sur le poste Windows de livraison avec les commandes fournies dans le guide d'installation.

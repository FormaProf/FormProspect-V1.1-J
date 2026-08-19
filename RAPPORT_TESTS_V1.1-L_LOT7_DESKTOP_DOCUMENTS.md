# Rapport de tests — Lot 7

## Réalisé

- Compilation Python des trois fichiers : réussie.
- Analyse AST des trois fichiers : réussie.
- Test isolé de l'upload multipart du client Cloud : réussi.
- Vérification des contrats API utilisés : catalogue, création de session, génération, historique, URL de téléchargement, upload administratif et upload de modèle.

## Limite de l'environnement de test

PySide6 n'est pas installé dans l'environnement de génération. L'ouverture visuelle réelle des fenêtres doit donc être validée dans l'application Windows de l'utilisateur.

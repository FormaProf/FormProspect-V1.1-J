# Correctif 7.1 — Catalogue des formations Cloud

## Problème corrigé
La version précédente permettait uniquement de créer une formation Cloud. Elle ne proposait aucun écran pour retrouver, modifier, désactiver ou supprimer les formations déjà créées.

## Backend
- PATCH `/api/v1/documents/trainings/{training_id}`
- DELETE `/api/v1/documents/trainings/{training_id}`
- contrôle administrateur via `TRAINING_MANAGE`
- suppression définitive autorisée uniquement pour une formation jamais utilisée
- désactivation possible pour conserver l'historique des sessions et documents
- audit des modifications et suppressions

## Application Windows
- bouton `Gérer les formations`
- tableau complet du catalogue Cloud, formations actives et inactives
- création, modification, activation/désactivation et suppression
- double-clic sur une formation pour la modifier
- proposition de désactivation lorsqu'une suppression est interdite car la formation a déjà été utilisée

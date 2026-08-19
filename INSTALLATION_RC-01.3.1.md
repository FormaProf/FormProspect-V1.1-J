# Installation — RC-01.3.1

## Emplacement

Cette mise à jour concerne uniquement l'application desktop principale :

`Form@Prospect`

## Prérequis

RC-01.2 et RC-01.3 doivent déjà être installées.

## Installation

1. Fermer Form@Prospect.
2. Sauvegarder :
   - `ui/pages/prospects_page.py`
3. Copier depuis l'archive et remplacer :
   - `ui/pages/prospects_page.py`
4. Reconstruire l'exécutable si le dossier `release` contient une version PyInstaller figée.
5. Relancer Form@Prospect.

## Validation

### Projet local
- Le Dashboard et le CRM doivent lire la même base SQLite.
- La liste, les recherches et les filtres doivent fonctionner.

### Projet déployé
- Le CRM doit lire l'API Cloud.
- Une connexion Cloud seule ne doit jamais transformer un projet local en projet Cloud.

## Point important

Le projet visible sur les captures est marqué « Déployé ». Après cette correction,
le CRM utilisera donc volontairement les données Cloud. Si les 45 134 prospects
n'ont pas encore été transférés vers le backend, le CRM Cloud restera vide :
ce sera alors un problème de déploiement/synchronisation des données, pas un
problème d'affichage de la page CRM.

## Retour arrière

Restaurer l'ancien fichier `ui/pages/prospects_page.py`.

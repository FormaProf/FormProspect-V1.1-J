# Recette finale — Form@Prospect 1.0.0

Cette checklist doit être entièrement validée sur la version installée, idéalement sur un ordinateur Windows ne disposant pas de Python.

## A. Installation

- [ ] L’installateur démarre sans erreur.
- [ ] Le nom, la version et l’éditeur sont corrects.
- [ ] L’icône est visible sur l’installateur.
- [ ] Le raccourci Bureau est créé si l’option est cochée.
- [ ] Le raccourci utilise l’icône Form@Prospect.
- [ ] Le logiciel démarre sans terminal.
- [ ] Le splash screen s’affiche correctement.
- [ ] Aucune installation de Python n’est nécessaire.

## B. Projet

- [ ] Création d’un projet dans un nouveau dossier.
- [ ] Présence de `project.json` et `project.db`.
- [ ] Présence des dossiers `imports`, `exports`, `logs`, `cache` et `backups`.
- [ ] Fermeture puis ouverture du projet existant.
- [ ] Le projet actif apparaît sur le Dashboard.

## C. Import

- [ ] Sélection d’un fichier `.xlsx` de test.
- [ ] Affichage correct du nombre de lignes et de colonnes.
- [ ] Import terminé sans erreur.
- [ ] Entreprise, SIRET, SIREN, code postal, ville et code NAF correctement importés.
- [ ] Conservation des zéros initiaux des identifiants et codes postaux.

## D. Dashboard

- [ ] Nombre total de prospects correct.
- [ ] Compteurs téléphone, email et site corrects.
- [ ] Répartition du pipeline correcte.
- [ ] Indicateurs de qualité cohérents.
- [ ] Centre d’action cohérent.
- [ ] Bouton Rafraîchir fonctionnel.

## E. CRM Tableau

- [ ] Les 100 premières lignes sont affichées sur la première page.
- [ ] Première, Précédente, Suivante et Dernière fonctionnent.
- [ ] La plage affichée et le nombre total sont corrects.
- [ ] Le tri fonctionne sur les colonnes.
- [ ] Les largeurs de colonnes sont mémorisées.
- [ ] Le double-clic ouvre le bon prospect, y compris après un tri.

## F. Recherche et filtres

- [ ] Recherche par entreprise.
- [ ] Recherche par ville.
- [ ] Filtre Pipeline.
- [ ] Filtre Priorité.
- [ ] Filtre Commercial.
- [ ] Filtre Ville.
- [ ] Cumul de plusieurs filtres.
- [ ] Pagination des résultats filtrés.
- [ ] Effacement complet des filtres.

## G. Fiche prospect

- [ ] Modification des coordonnées.
- [ ] Modification du pipeline.
- [ ] Modification de la priorité.
- [ ] Modification de la prochaine action et de sa date.
- [ ] Modification du commercial assigné.
- [ ] Ajout d’une note.
- [ ] Présence de la note dans la liste.
- [ ] Historique des changements correctement alimenté.
- [ ] Persistance des modifications après redémarrage.

## H. Kanban

- [ ] Affichage des cartes dans les bonnes colonnes.
- [ ] Double-clic sur une carte.
- [ ] Déplacement d’une carte vers chaque type de colonne.
- [ ] Défilement horizontal automatique près des bords.
- [ ] Dépôt possible dans toute la surface d’une colonne.
- [ ] Mise à jour immédiate du Tableau après déplacement.
- [ ] Persistance du pipeline après redémarrage.

## I. Export

- [ ] Création d’un fichier `.xlsx`.
- [ ] Nombre de lignes exportées correct.
- [ ] Ouverture du fichier dans Excel.
- [ ] Présence des principales colonnes CRM.

## J. Sauvegarde et restauration

- [ ] Création d’un fichier `.fpbackup`.
- [ ] Journalisation de la sauvegarde.
- [ ] Validation d’une sauvegarde correcte.
- [ ] Refus d’un fichier invalide.
- [ ] Restauration dans un nouveau dossier.
- [ ] Absence d’écrasement d’un projet existant.
- [ ] Ouverture automatique du projet restauré.
- [ ] Présence des prospects, notes et historiques restaurés.

## K. Identité et désinstallation

- [ ] Fenêtre Aide → À propos accessible.
- [ ] Version affichée : 1.0.0.
- [ ] Logo et copyright corrects.
- [ ] Désinstallation accessible depuis Windows.
- [ ] Les projets utilisateur ne sont pas supprimés sans avertissement.

## L. Contrôle du périmètre

- [ ] Les entrées non disponibles dans la V1 sont retirées, désactivées ou clairement identifiées.
- [ ] Aucun bouton visible ne semble actif sans produire d’action.
- [ ] Aucun texte « test » ou fonctionnalité expérimentale n’est présenté comme une fonction de production.

## Validation

- Version testée : `1.0.0`
- Date : ____________________
- Ordinateur / Windows : ____________________
- Testeur : ____________________
- Résultat : ☐ Accepté  ☐ Refusé
- Anomalies restantes :

```text

```

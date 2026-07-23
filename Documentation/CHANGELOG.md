# Historique des versions

Les évolutions importantes de Form@Prospect sont consignées dans ce fichier.

Le format suit les principes de *Keep a Changelog* et le versionnement sémantique.

## [À venir]

- import direct des fichiers CSV SIRENE ;
- fonctions avancées réservées aux versions ultérieures.

## [1.0.0] - 2026-07-13

### Ajouté

- création et ouverture de projets indépendants ;
- base de données SQLite propre à chaque projet ;
- import des prospects depuis un fichier Excel `.xlsx` ;
- export complet des prospects vers Excel ;
- dashboard avec indicateurs principaux, pipeline, qualité de la base et centre d’action ;
- CRM avec vue Tableau et vue Kanban ;
- recherche multicritère et filtres par pipeline, priorité, commercial et ville ;
- tri des colonnes et mémorisation de leur largeur ;
- pagination par groupes de 100 prospects ;
- fiche prospect avec coordonnées, réseaux sociaux, pipeline, priorité, prochaine action et commercial assigné ;
- notes CRM et historique des modifications ;
- déplacement des cartes Kanban par glisser-déposer ;
- défilement horizontal automatique pendant le déplacement d’une carte ;
- sauvegarde complète au format `.fpbackup` ;
- restauration sans écrasement d’un projet existant ;
- splash screen, icône Windows et fenêtre À propos ;
- génération d’un exécutable autonome et d’un installateur Windows.

### Corrigé

- affichage des 100 premiers prospects par défaut ;
- import de la ville depuis les colonnes SIRENE reconnues ;
- conservation du bon prospect lors de l’ouverture après un tri ;
- dépôt des cartes dans toute la surface d’une colonne Kanban ;
- défilement horizontal du Kanban pendant le glisser-déposer ;
- icône de l’exécutable, de l’installateur et des raccourcis Windows.

### Sécurité des données

- validation des sauvegardes avant restauration ;
- création d’un nouveau dossier lors d’une restauration pour éviter tout écrasement ;
- exclusion des sauvegardes imbriquées lors de la création d’un fichier `.fpbackup`.
# Version 1.1.0-e — 21 juillet 2026

- Administration Cloud des collaborateurs depuis l'application.
- Rôles, activation/désactivation et réinitialisation sécurisée.
- Journal d'audit visible par les administrateurs autorisés.
- Protection du dernier administrateur actif.

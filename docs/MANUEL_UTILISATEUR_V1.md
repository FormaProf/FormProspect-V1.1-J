# Manuel utilisateur — Form@Prospect 1.0.0

## 1. Présentation

Form@Prospect est un logiciel de prospection commerciale et de suivi CRM développé par NM FORMATION. Il permet d’importer une base de prospects, de rechercher et qualifier les entreprises, d’organiser le pipeline commercial et de sécuriser les projets par des sauvegardes.

## 2. Installation

### Configuration recommandée

- Windows 10 ou Windows 11 en 64 bits ;
- espace disque disponible pour le logiciel, les projets et les sauvegardes ;
- Microsoft Excel ou un logiciel compatible pour consulter les exports `.xlsx`.

### Installer Form@Prospect

1. Double-cliquez sur `Form@Prospect_Setup_v1.0.0.exe`.
2. Suivez les étapes de l’assistant d’installation.
3. Cochez la création d’un raccourci sur le Bureau si vous le souhaitez.
4. Cliquez sur **Terminer**.

Python n’est pas nécessaire pour utiliser la version installée.

## 3. Démarrage

Lancez Form@Prospect depuis le raccourci du Bureau ou le menu Démarrer. Un écran de démarrage apparaît pendant le chargement, puis la fenêtre principale s’ouvre.

Les trois espaces utilisés dans la version 1.0 sont :

- **Dashboard** : gestion du projet et vue d’ensemble ;
- **Traitement** : sélection et import d’un fichier Excel ;
- **CRM** : consultation et suivi des prospects.

## 4. Créer un projet

Chaque projet possède sa propre base de données, ses imports, ses exports, ses journaux et ses sauvegardes.

1. Ouvrez le **Dashboard**.
2. Cliquez sur **Nouveau projet**.
3. Saisissez le nom du projet.
4. Cliquez sur **Parcourir** et choisissez son emplacement.
5. Cliquez sur **Créer le projet**.

Le nouveau projet devient automatiquement le projet actif.

## 5. Ouvrir un projet existant

1. Depuis le Dashboard, cliquez sur **Ouvrir un projet**.
2. Sélectionnez le dossier du projet, et non le fichier `project.db`.
3. Validez.

Un dossier de projet valide contient notamment `project.json` et `project.db`.

## 6. Importer des prospects

### Format accepté

La version 1.0 accepte les fichiers Excel au format `.xlsx`.

Les colonnes courantes reconnues comprennent notamment :

- entreprise ou `denominationUniteLegale` ;
- SIRET et SIREN ;
- adresse ou éléments de voie ;
- code postal et ville ;
- code NAF ;
- téléphone, site web et email lorsqu’ils sont présents.

Les intitulés officiels SIRENE les plus courants sont reconnus automatiquement.

### Procédure

1. Créez ou ouvrez le projet qui doit recevoir les prospects.
2. Ouvrez **Traitement**.
3. Cliquez sur **Choisir un fichier Excel**.
4. Vérifiez le nombre de lignes et de colonnes affiché.
5. Cliquez sur **Importer dans le projet actif**.
6. Attendez le message confirmant le nombre de prospects importés.

Important : un nouvel import ajoute des lignes au projet. Avant de réimporter le même fichier, créez une sauvegarde et vérifiez que les données ne sont pas déjà présentes.

## 7. Utiliser le Dashboard

Le Dashboard présente :

- le projet actif ;
- le nombre total de prospects ;
- le nombre de téléphones, emails et sites web renseignés ;
- la répartition du pipeline ;
- la qualité de la base ;
- les actions du jour, actions en retard, priorités fortes et coordonnées manquantes.

Cliquez sur **Rafraîchir** après une modification importante si un compteur n’a pas encore été actualisé.

## 8. Utiliser le CRM

### Recherche

La barre de recherche permet de rechercher notamment une entreprise, une ville, un téléphone, un email, un pipeline, une action ou un commercial.

La recherche s’applique à toute la base du projet, pas seulement à la page visible.

### Filtres

Les filtres disponibles sont :

- Pipeline ;
- Priorité ;
- Commercial ;
- Ville.

Les filtres sont cumulables. Cliquez sur **Effacer filtres** pour revenir à la liste complète.

### Pagination

Le CRM affiche jusqu’à 100 prospects par page. Utilisez les boutons **Première**, **Précédente**, **Suivante** et **Dernière** pour naviguer.

La pagination reste compatible avec la recherche et les filtres actifs.

### Vue Tableau

- Cliquez sur un en-tête pour trier une colonne.
- Redimensionnez une colonne en déplaçant sa séparation dans l’en-tête.
- Double-cliquez sur une ligne pour ouvrir la fiche du prospect.

### Vue Kanban

1. Cliquez sur **Kanban**.
2. Les prospects de la page courante sont répartis selon leur pipeline.
3. Faites glisser une carte vers une autre colonne pour modifier son pipeline.
4. Approchez la carte du bord gauche ou droit pour faire défiler les colonnes.
5. Double-cliquez sur une carte pour ouvrir la fiche du prospect.

La modification du pipeline est enregistrée immédiatement dans la base du projet.

## 9. Gérer une fiche prospect

Dans la fiche prospect, vous pouvez renseigner ou modifier :

- téléphone ;
- site web ;
- email ;
- Facebook, LinkedIn, Instagram et YouTube ;
- pipeline ;
- priorité ;
- prochaine action ;
- date de prochaine action ;
- commercial assigné.

Cliquez sur **Enregistrer les informations** pour valider les modifications.

### Notes CRM

1. Saisissez une note dans la zone prévue.
2. Cliquez sur **Ajouter la note**.
3. La note apparaît dans la liste et une activité est ajoutée à l’historique.

### Historique

L’historique conserve les changements importants, notamment le pipeline, la priorité, la prochaine action, sa date et le commercial assigné.

## 10. Exporter les prospects

1. Ouvrez le **CRM**.
2. Cliquez sur **Exporter Excel**.
3. Choisissez le nom et l’emplacement du fichier `.xlsx`.
4. Attendez le message de confirmation.

Dans la version 1.0, l’export porte sur l’ensemble des prospects du projet.

## 11. Sauvegarder un projet

1. Ouvrez le projet concerné.
2. Depuis le Dashboard, cliquez sur **Sauvegarder**.
3. Choisissez l’emplacement du fichier.
4. Conservez l’extension `.fpbackup`.
5. Attendez le message de confirmation.

Une sauvegarde contient la base, la configuration et les dossiers utiles du projet. Le dossier `backups` lui-même est exclu afin d’éviter des archives imbriquées.

Conseil : conservez au moins une copie de sauvegarde sur un support différent de l’ordinateur principal.

## 12. Restaurer une sauvegarde

1. Depuis le Dashboard, cliquez sur **Restaurer**.
2. Sélectionnez le fichier `.fpbackup`.
3. Choisissez le dossier dans lequel restaurer le projet.
4. Confirmez l’opération.

Form@Prospect vérifie la sauvegarde avant de l’extraire. Si un projet du même nom existe déjà, un nouveau dossier est créé : aucune donnée existante n’est écrasée.

Le projet restauré est ensuite ouvert automatiquement.

## 13. À propos et version

Ouvrez **Aide → À propos de Form@Prospect** pour consulter :

- le nom du logiciel ;
- la version installée ;
- l’éditeur NM FORMATION ;
- les informations de copyright.

## 14. Bonnes pratiques

- Vérifiez toujours le projet actif avant un import.
- Créez une sauvegarde avant un import important ou une opération exceptionnelle.
- Ne modifiez pas manuellement `project.db` ou `project.json`.
- Ne déplacez pas uniquement la base : déplacez le dossier complet du projet.
- Fermez Form@Prospect avant de copier ou déplacer un projet avec l’Explorateur Windows.
- Conservez les SIREN, SIRET et codes postaux au format texte dans Excel pour préserver les zéros initiaux.

## 15. Dépannage

### Le projet ne s’ouvre pas

Vérifiez que le dossier sélectionné contient `project.json` et `project.db`.

### Le fichier Excel n’est pas proposé

Vérifiez que le fichier porte bien l’extension `.xlsx`.

### Certaines informations sont vides après l’import

Form@Prospect ne peut importer que les informations présentes dans le fichier source. Les fichiers SIRENE ne contiennent généralement ni téléphone, ni email, ni site web.

### Une sauvegarde est refusée

Le fichier doit porter l’extension `.fpbackup` et contenir un projet Form@Prospect valide.

### L’icône reste ancienne après une mise à jour

Supprimez l’ancien raccourci, puis recréez-le depuis la nouvelle installation. Windows peut conserver temporairement les anciennes icônes dans son cache.

## 16. Assistance

Lors d’une demande d’assistance, indiquez :

- la version de Form@Prospect ;
- la version de Windows ;
- l’action effectuée ;
- le message d’erreur exact ;
- une capture d’écran si possible.

© 2026 NM FORMATION — Tous droits réservés.

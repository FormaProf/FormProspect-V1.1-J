# Form@Prospect — Système de mise à jour automatique 1.0

Version source analysée : `V1.1-E.1`.

## Ce paquet ajoute

- vérification automatique des mises à jour après connexion ;
- menu **Aide > Rechercher des mises à jour** ;
- fenêtre premium de mise à jour ;
- téléchargement HTTPS ;
- contrôle SHA-256 obligatoire avant lancement ;
- installateur Inno Setup réutilisable pour les mises à jour ;
- génération automatique de `latest.json` et du SHA-256 ;
- dossier `release_publish` prêt à être envoyé sur le serveur.

## URL configurée

`https://forma-prof.fr/formaprospect/releases/latest.json`

Le logiciel ne plante pas si cette URL n'est pas encore disponible. La vérification
automatique échoue silencieusement ; une vérification manuelle affiche une information.

## Fichiers à copier dans le projet

Le ZIP respecte directement l'arborescence `Form@Prospect`.

## Premier test conseillé

1. Faire une sauvegarde du projet actuel.
2. Copier le contenu du dossier `Form@Prospect` de ce ZIP dans ton projet.
3. Lancer l'application en mode Python et vérifier qu'elle démarre.
4. Ouvrir **Aide > Rechercher des mises à jour**.
5. Tant que `latest.json` n'est pas publié, le message d'indisponibilité est normal.
6. Ensuite nous préparerons l'hébergement du dossier `release_publish` et le test
   réel `ancienne version -> nouvelle version`.

## Important

L'installateur utilise désormais un dossier par utilisateur :
`%LOCALAPPDATA%\Programs\Form@Prospect`

Cela évite de demander des droits administrateur aux setters et facilite les mises à jour.

Le `AppId` Inno Setup d'origine est conservé afin que les futures versions soient reconnues
comme des mises à jour de Form@Prospect.

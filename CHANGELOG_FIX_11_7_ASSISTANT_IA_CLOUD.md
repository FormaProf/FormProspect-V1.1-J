# Correctif Desktop 11.7 — Assistant IA Cloud

## Problème corrigé

La page Assistant IA utilisait uniquement l'ancienne base SQLite locale.
En session Cloud, elle tentait d'accéder à `project.database`, ce qui empêchait
l'ouverture de la rubrique sans afficher de message à l'utilisateur.

## Nouveau fonctionnement

- détection automatique d'une session Form@Prospect Cloud ;
- chargement des prospects visibles selon les droits du compte connecté ;
- classement et score interne explicable ;
- recommandations du jour ;
- qualification automatique ;
- copilote prospect ;
- préparation d'appel ;
- scripts, e-mails, objections et plans de relance ;
- historique IA et mémoire commerciale conservés localement sur le poste ;
- aucune donnée envoyée à un service d'IA externe ;
- affichage d'une erreur lisible au lieu de bloquer silencieusement la page.

Le fonctionnement historique SQLite reste conservé pour les projets locaux.

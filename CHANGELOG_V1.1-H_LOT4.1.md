# Form@Prospect V1.1-H — Lot 4.1

## Objet

Stabilisation du client desktop fusionné avant la poursuite de la migration Cloud.

## Corrections

- Fermeture déterministe des connexions SQLite utilisées comme gestionnaires de contexte.
- Suppression du verrouillage résiduel de `project.db` observé sous Windows pendant les tests.
- Ajout de `core/sqlite_utils.py` avec une connexion SQLite qui valide ou annule la transaction puis ferme toujours le fichier.
- Migration des services desktop concernés vers ce gestionnaire commun.
- Rétablissement des composants Cloud Lot 4 absents du dossier installé : client API, runtime Cloud et mapping CRM.
- Rétablissement des services et écrans nécessaires à l'intégration Cloud existante.
- Ajout d'un test de non-régression vérifiant la fermeture effective puis le renommage et la suppression de la base temporaire.

## Compatibilité

- Le backend et ses migrations ne sont pas modifiés fonctionnellement.
- Les modules locaux restent disponibles.
- Aucun changement de schéma SQLite n'est introduit par ce correctif.

# Installation — Form@Prospect V1.1-E.1

## Dossier concerné
Appliquer ce correctif dans le dossier principal local **Form@Prospect**.
Ne pas copier ces fichiers dans `Form@Prospect-cloud-local` : aucune modification backend n'est requise pour cette release.

## Avant installation
1. Fermer Form@Prospect.
2. Copier intégralement le dossier principal `Form@Prospect` dans un dossier de sauvegarde.
3. Conserver le dossier de projet utilisateur contenant `project.db` et `project.json`.

## Installation
Copier le contenu du dossier `PATCH_V1.1-E.1` à la racine du dossier principal `Form@Prospect` en conservant l'arborescence et en remplaçant les fichiers existants.

Fichiers remplacés :
- `services/project_deployment_service.py`
- `services/cloud_api_client.py`
- `ui/pages/dashboard_page.py`

Le fichier situé dans `tests/` est facultatif pour l'exécution, mais recommandé pour conserver les tests de la release.

## Récupération du projet déjà déployé
1. Relancer Form@Prospect et ouvrir le projet concerné.
2. Se connecter au compte Cloud administrateur habituel.
3. Le bouton vert affiche désormais **Synchroniser**.
4. Cliquer sur **Synchroniser**.
5. Le logiciel réutilise le `project_id` existant et importe les prospects locaux sans créer un second projet Cloud.
6. Ouvrir le CRM et vérifier que les prospects apparaissent.

## Nouveau déploiement
Pour un projet encore local, le bouton **Déployer** :
1. crée le projet Cloud ;
2. importe les prospects locaux ;
3. vérifie le résultat ;
4. marque `project.json` comme `deployed` uniquement après succès.

## Retour arrière
Restaurer les trois fichiers depuis la sauvegarde du dossier principal. Ne pas modifier manuellement `project.json` pendant l'opération.

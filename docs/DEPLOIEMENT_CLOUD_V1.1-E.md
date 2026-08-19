# Déploiement Cloud — V1.1-E

## 1. Mettre à jour le serveur Render

Déployer le contenu du dossier `backend` de la V1.1-E, puis ajouter dans les
variables secrètes Render :

`SUPABASE_SERVICE_ROLE_KEY` = clé `service_role` du projet Supabase.

Cette valeur est strictement serveur. Elle ne doit jamais être copiée dans
`services/cloud_auth_service.py`, dans un fichier distribué aux commerciaux ou
dans une capture d'écran publique.

## 2. Redémarrer le service

Après le déploiement, vérifier que l'URL `/health` de l'API répond, puis ouvrir
Form@Prospect avec le compte administrateur déjà validé en V1.1-D.

## 3. Recette rapide

1. Ouvrir « Compte et utilisateurs ».
2. Inviter une adresse e-mail de test avec le rôle Commercial.
3. Vérifier la réception de l'invitation Supabase.
4. Modifier le rôle en Manager.
5. Désactiver le compte et vérifier que son prochain contrôle de session est
   refusé.
6. Réactiver le compte et envoyer un lien de réinitialisation.
7. Vérifier que les actions apparaissent dans le journal Cloud.

## Retour arrière

Le paquet V1.1-E ne transforme aucune donnée métier. En cas de retour à la
V1.1-D, restaurer les fichiers applicatifs V1.1-D et redéployer son dossier
`backend`. Les comptes déjà invités restent dans Supabase et peuvent être
désactivés depuis le tableau de bord Supabase.

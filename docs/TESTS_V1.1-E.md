# Tests V1.1-E

Date d'exécution : 21 juillet 2026

Commande : `python -m pytest -q backend/tests tests`

Résultat : **48 tests réussis**.

Couverture spécifique V1.1-E :

- lecture des utilisateurs limitée à l'organisation active ;
- invitation d'un collaborateur et création de son adhésion ;
- refus de désactiver le dernier administrateur actif ;
- changement de rôle et désactivation ;
- envoi sécurisé de la réinitialisation ;
- création et lecture des traces d'audit ;
- présence du jeton utilisateur et de l'identifiant d'organisation dans les
  appels de l'application Windows ;
- non-régression des 46 tests Cloud et métier préexistants.

Un avertissement de dépréciation provenant de l'outil de test Starlette a été
observé ; il n'affecte ni le résultat ni l'exécution de l'application.

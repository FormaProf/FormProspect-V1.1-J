# Rapport de tests — V1.1-E.1

Date : 29 juillet 2026

## Tests ciblés
Commande :
`pytest -q tests/test_v11e1_cloud_deployment_workflow.py tests/test_deployment_options.py tests/test_deployment_foundation.py`

Résultat : **9 réussis, 0 échec**.

Scénarios validés :
- import avant activation du mode Cloud ;
- absence de bascule en cas d'import en échec ;
- synchronisation d'un projet Cloud existant sans recréation ;
- lecture du contrat backend actuel ;
- compatibilité des options de déploiement ;
- fondations du moteur de lots.

## Non-régression du dossier `tests`
Résultat : **59 réussis, 1 échec**, hors test UI nécessitant PySide6.

L'échec restant concerne `test_cloud_lot4_integration.py::test_cloud_prospect_service_adapts_api_payload_to_existing_table` : le test ne configure aucun projet actif alors que le `DataSourceResolver` actuel l'exige. Cet échec n'est pas causé par les fichiers de la V1.1-E.1 et existait dans le périmètre audité.

## Suite complète non exécutable dans cet environnement
La collecte globale inclut plusieurs copies historiques de backend et échoue sur :
- import Python `backend` non configuré depuis la racine principale ;
- absence de PySide6 dans l'environnement Linux de test ;
- duplication de tests dans les dossiers de sauvegarde et de staging.

## Validation syntaxique
Les fichiers modifiés ont passé `py_compile` avec succès.

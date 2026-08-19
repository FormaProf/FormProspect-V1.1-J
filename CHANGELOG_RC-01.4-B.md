# Changelog — RC-01.4-B

## Ajouts

- `DeploymentReader`, contrat générique de lecture locale ;
- `ProspectDeploymentReader`, adaptateur du moteur vers `ProspectRepository` ;
- `ProspectRepository.iterate_deployment_batches()` ;
- sélection complète des champs nécessaires au futur mapper Cloud ;
- lecture par lots configurables ;
- prise en charge de `start_offset` pour préparer la reprise.

## Architecture

```text
DeploymentEngine
    -> ProspectDeploymentReader
        -> ProspectRepository
            -> SQLite
```

Le moteur ne contient aucune requête SQL.

## Comportement volontaire

Aucun prospect n'est encore envoyé au Cloud.

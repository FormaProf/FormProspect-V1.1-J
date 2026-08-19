# Correctif RC-01.4-B

Ce correctif restaure intégralement `repositories/prospect_repository.py`
dans sa version d'origine et conserve la lecture paginée dans le lecteur de
déploiement.

## Installation

Fermer Form@Prospect puis remplacer :

- `repositories/prospect_repository.py`
- `services/deployment/readers/prospect_reader.py`

Relancer ensuite le logiciel et tester l'ouverture des fiches prospects et clients.

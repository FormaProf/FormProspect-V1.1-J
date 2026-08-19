# Installation — Form@Prospect V1.1-H Lot 4.1

1. Fermer Form@Prospect et tous les terminaux ouverts dans son dossier.
2. Faire une copie de sauvegarde du dossier actuel `Form@Prospect`.
3. Décompresser l'archive corrective.
4. Copier le contenu du dossier `Form@Prospect` de l'archive dans le dossier existant.
5. Accepter le remplacement des fichiers.
6. Ouvrir un terminal dans la racine du projet.

Validation desktop :

```powershell
python -m pytest tests -q
```

Résultat attendu :

```text
35 passed
```

Validation backend :

```powershell
python -m pytest backend\tests -q
```

Résultat attendu :

```text
32 passed
```

Aucune nouvelle migration Alembic n'est nécessaire pour ce correctif.

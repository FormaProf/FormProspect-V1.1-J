# Installation — V1.1-F2 Lot 3

1. Fermer le serveur backend s'il est lancé.
2. Décompresser le correctif à la racine du projet `formaprospect-cloud` et accepter le remplacement des fichiers.
3. Ouvrir PowerShell à la racine du projet.
4. Exécuter :

```powershell
python -m alembic -c backend\alembic.ini upgrade head
python -m pytest backend\tests -q
```

Résultat attendu :

```text
32 passed
```

La dernière migration doit être : `0005_v11f2_lot3`.

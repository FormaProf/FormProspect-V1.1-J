# Installation — V1.1-G Lot 4

## 1. Sauvegarde
Dupliquez intégralement votre dossier historique `Form@Prospect` avant tout remplacement.

## 2. Installation du correctif
Copiez le contenu du dossier `Form@Prospect` du correctif à la racine du projet Cloud historique, puis acceptez le remplacement des fichiers.

## 3. Variables Cloud
Les valeurs historiques restent utilisées par défaut. Pour imposer une autre API dans PowerShell :

```powershell
$env:FORMAPROSPECT_API_BASE_URL="https://votre-service.onrender.com/api/v1"
$env:FORMAPROSPECT_SUPABASE_URL="https://votre-projet.supabase.co"
$env:FORMAPROSPECT_SUPABASE_PUBLISHABLE_KEY="votre-cle-publique"
```

Ne placez jamais la clé `service_role` Supabase dans l'application desktop.

## 4. Backend
Depuis la racine du projet fusionné :

```powershell
python -m alembic -c backend\alembic.ini upgrade head
python -m pytest backend\tests -q
python -m pytest tests -q
```

Résultat de référence de la livraison : **66 tests réussis** (32 backend + 34 desktop/intégration).

## 5. Reconstruction Windows

```powershell
build_release.bat
```

L'exécutable sera généré dans :

```text
release\Form@Prospect\Form@Prospect.exe
```

## 6. Recette visuelle
1. Se connecter avec un administrateur.
2. Ouvrir CRM et vérifier la liste Cloud.
3. Ouvrir une fiche prospect.
4. Ajouter une note.
5. Modifier priorité et prochaine action.
6. Déplacer le prospect dans le Kanban.
7. Se connecter avec un commercial et vérifier qu'il ne voit que ses prospects.

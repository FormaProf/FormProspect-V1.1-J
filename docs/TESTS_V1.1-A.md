# Form@Prospect — Rapport de tests V1.1-A

Date de recette : 20 juillet 2026

## Résultat

**15 tests backend exécutés — 15 réussis — 0 échec.**

## Couverture fonctionnelle

1. Endpoint de santé public.
2. Vérification de disponibilité de la base.
3. Rejet d'une requête sans JWT.
4. Rejet d'un JWT expiré.
5. Rejet d'un identifiant d'organisation invalide.
6. Interdiction d'entrer dans une autre organisation.
7. Blocage d'une adhésion désactivée.
8. Blocage d'un profil désactivé.
9. Permissions administrateur calculées côté serveur.
10. Écriture d'une trace d'audit avec utilisateur, organisation et appareil.
11. Administrateur autorisé sur toutes les permissions.
12. Commercial limité à ses données affectées.
13. Formateur limité aux permissions initiales minimales.
14. Refus de SQLite ou d'une configuration Supabase incomplète en production.
15. Refus d'un secret JWT de test en production.

## Contrôles complémentaires

- Migration Alembic appliquée jusqu'à `0001_v11a (head)` sur une base vierge.
- Compilation Python de `backend`, `core`, `repositories`, `services`, `ui`,
  `modules`, `workers` et `app.py` sans erreur.
- Vérification que les écrans et services locaux existants ne sont pas modifiés.

## Commandes de recette

```bash
pytest backend/tests -q
alembic -c backend/alembic.ini upgrade head
python -m compileall -q backend core repositories services ui modules workers app.py
```

La validation RLS sur une instance PostgreSQL/Supabase réelle sera répétée lors
de la configuration de l'environnement de préproduction, car SQLite ne sait pas
exécuter les politiques PostgreSQL.


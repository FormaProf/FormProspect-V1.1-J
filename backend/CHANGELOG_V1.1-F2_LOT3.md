# Form@Prospect Cloud — V1.1-F2 Lot 3

## Fonctionnalités livrées

- Pipeline commercial standard à 8 étapes : Nouveau, À contacter, Contacté, RDV planifié, Proposition envoyée, Négociation, Gagné et Perdu.
- Changement d'étape avec historique horodaté, auteur et note.
- Activités commerciales : appel, e-mail, rendez-vous, tâche et note.
- Planification, priorité, affectation, résultat et clôture des activités.
- Liste des activités à venir et filtre des relances en retard.
- Isolation des données par organisation et respect des droits Admin, Manager et Commercial.
- Audit des changements d'étape et des activités.
- Migration Alembic `0005_v11f2_lot3`.

## API ajoutées

- `GET /api/v1/pipeline/stages`
- `POST /api/v1/prospects/{id}/stage`
- `GET /api/v1/prospects/{id}/stage-history`
- `POST /api/v1/prospects/{id}/activities`
- `GET /api/v1/prospects/{id}/activities`
- `PATCH /api/v1/activities/{id}`
- `POST /api/v1/activities/{id}/complete`
- `GET /api/v1/activities/due`

## Validation

- Suite complète : **32 tests réussis**.

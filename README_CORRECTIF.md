# Correctif ouverture de la fiche prospect

## Cause

Le tableau convertissait systématiquement l'identifiant du prospect en entier
lors du double-clic. Cette conversion fonctionne pour SQLite, mais échoue pour
les UUID utilisés dans le Cloud.

## Installation

Fermer Form@Prospect puis remplacer :

`ui/widgets/crm/prospects_table.py`

Relancer ensuite le logiciel et tester le double-clic sur un prospect.

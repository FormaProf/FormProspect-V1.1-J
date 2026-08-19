# Form@Prospect — Document Engine V1.0.1

## Correctif

Le modèle officiel du programme de formation ne contient plus les dates « 25 et 26 juin 2026 » écrites en dur dans l'encadré bleu de la première page.

Les éléments suivants sont maintenant alimentés depuis le dossier formation à chaque génération :

- durée : `{{FORMATION_DUREE}}` ;
- horaires : `{{HORAIRES}}` ;
- dates : `{{FORMATION_DATES}}` ;
- modalité : `{{FORMATION_MODALITE}}`.

## Vérification effectuée

Test de fusion avec une session programmée les 23 et 24 juillet 2026 :

- 3 occurrences des nouvelles dates dans le document généré ;
- 0 occurrence des anciennes dates ;
- 0 balise non remplacée parmi les quatre variables corrigées.

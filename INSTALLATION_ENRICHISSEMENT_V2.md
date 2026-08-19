# Form@Prospect — Correctif Enrichissement V2

## Installation DIRECT
1. Fermer Form@Prospect.
2. Faire une copie de sauvegarde du dossier actuel `Form@Prospect`.
3. Décompresser ce ZIP.
4. Copier le dossier `Form@Prospect` obtenu dans :
   `C:\Users\Nacim\Desktop\MAJ Form@Prospect\FormProspect_V1.1-D_TEST\`
5. Accepter la fusion et le remplacement des fichiers.
6. Relancer Form@Prospect depuis VS Code pour le premier test.

## Ce que change ce lot
- identité de référence : entreprise + SIRET + SIREN + adresse + CP + ville + NAF ;
- Google Maps ne valide plus automatiquement le premier résultat trouvé ;
- PagesJaunes est utilisé en fallback ou en complément si Google Maps est incomplet ;
- résultats soumis à un score de correspondance avant écriture ;
- aucun résultat fiable = aucune donnée injectée ;
- plusieurs téléphones sont fusionnés et dédoublonnés ;
- les 06/07 sont affichés avant les fixes ;
- le champ téléphone de la fiche prospect devient multi-lignes ;
- correction robuste de l'inversion X/Twitter / YouTube entre providers local et Cloud.

## Premier test
Ne relance pas les 999 prospects immédiatement.
Teste 5 à 10 fiches, dont ENTREPRISE GALAND-CHEVALIER / SIRET 01565013800025.
Le résultat Krys Audition doit être rejeté.

## Important
Les fiches déjà marquées `Enrichi` ne sont pas retraitées automatiquement.
Après validation du V2 sur quelques prospects, faire une remise à zéro contrôlée des anciennes données avant de relancer les 999.

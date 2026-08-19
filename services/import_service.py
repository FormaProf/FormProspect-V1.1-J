import re
import sqlite3
from core.sqlite_utils import connect_database
import unicodedata

import pandas as pd

from core.crm import PIPELINE_DEFAULT, PRIORITE_DEFAULT, ACTION_DEFAULT
from core.database import init_database


class ImportService:
    def _normaliser_nom_colonne(self, nom):
        """
        Normalise un nom de colonne Excel afin de reconnaître les colonnes même si :
        - les accents changent ;
        - les majuscules/minuscules changent ;
        - il y a des espaces, tirets, underscores ou caractères spéciaux ;
        - la source utilise les noms SIRENE officiels ou des noms simplifiés.
        """
        texte = str(nom).strip().lower()
        texte = unicodedata.normalize("NFD", texte)
        texte = "".join(
            caractere
            for caractere in texte
            if unicodedata.category(caractere) != "Mn"
        )
        texte = re.sub(r"[^a-z0-9]", "", texte)
        return texte

    def _normaliser_colonnes(self, df):
        """
        Retourne un dictionnaire {nom_colonne_normalise: nom_colonne_reel}.
        """
        colonnes = {}
        for colonne in df.columns:
            colonnes[self._normaliser_nom_colonne(colonne)] = colonne
        return colonnes

    def _valeur(self, row, colonnes, noms_possibles, valeur_defaut=""):
        """
        Récupère la première valeur NON VIDE trouvée parmi les noms possibles.

        Important :
        auparavant, si une colonne existait mais que sa cellule était vide,
        la recherche s'arrêtait immédiatement. Cela empêchait les colonnes
        alternatives d'être utilisées.
        """
        for nom in noms_possibles:
            cle = self._normaliser_nom_colonne(nom)
            if cle not in colonnes:
                continue

            valeur = row.get(colonnes[cle], valeur_defaut)
            if valeur is None:
                continue

            valeur = str(valeur).strip()
            if not valeur or valeur.lower() in ["nan", "none", "null"]:
                continue

            return valeur

        return valeur_defaut

    def _nom_entreprise(self, row, colonnes):
        """
        Construit le nom utilisable par l'enrichissement.

        Priorité :
        1. dénomination / raison sociale ;
        2. nom commercial ou nom d'entreprise générique ;
        3. prénom + nom de l'unité légale pour les entrepreneurs individuels.
        """
        denomination = self._valeur(
            row,
            colonnes,
            [
                "denominationUniteLegale",
                "denomination unite legale",
                "dénomination unité légale",
                "denomination",
                "dénomination",
                "raison sociale",
                "raison_sociale",
                "entreprise",
                "nom entreprise",
                "nom_entreprise",
                "nom complet",
                "nom_complet",
            ],
        )
        if denomination:
            return denomination

        nom = self._valeur(
            row,
            colonnes,
            [
                "nomUniteLegale",
                "nom unite legale",
                "nom unité légale",
                "nomUsageUniteLegale",
                "nom usage unite legale",
                "nom d'usage unite legale",
                "nom",
            ],
        )

        prenom = self._valeur(
            row,
            colonnes,
            [
                "prenom1UniteLegale",
                "prenom1 unite legale",
                "prénom1 unité légale",
                "prenom unite legale",
                "prénom unité légale",
                "prenom",
                "prénom",
            ],
        )

        return " ".join(
            part for part in (prenom, nom)
            if str(part or "").strip()
        ).strip()

    def importer_excel_vers_sqlite(self, fichier_excel, database_path):
        init_database(database_path)

        df = pd.read_excel(fichier_excel, dtype=str).fillna("")
        colonnes = self._normaliser_colonnes(df)

        conn = connect_database(database_path)
        cur = conn.cursor()

        total = 0

        for _, row in df.iterrows():
            entreprise = self._nom_entreprise(row, colonnes)

            siret = self._valeur(row, colonnes, [
                "siret",
                "numero siret",
                "numéro siret",
                "siret etablissement",
                "siret établissement",
            ])

            siren = self._valeur(row, colonnes, [
                "siren",
                "numero siren",
                "numéro siren",
                "siren unite legale",
                "siren unité légale",
            ])

            ville = self._valeur(row, colonnes, [
                "ville",
                "commune",
                "localite",
                "localité",
                "nom commune",
                "nom_commune",
                "libelle commune",
                "libellé commune",
                "libelle_commune",
                "commune etablissement",
                "commune établissement",
                "commune_etablissement",
                "ville etablissement",
                "ville établissement",
                "ville_etablissement",
                "libelleCommuneEtablissement",
                "libellé commune établissement",
                "libelle commune etablissement",
                "libellé de la commune de l'établissement",
                "libelle de la commune de l'etablissement",
                "libelle_commune_etablissement",
                "nomCommuneEtablissement",
                "nom commune etablissement",
                "nom commune établissement",
                "nom_commune_etablissement",
            ])

            code_postal = self._valeur(row, colonnes, [
                "codePostalEtablissement",
                "code postal etablissement",
                "code postal établissement",
                "code_postal_etablissement",
                "code postal",
                "code_postal",
                "cp",
                "postal code",
            ])

            code_naf = self._valeur(row, colonnes, [
                "activitePrincipaleEtablissement",
                "activité principale établissement",
                "activite principale etablissement",
                "activite_principale_etablissement",
                "code naf",
                "code_naf",
                "naf",
                "ape",
                "code ape",
                "code_ape",
            ])

            numero_voie = self._valeur(row, colonnes, [
                "numeroVoieEtablissement",
                "numero voie etablissement",
                "numéro voie établissement",
                "numero voie",
                "numéro voie",
            ])

            type_voie = self._valeur(row, colonnes, [
                "typeVoieEtablissement",
                "type voie etablissement",
                "type voie établissement",
                "type voie",
            ])

            libelle_voie = self._valeur(row, colonnes, [
                "libelleVoieEtablissement",
                "libellé voie établissement",
                "libelle voie etablissement",
                "libelle voie",
                "libellé voie",
                "adresse",
                "adresse etablissement",
                "adresse établissement",
            ])

            adresse = " ".join([
                numero_voie,
                type_voie,
                libelle_voie,
            ]).strip()

            telephone = self._valeur(row, colonnes, [
                "telephone",
                "téléphone",
                "tel",
                "mobile",
                "portable",
                "numero telephone",
                "numéro téléphone",
            ])

            site_web = self._valeur(row, colonnes, [
                "site_web",
                "site web",
                "website",
                "url",
                "site",
            ])

            email = self._valeur(row, colonnes, [
                "email",
                "e-mail",
                "mail",
                "adresse email",
                "adresse_email",
            ])

            cur.execute("""
                INSERT INTO prospects (
                    entreprise, siret, siren, adresse, code_postal, ville, code_naf,
                    telephone, site_web, email, facebook, linkedin, instagram, youtube,
                    statut_enrichissement, date_collecte, pipeline, priorite,
                    prochaine_action, date_prochaine_action, commercial_assigne
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', '', '', 'Importé', '', ?, ?, ?, '', '')
            """, (
                entreprise,
                siret,
                siren,
                adresse,
                code_postal,
                ville,
                code_naf,
                telephone,
                site_web,
                email,
                PIPELINE_DEFAULT,
                PRIORITE_DEFAULT,
                ACTION_DEFAULT,
            ))

            total += 1

        conn.commit()
        conn.close()

        return total

    def reparer_noms_entreprises_depuis_excel(self, fichier_excel, database_path):
        """
        Répare UNIQUEMENT les prospects déjà présents dont entreprise est vide.

        La correspondance se fait d'abord par SIRET, puis par SIREN si le SIRET
        n'est pas disponible. Aucune ligne n'est insérée : cette méthode ne peut
        donc pas créer de doublons.

        Retour :
            {
                "lignes_excel": ...,
                "repares": ...,
                "deja_renseignes": ...,
                "sans_identifiant": ...,
                "sans_nom_exploitable": ...,
                "introuvables": ...
            }
        """
        init_database(database_path)

        df = pd.read_excel(fichier_excel, dtype=str).fillna("")
        colonnes = self._normaliser_colonnes(df)

        conn = connect_database(database_path)
        cur = conn.cursor()

        stats = {
            "lignes_excel": 0,
            "repares": 0,
            "deja_renseignes": 0,
            "sans_identifiant": 0,
            "sans_nom_exploitable": 0,
            "introuvables": 0,
        }

        try:
            for _, row in df.iterrows():
                stats["lignes_excel"] += 1

                entreprise = self._nom_entreprise(row, colonnes)
                if not entreprise:
                    stats["sans_nom_exploitable"] += 1
                    continue

                siret = self._valeur(row, colonnes, [
                    "siret",
                    "numero siret",
                    "numéro siret",
                    "siret etablissement",
                    "siret établissement",
                ])
                siren = self._valeur(row, colonnes, [
                    "siren",
                    "numero siren",
                    "numéro siren",
                    "siren unite legale",
                    "siren unité légale",
                ])

                prospect = None

                if siret:
                    cur.execute(
                        """
                        SELECT id, entreprise
                        FROM prospects
                        WHERE TRIM(COALESCE(siret, '')) = ?
                        ORDER BY id ASC
                        LIMIT 1
                        """,
                        (siret,),
                    )
                    prospect = cur.fetchone()

                if prospect is None and siren:
                    cur.execute(
                        """
                        SELECT id, entreprise
                        FROM prospects
                        WHERE TRIM(COALESCE(siren, '')) = ?
                        ORDER BY id ASC
                        LIMIT 1
                        """,
                        (siren,),
                    )
                    prospect = cur.fetchone()

                if not siret and not siren:
                    stats["sans_identifiant"] += 1
                    continue

                if prospect is None:
                    stats["introuvables"] += 1
                    continue

                prospect_id, nom_actuel = prospect
                if str(nom_actuel or "").strip():
                    stats["deja_renseignes"] += 1
                    continue

                cur.execute(
                    """
                    UPDATE prospects
                    SET entreprise = ?
                    WHERE id = ?
                      AND COALESCE(TRIM(entreprise), '') = ''
                    """,
                    (entreprise, prospect_id),
                )

                if cur.rowcount:
                    stats["repares"] += 1

            conn.commit()
            return stats
        finally:
            conn.close()

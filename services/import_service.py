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
        texte = "".join(caractere for caractere in texte if unicodedata.category(caractere) != "Mn")
        texte = re.sub(r"[^a-z0-9]", "", texte)
        return texte

    def _normaliser_colonnes(self, df):
        """
        Retourne un dictionnaire {nom_colonne_normalise: nom_colonne_reel}.
        Exemple : "Libellé commune établissement" devient "libellecommuneetablissement".
        """
        colonnes = {}
        for colonne in df.columns:
            colonnes[self._normaliser_nom_colonne(colonne)] = colonne
        return colonnes

    def _valeur(self, row, colonnes, noms_possibles, valeur_defaut=""):
        """
        Récupère une valeur dans une ligne Excel à partir d'une liste de noms possibles.
        La comparaison est volontairement très tolérante pour éviter les imports vides.
        """
        for nom in noms_possibles:
            cle = self._normaliser_nom_colonne(nom)
            if cle in colonnes:
                valeur = row.get(colonnes[cle], valeur_defaut)
                if valeur is None:
                    return valeur_defaut
                valeur = str(valeur).strip()
                if valeur.lower() in ["nan", "none", "null"]:
                    return valeur_defaut
                return valeur
        return valeur_defaut

    def importer_excel_vers_sqlite(self, fichier_excel, database_path):
        init_database(database_path)

        df = pd.read_excel(fichier_excel, dtype=str).fillna("")
        colonnes = self._normaliser_colonnes(df)

        conn = connect_database(database_path)
        cur = conn.cursor()

        total = 0

        for _, row in df.iterrows():
            entreprise = self._valeur(row, colonnes, [
                "denominationUniteLegale",
                "denomination unite legale",
                "dénomination unité légale",
                "denomination",
                "dénomination",
                "entreprise",
                "nom entreprise",
                "nom_entreprise",
                "raison sociale",
                "raison_sociale",
                "nom",
                "nom complet",
                "nom_complet",
            ])

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

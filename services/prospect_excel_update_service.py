from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import unicodedata

import pandas as pd


class ProspectExcelUpdateService:
    """
    Analyse en lecture seule un fichier Excel destiné à mettre à jour des
    prospects existants.

    Ce service ne connaît ni SQLite, ni Supabase, ni CloudAPIClient :
    il ne peut donc effectuer aucune écriture dans une base Form@Prospect.
    """

    SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm"}

    FIELD_ALIASES = {
        "siret": (
            "siret",
            "numero siret",
            "numéro siret",
            "siret etablissement",
            "siret établissement",
        ),
        "siren": (
            "siren",
            "numero siren",
            "numéro siren",
            "siren unite legale",
            "siren unité légale",
        ),
        "entreprise": (
            "entreprise",
            "nom entreprise",
            "nom_entreprise",
            "raison sociale",
            "raison_sociale",
            "denomination",
            "dénomination",
            "denomination unite legale",
            "dénomination unité légale",
            "denominationUniteLegale",
            "nom complet",
            "nom_complet",
        ),
        "telephone": (
            "telephone",
            "téléphone",
            "tel",
            "phone",
            "numero telephone",
            "numéro téléphone",
            "telephone fixe",
            "téléphone fixe",
            "tel fixe",
        ),
        "mobile": (
            "mobile",
            "portable",
            "telephone mobile",
            "téléphone mobile",
            "tel mobile",
            "numero mobile",
            "numéro mobile",
        ),
        "email": (
            "email",
            "e-mail",
            "mail",
            "adresse email",
            "adresse_email",
            "courriel",
        ),
        "site_web": (
            "site web",
            "site_web",
            "site internet",
            "site_internet",
            "website",
            "url",
            "site",
        ),
        "linkedin": (
            "linkedin",
            "linkedin url",
            "url linkedin",
            "linkedin_url",
        ),
        "facebook": (
            "facebook",
            "facebook url",
            "url facebook",
            "facebook_url",
        ),
        "instagram": (
            "instagram",
            "instagram url",
            "url instagram",
            "instagram_url",
        ),
        "youtube": (
            "youtube",
            "youtube url",
            "url youtube",
            "youtube_url",
        ),
        "adresse": (
            "adresse",
            "adresse etablissement",
            "adresse établissement",
            "adresse complete",
            "adresse complète",
        ),
        "code_postal": (
            "code postal",
            "code_postal",
            "cp",
            "postal code",
            "code postal etablissement",
            "code postal établissement",
            "codePostalEtablissement",
        ),
        "ville": (
            "ville",
            "commune",
            "localite",
            "localité",
            "nom commune",
            "nom_commune",
            "libelle commune",
            "libellé commune",
            "commune etablissement",
            "commune établissement",
            "libelleCommuneEtablissement",
        ),
        "code_naf": (
            "code naf",
            "code_naf",
            "naf",
            "ape",
            "code ape",
            "code_ape",
            "activitePrincipaleEtablissement",
            "activité principale établissement",
        ),
    }

    EXCLUDED_FIELD_ALIASES = {
        "fax": (
            "fax",
            "telecopie",
            "télécopie",
            "numero fax",
            "numéro fax",
        ),
    }

    # Ces champs peuvent légitimement apparaître plusieurs fois dans un fichier
    # (Téléphone 1, Téléphone 2, Email 1, etc.).
    MULTI_VALUE_FIELDS = {
        "telephone",
        "mobile",
        "email",
        "site_web",
        "linkedin",
        "facebook",
        "instagram",
        "youtube",
    }

    def analyser_fichier(self, fichier_excel) -> dict:
        """
        Lit et analyse un fichier Excel sans effectuer aucune écriture.

        Le résultat contient uniquement des statistiques et le mapping des
        colonnes. Les lignes du fichier ne sont pas conservées dans le résultat
        afin d'éviter de dupliquer en mémoire de très gros fichiers.
        """
        path = Path(fichier_excel)

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Fichier Excel introuvable : {path}")

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                "Format Excel non pris en charge. Utilisez un fichier .xlsx ou .xlsm."
            )

        df = pd.read_excel(path, dtype=str, keep_default_na=False).fillna("")

        mappings, excluded, ignored = self._detect_columns(df.columns)

        stats = {
            "fichier": str(path),
            "nom_fichier": path.name,
            "lignes_excel": int(len(df)),
            "lignes_exploitables": 0,
            "lignes_sans_identifiant": 0,
            "siret_valides": 0,
            "siret_invalides": 0,
            "siren_valides": 0,
            "siren_invalides": 0,
            "siren_deduits_du_siret": 0,
            "incoherences_identifiants": 0,
            "colonnes_reconnues": mappings,
            "colonnes_exclues": excluded,
            "colonnes_ignorees": ignored,
            "valeurs_detectees": self._count_values(df, mappings),
            "lecture_seule": True,
        }

        siret_columns = mappings.get("siret", [])
        siren_columns = mappings.get("siren", [])

        for _, row in df.iterrows():
            siret_info = self._identifier_from_row(
                row,
                siret_columns,
                expected_length=14,
            )
            siren_info = self._identifier_from_row(
                row,
                siren_columns,
                expected_length=9,
            )

            siret = siret_info["value"]
            siren = siren_info["value"]

            if siret_info["has_raw"]:
                if siret:
                    stats["siret_valides"] += 1
                else:
                    stats["siret_invalides"] += 1

            if siren_info["has_raw"]:
                if siren:
                    stats["siren_valides"] += 1
                else:
                    stats["siren_invalides"] += 1

            if not siren and siret:
                siren = siret[:9]
                stats["siren_deduits_du_siret"] += 1

            if siret and siren and siret[:9] != siren:
                stats["incoherences_identifiants"] += 1

            if siret or siren:
                stats["lignes_exploitables"] += 1
            else:
                stats["lignes_sans_identifiant"] += 1

        return stats


    @staticmethod
    def _normaliser_nom_colonne(nom) -> str:
        texte = str(nom or "").strip().lower()
        texte = unicodedata.normalize("NFD", texte)
        texte = "".join(
            caractere
            for caractere in texte
            if unicodedata.category(caractere) != "Mn"
        )
        return re.sub(r"[^a-z0-9]", "", texte)

    def _detect_columns(self, columns) -> tuple[dict, dict, list]:
        mappings = {field: [] for field in self.FIELD_ALIASES}
        excluded = {field: [] for field in self.EXCLUDED_FIELD_ALIASES}
        ignored = []

        normalized_aliases = {
            field: {
                self._normaliser_nom_colonne(alias)
                for alias in aliases
            }
            for field, aliases in self.FIELD_ALIASES.items()
        }
        normalized_excluded = {
            field: {
                self._normaliser_nom_colonne(alias)
                for alias in aliases
            }
            for field, aliases in self.EXCLUDED_FIELD_ALIASES.items()
        }

        for column in columns:
            source_name = str(column)
            normalized = self._normaliser_nom_colonne(source_name)

            excluded_field = self._match_field(
                normalized,
                normalized_excluded,
                allow_numbered=True,
            )
            if excluded_field:
                excluded[excluded_field].append(source_name)
                continue

            field = self._match_field(
                normalized,
                normalized_aliases,
                allow_numbered=True,
            )
            if field:
                if (
                    field not in self.MULTI_VALUE_FIELDS
                    and mappings[field]
                ):
                    # Pour les champs mono-valeur, on garde la première colonne
                    # comme référence et on laisse les doublons visibles comme
                    # colonnes ignorées afin qu'aucune ambiguïté ne soit masquée.
                    ignored.append(source_name)
                else:
                    mappings[field].append(source_name)
                continue

            ignored.append(source_name)

        mappings = {
            field: source_columns
            for field, source_columns in mappings.items()
            if source_columns
        }
        excluded = {
            field: source_columns
            for field, source_columns in excluded.items()
            if source_columns
        }

        return mappings, excluded, ignored

    def _match_field(
        self,
        normalized_column: str,
        aliases_by_field: dict[str, set[str]],
        *,
        allow_numbered: bool,
    ) -> str | None:
        for field, aliases in aliases_by_field.items():
            if normalized_column in aliases:
                return field

            if allow_numbered:
                for alias in aliases:
                    if normalized_column.startswith(alias):
                        suffix = normalized_column[len(alias):]
                        if suffix and suffix.isdigit():
                            return field

        return None

    @staticmethod
    def _count_values(df, mappings: dict) -> dict[str, int]:
        counts = {}

        for field, columns in mappings.items():
            total = 0
            for column in columns:
                series = df[column].map(
                    lambda value: str(value or "").strip()
                )
                total += int(
                    series.map(
                        lambda value: bool(value)
                        and value.lower() not in {"nan", "none", "null"}
                    ).sum()
                )
            counts[field] = total

        return counts

    def _identifier_from_row(
        self,
        row,
        columns,
        *,
        expected_length: int,
    ) -> dict:
        has_raw = False

        for column in columns:
            raw = row.get(column, "")
            text = str(raw or "").strip()

            if not text or text.lower() in {"nan", "none", "null"}:
                continue

            has_raw = True
            normalized = self._normaliser_identifiant(
                text,
                expected_length=expected_length,
            )

            if normalized:
                return {
                    "value": normalized,
                    "has_raw": True,
                }

        return {
            "value": "",
            "has_raw": has_raw,
        }

    @staticmethod
    def _normaliser_identifiant(
        value,
        *,
        expected_length: int,
    ) -> str:
        """
        Normalise un SIREN/SIRET lu depuis Excel.

        Accepte notamment :
        - "31035888200028"
        - "310 358 882 00028"
        - "31035888200028.0"
        - une écriture scientifique Excel lorsqu'elle représente exactement
          un entier de la longueur attendue.
        """
        text = str(value or "").strip()

        if not text:
            return ""

        no_spaces = re.sub(r"[\s\u00A0]", "", text)

        excel_decimal = re.fullmatch(r"(\d+)\.0+", no_spaces)
        if excel_decimal:
            digits = excel_decimal.group(1)
            return digits if len(digits) == expected_length else ""

        compact = re.sub(r"[\s\u00A0._-]", "", text)

        if compact.isdigit():
            return compact if len(compact) == expected_length else ""

        decimal_candidate = text.replace(",", ".").replace(" ", "")

        try:
            number = Decimal(decimal_candidate)
        except (InvalidOperation, ValueError):
            return ""

        if not number.is_finite():
            return ""

        integral = number.to_integral_value()

        if number != integral:
            return ""

        digits = format(integral, "f")

        if digits.startswith("+"):
            digits = digits[1:]

        if not digits.isdigit():
            return ""

        return digits if len(digits) == expected_length else ""

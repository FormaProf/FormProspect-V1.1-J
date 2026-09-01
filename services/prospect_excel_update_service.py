from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import sqlite3
import unicodedata

import pandas as pd


class ProspectExcelUpdateService:
    """
    Analyse en lecture seule un fichier Excel destiné à enrichir des
    prospects déjà existants.

    La comparaison SQLite est volontairement ouverte en lecture seule.
    Aucune méthode de ce lot ne crée, ne modifie ni ne supprime de prospect.
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


    DATABASE_FIELD_MAP = {
        "entreprise": "entreprise",
        "telephone": "telephone",
        "mobile": "telephone",
        "email": "email",
        "site_web": "site_web",
        "linkedin": "linkedin",
        "facebook": "facebook",
        "instagram": "instagram",
        "youtube": "youtube",
        "adresse": "adresse",
        "code_postal": "code_postal",
        "ville": "ville",
        "code_naf": "code_naf",
    }

    MERGE_FIELDS = {"telephone", "email"}

    def comparer_avec_sqlite(
        self,
        fichier_excel,
        database_path,
        *,
        apercu_limite: int = 100,
    ) -> dict:
        """
        Compare un fichier Excel avec des prospects SQLite existants.

        Sécurité du lot 2 :
        - la base est ouverte avec ``mode=ro`` ;
        - aucune création de prospect ;
        - aucune modification ni suppression ;
        - la correspondance se fait UNIQUEMENT par SIRET exact ;
        - le SIREN ne sert jamais de clé de secours.

        Les contacts multivalués sont comparés de façon additive : une valeur
        déjà présente est ignorée, une nouvelle valeur est proposée à la
        fusion. Les champs mono-valeur ne sont jamais écrasés : s'ils sont
        vides ils peuvent être complétés, sinon une valeur différente est
        seulement signalée comme conflit à vérifier.
        """
        path = Path(fichier_excel)
        db_path = Path(database_path)

        if not db_path.exists() or not db_path.is_file():
            raise FileNotFoundError(f"Base SQLite introuvable : {db_path}")

        if apercu_limite < 0:
            raise ValueError("apercu_limite doit être supérieur ou égal à 0.")

        analyse = self.analyser_fichier(path)
        df = pd.read_excel(path, dtype=str, keep_default_na=False).fillna("")
        mappings = analyse["colonnes_reconnues"]

        parsed_rows = []
        target_sirets = set()

        for excel_index, (_, row) in enumerate(df.iterrows(), start=2):
            siret_info = self._identifier_from_row(
                row,
                mappings.get("siret", []),
                expected_length=14,
            )
            siren_info = self._identifier_from_row(
                row,
                mappings.get("siren", []),
                expected_length=9,
            )
            siret = siret_info["value"]
            siren = siren_info["value"]

            incoherent = bool(siret and siren and siret[:9] != siren)
            payload = self._extract_update_values(row, mappings)

            parsed_rows.append(
                {
                    "ligne_excel": excel_index,
                    "siret": siret,
                    "siret_present_mais_invalide": bool(
                        siret_info["has_raw"] and not siret
                    ),
                    "siren": siren,
                    "incoherent": incoherent,
                    "payload": payload,
                }
            )

            if siret and not incoherent:
                target_sirets.add(siret)

        conn = self._open_sqlite_read_only(db_path)
        try:
            available_columns = self._prospect_columns(conn)
            if not available_columns:
                raise ValueError(
                    "La table prospects est absente ou illisible dans la base sélectionnée."
                )
            if "siret" not in available_columns:
                raise ValueError(
                    "La table prospects ne contient pas de colonne SIRET."
                )

            by_siret = self._load_matching_prospects_by_siret(
                conn,
                available_columns,
                target_sirets,
            )
        finally:
            conn.close()

        potential = {field: 0 for field in self.DATABASE_FIELD_MAP}
        stats = {
            "fichier": str(path),
            "base_sqlite": str(db_path),
            "lecture_seule": True,
            "mode_base": "sqlite_ro",
            "cle_correspondance": "siret_exact",
            "creation_prospects": False,
            "suppression_donnees": False,
            "lignes_excel": int(len(df)),
            "lignes_comparees": 0,
            "correspondances_siret": 0,
            "introuvables": 0,
            "ambigus_siret": 0,
            "sans_siret": 0,
            "siret_invalides": 0,
            "ignores_incoherents": 0,
            "lignes_sans_changement": 0,
            "champs_vides_a_completer": 0,
            "valeurs_a_fusionner": 0,
            "conflits_a_verifier": 0,
            "modifications_potentielles": potential,
            "colonnes_base_disponibles": sorted(available_columns),
            "apercu": [],
        }

        for parsed in parsed_rows:
            if parsed["incoherent"]:
                stats["ignores_incoherents"] += 1
                continue

            siret = parsed["siret"]
            if not siret:
                if parsed["siret_present_mais_invalide"]:
                    stats["siret_invalides"] += 1
                else:
                    stats["sans_siret"] += 1
                continue

            exact = by_siret.get(siret, [])
            if len(exact) > 1:
                stats["ambigus_siret"] += 1
                continue
            if not exact:
                stats["introuvables"] += 1
                continue

            prospect = exact[0]
            stats["lignes_comparees"] += 1
            stats["correspondances_siret"] += 1

            differences = self._compare_payload_with_prospect(
                parsed["payload"],
                prospect,
                available_columns,
            )

            if not differences:
                stats["lignes_sans_changement"] += 1
                continue

            for diff in differences:
                source_field = diff["champ_source"]
                if source_field in potential:
                    potential[source_field] += diff["nombre_valeurs"]
                if diff["action"] == "completer":
                    stats["champs_vides_a_completer"] += 1
                elif diff["action"] == "fusionner":
                    stats["valeurs_a_fusionner"] += diff["nombre_valeurs"]
                elif diff["action"] == "verifier":
                    stats["conflits_a_verifier"] += 1

            if len(stats["apercu"]) < apercu_limite:
                stats["apercu"].append(
                    {
                        "ligne_excel": parsed["ligne_excel"],
                        "correspondance": "siret",
                        "prospect_id": prospect.get("id"),
                        "siret": prospect.get("siret", ""),
                        "siren": prospect.get("siren", ""),
                        "entreprise": prospect.get("entreprise", ""),
                        "differences": differences,
                    }
                )

        return stats

    @staticmethod
    def _open_sqlite_read_only(database_path: Path) -> sqlite3.Connection:
        uri = database_path.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _prospect_columns(conn: sqlite3.Connection) -> set[str]:
        rows = conn.execute("PRAGMA table_info(prospects)").fetchall()
        return {str(row[1]) for row in rows}

    def _load_matching_prospects_by_siret(
        self,
        conn: sqlite3.Connection,
        available_columns: set[str],
        target_sirets: set[str],
    ) -> dict[str, list[dict]]:
        """Charge uniquement les prospects dont le SIRET est ciblé."""
        wanted = {"id", "siret", "siren"}
        wanted.update(self.DATABASE_FIELD_MAP.values())
        selected = [
            column
            for column in wanted
            if column in available_columns
        ]
        if not selected:
            return {}

        quoted = ", ".join(f'"{column}"' for column in selected)
        cursor = conn.execute(f"SELECT {quoted} FROM prospects")

        by_siret: dict[str, list[dict]] = {}

        while True:
            batch = cursor.fetchmany(1000)
            if not batch:
                break

            for row in batch:
                prospect = {column: row[column] for column in selected}
                siret = self._normaliser_identifiant(
                    prospect.get("siret", ""),
                    expected_length=14,
                )
                if siret and siret in target_sirets:
                    by_siret.setdefault(siret, []).append(prospect)

        return by_siret

    def _extract_update_values(self, row, mappings: dict) -> dict[str, list[str]]:
        values = {}
        for field, columns in mappings.items():
            if field in {"siret", "siren"}:
                continue
            row_values = self._values_from_row(row, columns)
            if row_values:
                values[field] = row_values
        return values

    @staticmethod
    def _values_from_row(row, columns) -> list[str]:
        result = []
        seen = set()
        for column in columns:
            value = str(row.get(column, "") or "").strip()
            if not value or value.lower() in {"nan", "none", "null"}:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    def _compare_payload_with_prospect(
        self,
        payload: dict[str, list[str]],
        prospect: dict,
        available_columns: set[str],
    ) -> list[dict]:
        differences = []
        staged_keys: dict[str, set[str]] = {}

        # Le mobile est stocké dans ``telephone`` dans le schéma actuel. Les
        # statistiques conservent cependant son champ source pour distinguer les
        # apports du fichier Excel. ``staged_keys`` évite de compter deux fois
        # le même contact s'il apparaît dans plusieurs colonnes du fichier.
        for source_field, incoming_values in payload.items():
            destination = self.DATABASE_FIELD_MAP.get(source_field)
            if not destination or destination not in available_columns:
                continue

            current = str(prospect.get(destination, "") or "").strip()

            if destination in self.MERGE_FIELDS:
                if destination not in staged_keys:
                    current_values = self._split_multi_value(current, destination)
                    staged_keys[destination] = {
                        self._normaliser_contact_value(value, destination)
                        for value in current_values
                        if self._normaliser_contact_value(value, destination)
                    }

                current_keys = staged_keys[destination]
                expanded_incoming = []
                for value in incoming_values:
                    expanded_incoming.extend(
                        self._split_multi_value(value, destination)
                    )

                additions = []
                for value in expanded_incoming:
                    normalized = self._normaliser_contact_value(value, destination)
                    if normalized and normalized not in current_keys:
                        additions.append(value)
                        current_keys.add(normalized)

                if not additions:
                    continue

                differences.append(
                    {
                        "champ_source": source_field,
                        "champ_destination": destination,
                        "action": "fusionner" if current else "completer",
                        "valeur_actuelle": current,
                        "valeurs_excel": additions,
                        "nombre_valeurs": len(additions),
                    }
                )
                continue

            incoming = incoming_values[0]
            if not current:
                differences.append(
                    {
                        "champ_source": source_field,
                        "champ_destination": destination,
                        "action": "completer",
                        "valeur_actuelle": "",
                        "valeurs_excel": [incoming],
                        "nombre_valeurs": 1,
                    }
                )
                continue

            if self._normaliser_scalar(current, destination) != self._normaliser_scalar(
                incoming,
                destination,
            ):
                differences.append(
                    {
                        "champ_source": source_field,
                        "champ_destination": destination,
                        "action": "verifier",
                        "valeur_actuelle": current,
                        "valeurs_excel": [incoming],
                        "nombre_valeurs": 1,
                    }
                )

        return differences

    @staticmethod
    def _split_multi_value(value: str, field: str) -> list[str]:
        if not value:
            return []
        # Les séparateurs historiques les plus fréquents dans Form@Prospect.
        parts = re.split(r"[\n;|]+|\s+/\s+", value)
        if field in {"telephone", "email"}:
            expanded = []
            for part in parts:
                expanded.extend(re.split(r"\s*,\s*", part))
            parts = expanded
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _normaliser_contact_value(value: str, field: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if field == "telephone":
            digits = re.sub(r"\D", "", text)
            if digits.startswith("0033") and len(digits) == 13:
                digits = "0" + digits[4:]
            elif digits.startswith("33") and len(digits) == 11:
                digits = "0" + digits[2:]
            return digits
        if field == "email":
            return text.casefold()
        return text.casefold()

    @staticmethod
    def _normaliser_scalar(value: str, field: str) -> str:
        text = " ".join(str(value or "").strip().split()).casefold()
        if field in {"site_web", "linkedin", "facebook", "instagram", "youtube"}:
            text = re.sub(r"^https?://", "", text)
            text = re.sub(r"^www\.", "", text)
            text = text.rstrip("/")
        return text

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

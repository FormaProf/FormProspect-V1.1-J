from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import date

from core.sqlite_utils import connect_database
from modules.email_finder import EmailFinder
from modules.entreprise_api import EntrepriseApiClient
from modules.google_maps import GoogleMapsFinder
from modules.pages_jaunes import PagesJaunesFinder
from modules.social_finder import SocialFinder
from modules.web_fallback import WebFallbackFinder
from services.scoring_service import ScoringService


class EnrichmentService:
    ENRICHED_STATUS = "Enrichi"
    NO_RELIABLE_RESULT_STATUS = "Aucun résultat fiable"
    ERROR_STATUS = "Erreur enrichissement"

    MODE_PENDING = "pending"
    MODE_SELECTED = "selected"
    MODE_ALL = "all"
    VALID_MODES = {MODE_PENDING, MODE_SELECTED, MODE_ALL}

    def __init__(self):
        self.google = GoogleMapsFinder()
        self.pages_jaunes = PagesJaunesFinder()
        self.email_finder = EmailFinder()
        self.social_finder = SocialFinder()
        self.entreprise_api = EntrepriseApiClient()
        self.web_fallback = WebFallbackFinder()

    @staticmethod
    def _ensure_social_columns(conn):
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(prospects)")
        columns = {row[1] for row in cur.fetchall()}

        for column in ("twitter", "social_other_urls", "mobile", "noms_recherche"):
            if column not in columns:
                cur.execute(
                    f"ALTER TABLE prospects ADD COLUMN {column} TEXT DEFAULT ''"
                )
        conn.commit()

    @staticmethod
    def _normaliser_ids(prospect_ids):
        if prospect_ids is None:
            return []
        values = []
        seen = set()
        for value in prospect_ids:
            try:
                normalized = int(value)
            except (TypeError, ValueError):
                continue
            if normalized <= 0 or normalized in seen:
                continue
            seen.add(normalized)
            values.append(normalized)
        return values

    def _sanitize_existing_contacts(self, conn, prospect_ids=None):
        """Nettoie uniquement les faux emails techniques certains.

        Pour un enrichissement ciblé, le nettoyage est limité aux prospects
        sélectionnés afin qu'une opération locale ne modifie pas d'autres
        fiches du projet.
        """
        cur = conn.cursor()
        ids = self._normaliser_ids(prospect_ids)
        query = """
            SELECT id, email
            FROM prospects
            WHERE COALESCE(TRIM(email),'') != ''
        """
        params = []
        if prospect_ids is not None:
            if not ids:
                return 0
            placeholders = ",".join("?" for _ in ids)
            query += f" AND id IN ({placeholders})"
            params.extend(ids)
        cur.execute(query, params)

        cleaned = 0
        for prospect_id, email in cur.fetchall():
            try:
                technical = self.email_finder._is_technical(email)
            except Exception:
                technical = False
            if technical:
                cur.execute(
                    "UPDATE prospects SET email = '' WHERE id = ?",
                    (prospect_id,),
                )
                cleaned += 1
        if cleaned:
            conn.commit()
        return cleaned

    @classmethod
    def _valider_mode(cls, mode):
        mode = str(mode or cls.MODE_PENDING).strip().lower()
        if mode not in cls.VALID_MODES:
            raise ValueError(f"Mode d'enrichissement invalide : {mode}")
        return mode

    def compter_cible(self, database_path, *, mode=MODE_PENDING, prospect_ids=None):
        mode = self._valider_mode(mode)
        conn = connect_database(database_path)
        self._ensure_social_columns(conn)
        try:
            cur = conn.cursor()
            query = """
                SELECT COUNT(*)
                FROM prospects
                WHERE COALESCE(TRIM(entreprise),'') != ''
            """
            params = []

            if mode == self.MODE_PENDING:
                query += """
                    AND COALESCE(TRIM(statut_enrichissement),'')
                        NOT IN (?, ?)
                """
                params.extend(
                    [self.ENRICHED_STATUS, self.NO_RELIABLE_RESULT_STATUS]
                )
            elif mode == self.MODE_SELECTED:
                ids = self._normaliser_ids(prospect_ids)
                if not ids:
                    return 0
                placeholders = ",".join("?" for _ in ids)
                query += f" AND id IN ({placeholders})"
                params.extend(ids)

            cur.execute(query, params)
            return int(cur.fetchone()[0])
        finally:
            conn.close()

    def compter_a_enrichir(self, database_path):
        return self.compter_cible(database_path, mode=self.MODE_PENDING)

    def compter_sans_resultat(self, database_path):
        conn = connect_database(database_path)
        self._ensure_social_columns(conn)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*)
                FROM prospects
                WHERE COALESCE(TRIM(statut_enrichissement),'') = ?
                  AND COALESCE(TRIM(entreprise),'') != ''
                """,
                (self.NO_RELIABLE_RESULT_STATUS,),
            )
            return int(cur.fetchone()[0])
        finally:
            conn.close()

    def reinitialiser_sans_resultat(self, database_path):
        """Rend retraitables les prospects précédemment restés sans résultat.

        Les coordonnées déjà présentes ne sont jamais effacées ; seuls le
        statut d'enrichissement et la date de collecte sont réinitialisés.
        """
        conn = connect_database(database_path)
        self._ensure_social_columns(conn)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE prospects
                SET statut_enrichissement = '', date_collecte = NULL
                WHERE COALESCE(TRIM(statut_enrichissement),'') = ?
                """,
                (self.NO_RELIABLE_RESULT_STATUS,),
            )
            count = int(cur.rowcount or 0)
            conn.commit()
            return count
        finally:
            conn.close()

    def _charger_prospects(
        self,
        conn,
        limite=None,
        *,
        mode=MODE_PENDING,
        prospect_ids=None,
    ):
        mode = self._valider_mode(mode)
        cur = conn.cursor()
        query = """
            SELECT
                id,
                entreprise,
                siret,
                siren,
                adresse,
                code_postal,
                ville,
                code_naf,
                noms_recherche
            FROM prospects
            WHERE COALESCE(TRIM(entreprise),'') != ''
        """
        params = []

        if mode == self.MODE_PENDING:
            query += """
                AND COALESCE(TRIM(statut_enrichissement),'')
                    NOT IN (?, ?)
            """
            params.extend(
                [self.ENRICHED_STATUS, self.NO_RELIABLE_RESULT_STATUS]
            )
        elif mode == self.MODE_SELECTED:
            ids = self._normaliser_ids(prospect_ids)
            if not ids:
                return []
            placeholders = ",".join("?" for _ in ids)
            query += f" AND id IN ({placeholders})"
            params.extend(ids)

        query += " ORDER BY id ASC"

        if limite is not None:
            limite = int(limite)
            if limite <= 0:
                return []
            query += " LIMIT ?"
            params.append(limite)

        cur.execute(query, params)
        return cur.fetchall()

    @staticmethod
    def _parse_names_payload(payload):
        if isinstance(payload, list):
            return [str(value).strip() for value in payload if str(value).strip()]
        raw = str(payload or "").strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(value).strip() for value in parsed if str(value).strip()]
        except Exception:
            pass
        return [value.strip() for value in raw.split("\n") if value.strip()]

    @staticmethod
    def _text_key(value):
        value = str(value or "").lower().strip()
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    @classmethod
    def _append_unique_text(cls, target, *values):
        seen = {cls._text_key(value) for value in target if cls._text_key(value)}
        for value in values:
            value = str(value or "").strip()
            key = cls._text_key(value)
            if value and key and key not in seen:
                seen.add(key)
                target.append(value)

    @staticmethod
    def _split_saved_numbers(value):
        raw = str(value or "").strip()
        if not raw:
            return []
        return [part.strip() for part in re.split(r"\s*(?:/|;|\n)\s*", raw) if part.strip()]

    def _charger_contexte_siren(self, conn):
        """Charge les autres établissements de chaque unité légale locale.

        Aucun appel externe n'est réalisé. Ce contexte sert uniquement à
        mutualiser noms, implantations et coordonnées déjà connues entre les
        SIRET portant le même SIREN.
        """
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                id, entreprise, siret, siren, adresse, code_postal, ville,
                noms_recherche, telephone, mobile, site_web, email,
                facebook, linkedin, instagram, twitter, youtube,
                social_other_urls
            FROM prospects
            WHERE COALESCE(TRIM(siren),'') != ''
            ORDER BY id ASC
            """
        )
        groups = {}
        for row in cur.fetchall():
            siren = re.sub(r"\D", "", str(row[3] or ""))
            if len(siren) != 9:
                continue
            member = {
                "id": row[0],
                "entreprise": row[1] or "",
                "siret": row[2] or "",
                "siren": siren,
                "adresse": row[4] or "",
                "code_postal": row[5] or "",
                "ville": row[6] or "",
                "noms_recherche": self._parse_names_payload(row[7]),
                "telephone": row[8] or "",
                "mobile": row[9] or "",
                "site_web": row[10] or "",
                "email": row[11] or "",
                "facebook": row[12] or "",
                "linkedin": row[13] or "",
                "instagram": row[14] or "",
                "twitter": row[15] or "",
                "youtube": row[16] or "",
                "social_other_urls": row[17] or "",
            }
            groups.setdefault(siren, []).append(member)
        return groups

    @staticmethod
    def _neutraliser_contacts_cibles_siren(groups, prospect_ids):
        """Retire du contexte les anciennes coordonnées des cibles retraitées.

        Les noms et implantations restent disponibles pour l'identification,
        mais une ancienne coordonnée d'un prospect ciblé ne peut pas revenir
        par mutualisation SIREN pendant le même réenrichissement.
        """
        target_ids = set(prospect_ids or [])
        if not target_ids:
            return
        contact_keys = (
            "telephone",
            "mobile",
            "site_web",
            "email",
            "facebook",
            "linkedin",
            "instagram",
            "twitter",
            "youtube",
            "social_other_urls",
        )
        for members in groups.values():
            for member in members:
                if member.get("id") not in target_ids:
                    continue
                for key in contact_keys:
                    member[key] = ""

    def _identity_avec_contexte_siren(self, identity, prospect_id, groups):
        """Ajoute les noms/adresses des autres établissements du même SIREN."""
        enriched = dict(identity)
        siren = re.sub(r"\D", "", str(identity.get("siren") or ""))
        members = groups.get(siren, []) if len(siren) == 9 else []
        if len(members) <= 1:
            enriched["localisations_recherche"] = []
            return enriched

        aliases = list(identity.get("noms_recherche") or [])
        locations = []
        principal_key = self._text_key(identity.get("entreprise", ""))

        for member in members:
            # Les coordonnées du SIRET courant sont déjà présentes dans identity.
            if member.get("id") == prospect_id:
                continue

            sibling_name = str(member.get("entreprise") or "").strip()
            if sibling_name and self._text_key(sibling_name) != principal_key:
                self._append_unique_text(aliases, sibling_name)
            self._append_unique_text(aliases, *(member.get("noms_recherche") or []))

            location = {
                "adresse": member.get("adresse", ""),
                "code_postal": member.get("code_postal", ""),
                "ville": member.get("ville", ""),
            }
            if any(str(value or "").strip() for value in location.values()):
                key = tuple(self._text_key(location[k]) for k in ("adresse", "code_postal", "ville"))
                existing = {
                    tuple(self._text_key(item.get(k, "")) for k in ("adresse", "code_postal", "ville"))
                    for item in locations
                }
                if key not in existing:
                    locations.append(location)

        enriched["noms_recherche"] = aliases
        enriched["localisations_recherche"] = locations
        return enriched

    def _identity_avec_api_context(self, identity, api_context):
        """Ajoute le siège / établissements nationaux résolus via l'API publique.

        L'API ne remplace pas les sources de coordonnées. Elle complète seulement
        les noms et localisations afin que PagesJaunes et Google Maps puissent
        rechercher le siège ou une autre implantation de la même unité légale.
        """
        enriched = dict(identity)
        if not (api_context or {}).get("resolved"):
            return enriched

        aliases = list(enriched.get("noms_recherche") or [])
        self._append_unique_text(aliases, *((api_context or {}).get("names") or []))

        # Le siège retourné par l'API est prioritaire parmi les localisations
        # secondaires : PagesJaunes / Maps ne testent volontairement qu'un petit
        # nombre d'adresses pour préserver la vitesse.
        local_locations = list(enriched.get("localisations_recherche") or [])
        locations = []
        existing = {
            tuple(
                self._text_key(enriched.get(k, ""))
                for k in ("adresse", "code_postal", "ville")
            )
        }

        for item in list((api_context or {}).get("locations") or []) + local_locations:
            if not isinstance(item, dict):
                continue
            location = {
                "adresse": str(item.get("adresse") or "").strip(),
                "code_postal": str(item.get("code_postal") or "").strip(),
                "ville": str(item.get("ville") or "").strip(),
            }
            key = tuple(self._text_key(location[k]) for k in ("adresse", "code_postal", "ville"))
            if any(key) and key not in existing:
                existing.add(key)
                locations.append(location)

        enriched["noms_recherche"] = aliases
        enriched["localisations_recherche"] = locations
        enriched["siret_siege_api"] = str((api_context or {}).get("siret_siege") or "")
        enriched["api_siren_resolved"] = True
        return enriched

    def _contacts_du_siren(self, identity, prospect_id, groups):
        """Retourne les coordonnées déjà connues sur les SIRET frères."""
        siren = re.sub(r"\D", "", str(identity.get("siren") or ""))
        members = groups.get(siren, []) if len(siren) == 9 else []
        phones = []
        mobiles = []
        other_urls = []
        bundle = {
            "phones": phones,
            "mobiles": mobiles,
            "site_web": "",
            "email": "",
            "facebook": "",
            "linkedin": "",
            "instagram": "",
            "twitter": "",
            "youtube": "",
            "other_urls": other_urls,
        }
        for member in members:
            if member.get("id") == prospect_id:
                continue
            phones.extend(self._split_saved_numbers(member.get("telephone")))
            mobiles.extend(self._split_saved_numbers(member.get("mobile")))
            for key in (
                "site_web", "email", "facebook", "linkedin", "instagram",
                "twitter", "youtube",
            ):
                if not bundle[key] and str(member.get(key) or "").strip():
                    bundle[key] = str(member.get(key) or "").strip()
            for url in str(member.get("social_other_urls") or "").splitlines():
                url = url.strip()
                if url and url not in other_urls:
                    other_urls.append(url)

        bundle["phones"] = self._fusionner_telephones(phones)
        bundle["mobiles"] = self._fusionner_telephones(mobiles)
        return bundle

    def _mettre_a_jour_contexte_siren(
        self,
        groups,
        prospect_id,
        siren,
        *,
        telephone="",
        mobile="",
        site_web="",
        email="",
        reseaux=None,
    ):
        """Rend immédiatement les nouvelles données disponibles aux SIRET frères."""
        siren = re.sub(r"\D", "", str(siren or ""))
        if len(siren) != 9:
            return
        reseaux = reseaux or {}
        for member in groups.get(siren, []):
            if member.get("id") != prospect_id:
                continue
            if telephone:
                member["telephone"] = telephone
            if mobile:
                member["mobile"] = mobile
            if site_web:
                member["site_web"] = site_web
            if email:
                member["email"] = email
            for key in ("facebook", "linkedin", "instagram", "twitter", "youtube"):
                value = str(reseaux.get(key) or "").strip()
                if value:
                    member[key] = value
            other = reseaux.get("other_urls") or []
            if other:
                member["social_other_urls"] = "\n".join(other)
            break

    @staticmethod
    def _format_progress_stats(
        *,
        index,
        total,
        entreprise,
        message,
        started_at,
        traites,
        enrichis,
        sans_resultat,
        erreurs,
        telephones,
        sites,
        emails,
        facebook,
        linkedin,
        instagram,
        youtube,
        source_pages_jaunes,
        source_google_maps,
        source_siren,
        source_web,
        api_siren_resolved,
        state="RUNNING",
    ):
        elapsed = max(0.0, time.monotonic() - started_at)
        completed = traites + erreurs
        speed = (
            (completed / elapsed) * 60
            if elapsed > 0 and completed > 0
            else 0.0
        )
        remaining = max(0, total - completed)
        eta = (remaining / speed) * 60 if speed > 0 else None
        percentage = int((completed / total) * 100) if total else 0

        return {
            "state": state,
            "index": index,
            "completed": completed,
            "total": total,
            "percentage": min(100, percentage),
            "entreprise": entreprise or "",
            "message": message,
            "traites": traites,
            "enrichis": enrichis,
            "sans_resultat": sans_resultat,
            "erreurs": erreurs,
            "telephones": telephones,
            "sites": sites,
            "emails": emails,
            "facebook": facebook,
            "linkedin": linkedin,
            "instagram": instagram,
            "youtube": youtube,
            "source_pages_jaunes": source_pages_jaunes,
            "source_google_maps": source_google_maps,
            "source_siren": source_siren,
            "source_web": source_web,
            "api_siren_resolved": api_siren_resolved,
            "elapsed_seconds": elapsed,
            "eta_seconds": eta,
            "speed_per_minute": speed,
        }

    @staticmethod
    def _normaliser_telephone(numero):
        raw = str(numero or "").strip()
        compact = re.sub(r"\D", "", raw)

        if raw.startswith("+33") and len(compact) == 11 and compact.startswith("33"):
            compact = "0" + compact[2:]
        elif raw.startswith("0033") and len(compact) == 13 and compact.startswith("0033"):
            compact = "0" + compact[4:]

        if (
            len(compact) == 10
            and compact.startswith("0")
            and compact[1] in "123456789"
        ):
            return " ".join(compact[i:i + 2] for i in range(0, 10, 2))
        return ""

    @classmethod
    def _fusionner_telephones(cls, *collections):
        values = []
        seen = set()

        for collection in collections:
            for raw in collection or []:
                number = cls._normaliser_telephone(raw)
                key = re.sub(r"\D", "", number)
                if key and key not in seen:
                    seen.add(key)
                    values.append(number)

        def order(number):
            compact = re.sub(r"\D", "", number)
            if compact.startswith(("06", "07")):
                return (0, compact)
            if compact.startswith(("01", "02", "03", "04", "05", "09")):
                return (1, compact)
            return (2, compact)

        return sorted(values, key=order)

    @classmethod
    def _select_contact_numbers(cls, valid_results):
        """Fusionne tous les numéros des sources validées, hors fax.

        Le commercial doit pouvoir disposer de plusieurs standards / mobiles
        lorsqu'ils sont publiés pour la même entreprise. Les fax explicitement
        identifiés restent systématiquement exclus.
        """
        ordered = sorted(
            valid_results or [],
            key=lambda result: int(result.get("match_score") or 0),
            reverse=True,
        )

        fax_keys = set()
        for result in ordered:
            for raw in result.get("faxes") or []:
                fax = cls._normaliser_telephone(raw)
                key = re.sub(r"\D", "", fax)
                if key:
                    fax_keys.add(key)

        merged = []
        sources = []
        seen = set()
        for result in ordered:
            source_has_phone = False
            for raw in result.get("telephones") or []:
                number = cls._normaliser_telephone(raw)
                key = re.sub(r"\D", "", number)
                if not key or key in fax_keys or key in seen:
                    continue
                seen.add(key)
                merged.append(number)
                source_has_phone = True
            if source_has_phone:
                source = str(result.get("source") or "").strip()
                if source and source not in sources:
                    sources.append(source)

        merged = cls._fusionner_telephones(merged)
        return merged, " + ".join(sources)

    @staticmethod
    def _valid(result):
        return bool(result and result.get("confidence") == "validated")

    @staticmethod
    def _technical_errors(*results):
        errors = []
        for result in results:
            for error in (result or {}).get("technical_errors") or []:
                if error and error not in errors:
                    errors.append(str(error))
        return errors

    @staticmethod
    def _has_candidate(*results):
        return any(
            result
            and (
                str(result.get("nom") or "").strip()
                or str(result.get("texte") or "").strip()
            )
            for result in results
        )

    @staticmethod
    def _result_has_contact(result):
        result = result or {}
        return bool(
            result.get("telephones")
            or str(result.get("site_web") or "").strip()
            or str(result.get("email") or "").strip()
        )

    @staticmethod
    def _has_useful_data(
        telephone,
        mobile,
        site_web,
        email,
        reseaux,
    ):
        return any(
            [
                telephone,
                mobile,
                site_web,
                email,
                reseaux.get("facebook", ""),
                reseaux.get("linkedin", ""),
                reseaux.get("instagram", ""),
                reseaux.get("twitter", ""),
                reseaux.get("youtube", ""),
                *(reseaux.get("other_urls") or []),
            ]
        )

    @staticmethod
    def _vider_coordonnees_enrichissement(cur, prospect_id):
        cur.execute(
            """
            UPDATE prospects
            SET telephone = '',
                mobile = '',
                site_web = '',
                email = '',
                facebook = '',
                linkedin = '',
                instagram = '',
                twitter = '',
                youtube = '',
                social_other_urls = ''
            WHERE id = ?
            """,
            (prospect_id,),
        )

    @staticmethod
    def _enregistrer_coordonnees(
        cur,
        prospect_id,
        *,
        telephone,
        mobile,
        site_web,
        email,
        reseaux,
        statut,
        remplacer,
    ):
        other_urls = "\n".join(reseaux.get("other_urls") or [])

        if remplacer:
            cur.execute(
                """
                UPDATE prospects
                SET telephone = ?,
                    mobile = ?,
                    site_web = ?,
                    email = ?,
                    facebook = ?,
                    linkedin = ?,
                    instagram = ?,
                    twitter = ?,
                    youtube = ?,
                    social_other_urls = ?,
                    statut_enrichissement = ?,
                    date_collecte = ?
                WHERE id = ?
                """,
                (
                    telephone,
                    mobile,
                    site_web,
                    email,
                    reseaux.get("facebook", ""),
                    reseaux.get("linkedin", ""),
                    reseaux.get("instagram", ""),
                    reseaux.get("twitter", ""),
                    reseaux.get("youtube", ""),
                    other_urls,
                    statut,
                    str(date.today()),
                    prospect_id,
                ),
            )
            return

        cur.execute(
            """
            UPDATE prospects
            SET
                telephone = CASE WHEN COALESCE(TRIM(?),'') != ''
                    THEN ? ELSE telephone END,
                mobile = CASE WHEN COALESCE(TRIM(?),'') != ''
                    THEN ? ELSE mobile END,
                site_web = CASE WHEN COALESCE(TRIM(?),'') != ''
                    THEN ? ELSE site_web END,
                email = CASE WHEN COALESCE(TRIM(?),'') != ''
                    THEN ? ELSE email END,
                facebook = CASE WHEN COALESCE(TRIM(?),'') != ''
                    THEN ? ELSE facebook END,
                linkedin = CASE WHEN COALESCE(TRIM(?),'') != ''
                    THEN ? ELSE linkedin END,
                instagram = CASE WHEN COALESCE(TRIM(?),'') != ''
                    THEN ? ELSE instagram END,
                twitter = CASE WHEN COALESCE(TRIM(?),'') != ''
                    THEN ? ELSE twitter END,
                youtube = CASE WHEN COALESCE(TRIM(?),'') != ''
                    THEN ? ELSE youtube END,
                social_other_urls = CASE WHEN COALESCE(TRIM(?),'') != ''
                    THEN ? ELSE social_other_urls END,
                statut_enrichissement = ?,
                date_collecte = ?
            WHERE id = ?
            """,
            (
                telephone,
                telephone,
                mobile,
                mobile,
                site_web,
                site_web,
                email,
                email,
                reseaux.get("facebook", ""),
                reseaux.get("facebook", ""),
                reseaux.get("linkedin", ""),
                reseaux.get("linkedin", ""),
                reseaux.get("instagram", ""),
                reseaux.get("instagram", ""),
                reseaux.get("twitter", ""),
                reseaux.get("twitter", ""),
                reseaux.get("youtube", ""),
                reseaux.get("youtube", ""),
                other_urls,
                other_urls,
                statut,
                str(date.today()),
                prospect_id,
            ),
        )

    def enrichir(
        self,
        database_path,
        limite=None,
        progress_callback=None,
        should_stop=None,
        wait_if_paused=None,
        mode=MODE_PENDING,
        prospect_ids=None,
    ):
        """Entrée synchrone conservée pour le Worker Qt."""
        return asyncio.run(
            self._enrichir_async(
                database_path,
                limite=limite,
                progress_callback=progress_callback,
                should_stop=should_stop,
                wait_if_paused=wait_if_paused,
                mode=mode,
                prospect_ids=prospect_ids,
            )
        )

    async def _enrichir_async(
        self,
        database_path,
        limite=None,
        progress_callback=None,
        should_stop=None,
        wait_if_paused=None,
        mode=MODE_PENDING,
        prospect_ids=None,
    ):
        mode = self._valider_mode(mode)
        remplacer = mode in {self.MODE_SELECTED, self.MODE_ALL}

        conn = connect_database(database_path)
        self._ensure_social_columns(conn)
        prospects = self._charger_prospects(
            conn,
            limite,
            mode=mode,
            prospect_ids=prospect_ids,
        )
        target_ids = [row[0] for row in prospects]
        self._sanitize_existing_contacts(
            conn,
            prospect_ids=target_ids if mode == self.MODE_SELECTED else None,
        )
        siren_groups = self._charger_contexte_siren(conn)
        if remplacer:
            self._neutraliser_contacts_cibles_siren(siren_groups, target_ids)
        total = len(prospects)
        started_at = time.monotonic()
        api_stats_start = self.entreprise_api.stats()

        def api_run_stats():
            current = self.entreprise_api.stats()
            return {
                "api_requests": max(0, int(current.get("api_requests", 0)) - int(api_stats_start.get("api_requests", 0))),
                "api_cache_hits": max(0, int(current.get("api_cache_hits", 0)) - int(api_stats_start.get("api_cache_hits", 0))),
                "api_failures": max(0, int(current.get("api_failures", 0)) - int(api_stats_start.get("api_failures", 0))),
                "api_cache_size": int(current.get("api_cache_size", 0)),
            }

        traites = 0
        enrichis = 0
        sans_resultat = 0
        erreurs = 0
        interrompu = False

        compteurs = {
            "telephones": 0,
            "sites": 0,
            "emails": 0,
            "facebook": 0,
            "linkedin": 0,
            "instagram": 0,
            "youtube": 0,
            "source_pages_jaunes": 0,
            "source_google_maps": 0,
            "source_siren": 0,
            "source_web": 0,
            "api_siren_resolved": 0,
        }

        def emit(index, entreprise, message):
            if progress_callback:
                progress_callback(
                    self._format_progress_stats(
                        index=index,
                        total=total,
                        entreprise=entreprise,
                        message=message,
                        started_at=started_at,
                        traites=traites,
                        enrichis=enrichis,
                        sans_resultat=sans_resultat,
                        erreurs=erreurs,
                        **compteurs,
                    )
                )

        if total == 0:
            conn.close()
            return {
                "total": 0,
                "traites": 0,
                "enrichis": 0,
                "sans_resultat": 0,
                "erreurs": 0,
                "interrompu": False,
                **compteurs,
                **api_run_stats(),
                "elapsed_seconds": 0.0,
            }

        try:
            # Lot 2.3.1 : ouverture paresseuse des navigateurs. Auparavant
            # Google Maps ET PagesJaunes étaient lancés avant même le premier
            # prospect, ce qui donnait l'impression que l'enrichissement était
            # bloqué au démarrage. Chaque source ouvre maintenant son navigateur
            # uniquement au moment où elle est réellement utilisée.
            cur = conn.cursor()

            for index, prospect in enumerate(prospects, start=1):
                if wait_if_paused:
                    wait_if_paused()
                if should_stop and should_stop():
                    interrompu = True
                    break

                (
                    prospect_id,
                    entreprise,
                    siret,
                    siren,
                    adresse,
                    code_postal,
                    ville,
                    code_naf,
                    noms_recherche,
                ) = prospect

                try:
                    parsed_names = json.loads(noms_recherche or "[]")
                    if not isinstance(parsed_names, list):
                        parsed_names = []
                except Exception:
                    parsed_names = [
                        value.strip()
                        for value in str(noms_recherche or "").split("\n")
                        if value.strip()
                    ]

                identity = {
                    "entreprise": entreprise or "",
                    "siret": siret or "",
                    "siren": siren or "",
                    "adresse": adresse or "",
                    "code_postal": code_postal or "",
                    "ville": ville or "",
                    "code_naf": code_naf or "",
                    "noms_recherche": parsed_names,
                }
                identity = self._identity_avec_contexte_siren(
                    identity, prospect_id, siren_groups
                )

                # Affiche immédiatement une activité avant l'appel réseau API,
                # afin que le premier prospect ne paraisse plus figé au départ.
                emit(
                    index,
                    entreprise,
                    "API SIREN : résolution du siège et des établissements...",
                )

                # Lot 2.3 : résolution nationale du SIREN. L'appel est rapide,
                # mis en cache et ne sert qu'à compléter les noms / adresses.
                api_context = await asyncio.to_thread(
                    self.entreprise_api.resolve,
                    identity,
                )
                if api_context.get("resolved"):
                    compteurs["api_siren_resolved"] += 1
                    identity = self._identity_avec_api_context(identity, api_context)

                siren_contacts = self._contacts_du_siren(
                    identity, prospect_id, siren_groups
                )

                try:
                    emit(
                        index,
                        entreprise,
                        "PagesJaunes : recherche par enseigne / nom / raison sociale et localisation...",
                    )
                    pages_name_result = await self.pages_jaunes.rechercher_nom(identity)

                    pre_valid = [
                        result
                        for result in (pages_name_result,)
                        if self._valid(result)
                    ]
                    has_phone = any(
                        result.get("telephones") for result in pre_valid
                    )
                    has_site = any(result.get("site_web") for result in pre_valid)

                    google_result = None
                    if not pre_valid or not has_phone or not has_site:
                        emit(
                            index,
                            entreprise,
                            "Google Maps : recherche et contrôle d’identité...",
                        )
                        google_result = await self.google.rechercher(identity)

                    siren_reseaux = {
                        "facebook": siren_contacts.get("facebook", ""),
                        "linkedin": siren_contacts.get("linkedin", ""),
                        "instagram": siren_contacts.get("instagram", ""),
                        "twitter": siren_contacts.get("twitter", ""),
                        "youtube": siren_contacts.get("youtube", ""),
                        "other_urls": list(siren_contacts.get("other_urls") or []),
                    }
                    has_siren_contacts = self._has_useful_data(
                        " / ".join(siren_contacts.get("phones") or []),
                        " / ".join(siren_contacts.get("mobiles") or []),
                        siren_contacts.get("site_web", ""),
                        siren_contacts.get("email", ""),
                        siren_reseaux,
                    )

                    # Recherche web de secours uniquement si PagesJaunes + Maps
                    # n'apportent aucune coordonnée et que le SIREN local n'a
                    # rien à mutualiser. Cela limite fortement le coût du fallback.
                    base_results = (pages_name_result, google_result)
                    base_valid = [result for result in base_results if self._valid(result)]
                    base_has_contact = any(
                        self._result_has_contact(result) for result in base_valid
                    )
                    web_result = None
                    if not base_has_contact and not has_siren_contacts:
                        emit(
                            index,
                            entreprise,
                            "Recherche web de secours : annuaires / site officiel...",
                        )
                        web_result = await asyncio.to_thread(
                            self.web_fallback.rechercher,
                            identity,
                        )

                    all_results = (pages_name_result, google_result, web_result)
                    valid = [result for result in all_results if self._valid(result)]

                    if not valid:
                        technical_errors = self._technical_errors(*all_results)
                        if (
                            technical_errors
                            and not self._has_candidate(*all_results)
                            and not has_siren_contacts
                        ):
                            raise RuntimeError(
                                "Sources inaccessibles ou non analysables : "
                                + technical_errors[0][:240]
                            )

                        # Lot 2.2 : si un établissement frère du même SIREN a
                        # déjà des coordonnées, elles restent exploitables même
                        # lorsque les recherches web du SIRET courant échouent.
                        if not has_siren_contacts:
                            if remplacer:
                                self._vider_coordonnees_enrichissement(
                                    cur, prospect_id
                                )
                            cur.execute(
                                """
                                UPDATE prospects
                                SET statut_enrichissement = ?, date_collecte = ?
                                WHERE id = ?
                                """,
                                (
                                    self.NO_RELIABLE_RESULT_STATUS,
                                    str(date.today()),
                                    prospect_id,
                                ),
                            )
                            conn.commit()
                            traites += 1
                            sans_resultat += 1
                            emit(
                                index,
                                entreprise,
                                "Aucun résultat suffisamment fiable : aucune donnée ajoutée.",
                            )
                            continue

                    valid.sort(
                        key=lambda result: int(result.get("match_score") or 0),
                        reverse=True,
                    )

                    web_phones, phone_source = self._select_contact_numbers(valid)
                    phones = self._fusionner_telephones(
                        web_phones,
                        siren_contacts.get("phones") or [],
                        siren_contacts.get("mobiles") or [],
                    )
                    if has_siren_contacts:
                        phone_source = (
                            f"{phone_source} + SIREN" if phone_source else "SIREN"
                        )

                    fixed_phones = []
                    mobile_phones = []
                    for number in phones:
                        compact = re.sub(r"\D", "", number)
                        if compact.startswith(("06", "07")):
                            mobile_phones.append(number)
                        else:
                            fixed_phones.append(number)
                    telephone = " / ".join(fixed_phones)
                    mobile = " / ".join(mobile_phones)

                    site_web = next(
                        (
                            result.get("site_web")
                            for result in valid
                            if result.get("site_web")
                        ),
                        "",
                    ) or siren_contacts.get("site_web", "")

                    email = next(
                        (
                            str(result.get("email") or "").strip()
                            for result in valid
                            if str(result.get("email") or "").strip()
                        ),
                        "",
                    ) or siren_contacts.get("email", "")
                    reseaux = dict(siren_reseaux)

                    if site_web:
                        emit(
                            index,
                            entreprise,
                            "Site validé / mutualisé : recherche email et réseaux sociaux...",
                        )
                        found_email = await asyncio.to_thread(
                            self.email_finder.chercher,
                            site_web,
                        )
                        if found_email:
                            email = found_email

                        found_socials = await asyncio.to_thread(
                            self.social_finder.chercher,
                            site_web,
                        )
                        for key in (
                            "facebook", "linkedin", "instagram", "twitter", "youtube"
                        ):
                            if found_socials.get(key):
                                reseaux[key] = found_socials.get(key)
                        for url in found_socials.get("other_urls") or []:
                            if url and url not in reseaux["other_urls"]:
                                reseaux["other_urls"].append(url)

                    if not self._has_useful_data(
                        telephone,
                        mobile,
                        site_web,
                        email,
                        reseaux,
                    ):
                        if remplacer:
                            self._vider_coordonnees_enrichissement(
                                cur, prospect_id
                            )
                        cur.execute(
                            """
                            UPDATE prospects
                            SET statut_enrichissement = ?, date_collecte = ?
                            WHERE id = ?
                            """,
                            (
                                self.NO_RELIABLE_RESULT_STATUS,
                                str(date.today()),
                                prospect_id,
                            ),
                        )
                        conn.commit()
                        traites += 1
                        sans_resultat += 1
                        emit(
                            index,
                            entreprise,
                            "Identité validée, mais aucune coordonnée exploitable n’a été trouvée.",
                        )
                        continue

                    self._enregistrer_coordonnees(
                        cur,
                        prospect_id,
                        telephone=telephone,
                        mobile=mobile,
                        site_web=site_web,
                        email=email,
                        reseaux=reseaux,
                        statut=self.ENRICHED_STATUS,
                        remplacer=remplacer,
                    )

                    ScoringService.score_prospect_with_connection(conn, prospect_id)
                    conn.commit()
                    self._mettre_a_jour_contexte_siren(
                        siren_groups,
                        prospect_id,
                        siren,
                        telephone=telephone,
                        mobile=mobile,
                        site_web=site_web,
                        email=email,
                        reseaux=reseaux,
                    )
                    traites += 1
                    enrichis += 1

                    if phones:
                        compteurs["telephones"] += 1
                    if site_web:
                        compteurs["sites"] += 1
                    if email:
                        compteurs["emails"] += 1
                    for key in ("facebook", "linkedin", "instagram", "youtube"):
                        if reseaux.get(key):
                            compteurs[key] += 1

                    if self._valid(pages_name_result) and self._result_has_contact(pages_name_result):
                        compteurs["source_pages_jaunes"] += 1
                    if self._valid(google_result) and self._result_has_contact(google_result):
                        compteurs["source_google_maps"] += 1
                    if has_siren_contacts:
                        compteurs["source_siren"] += 1
                    if self._valid(web_result) and self._result_has_contact(web_result):
                        compteurs["source_web"] += 1

                    source_values = []
                    for result in valid:
                        source = str(result.get("source") or "").strip()
                        if source == "web_fallback" and result.get("source_detail"):
                            source = f"web ({result.get('source_detail')})"
                        if source:
                            source_values.append(source)
                    if has_siren_contacts:
                        source_values.append("mutualisation SIREN")
                    sources = " + ".join(dict.fromkeys(source_values)) or "mutualisation SIREN"
                    phone_detail = (
                        f"{len(phones)} numéro(s) [{phone_source}]"
                        if phones
                        else "0"
                    )
                    emit(
                        index,
                        entreprise,
                        f"{sources} | Tél: {phone_detail} | "
                        f"Site: {site_web or '—'} | Email: {email or '—'}",
                    )

                except Exception as exc:
                    erreurs += 1
                    cur.execute(
                        """
                        UPDATE prospects
                        SET statut_enrichissement = ?, date_collecte = ?
                        WHERE id = ?
                        """,
                        (
                            self.ERROR_STATUS,
                            str(date.today()),
                            prospect_id,
                        ),
                    )
                    conn.commit()
                    emit(
                        index,
                        entreprise,
                        f"Erreur technique, passage au prospect suivant : {exc}",
                    )

        finally:
            try:
                await self.google.fermer()
            finally:
                await self.pages_jaunes.fermer()
                conn.close()

        return {
            "total": total,
            "traites": traites,
            "enrichis": enrichis,
            "sans_resultat": sans_resultat,
            "erreurs": erreurs,
            "interrompu": interrompu,
            **compteurs,
            **api_run_stats(),
            "elapsed_seconds": max(0.0, time.monotonic() - started_at),
        }

from __future__ import annotations

import asyncio
import re
import time
from datetime import date

from core.sqlite_utils import connect_database
from modules.google_maps import GoogleMapsFinder
from modules.pages_jaunes import PagesJaunesFinder
from modules.email_finder import EmailFinder
from modules.social_finder import SocialFinder
from services.scoring_service import ScoringService


class EnrichmentService:
    ENRICHED_STATUS = "Enrichi"
    NO_RELIABLE_RESULT_STATUS = "Aucun résultat fiable"
    ERROR_STATUS = "Erreur enrichissement"

    def __init__(self):
        self.google = GoogleMapsFinder()
        self.pages_jaunes = PagesJaunesFinder()
        self.email_finder = EmailFinder()
        self.social_finder = SocialFinder()

    @staticmethod
    def _ensure_social_columns(conn):
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(prospects)")
        columns = {row[1] for row in cur.fetchall()}

        for column in ("twitter", "social_other_urls"):
            if column not in columns:
                cur.execute(
                    f"ALTER TABLE prospects "
                    f"ADD COLUMN {column} TEXT DEFAULT ''"
                )
        conn.commit()

    def compter_a_enrichir(self, database_path):
        conn = connect_database(database_path)
        self._ensure_social_columns(conn)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*)
                FROM prospects
                WHERE COALESCE(TRIM(statut_enrichissement),'')
                      NOT IN (?, ?)
                  AND COALESCE(TRIM(entreprise),'') != ''
                """,
                (
                    self.ENRICHED_STATUS,
                    self.NO_RELIABLE_RESULT_STATUS,
                ),
            )
            return int(cur.fetchone()[0])
        finally:
            conn.close()

    def _charger_prospects(self, conn, limite=None):
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
                code_naf
            FROM prospects
            WHERE COALESCE(TRIM(statut_enrichissement),'')
                  NOT IN (?, ?)
              AND COALESCE(TRIM(entreprise),'') != ''
            ORDER BY id ASC
        """
        params = [
            self.ENRICHED_STATUS,
            self.NO_RELIABLE_RESULT_STATUS,
        ]

        if limite is not None:
            limite = int(limite)
            if limite <= 0:
                return []
            query += " LIMIT ?"
            params.append(limite)

        cur.execute(query, params)
        return cur.fetchall()

    @staticmethod
    def _format_progress_stats(
        *,
        index,
        total,
        entreprise,
        message,
        started_at,
        traites,
        erreurs,
        telephones,
        sites,
        emails,
        facebook,
        linkedin,
        instagram,
        youtube,
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
        eta = (
            (remaining / speed) * 60
            if speed > 0
            else None
        )
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
            "erreurs": erreurs,
            "telephones": telephones,
            "sites": sites,
            "emails": emails,
            "facebook": facebook,
            "linkedin": linkedin,
            "instagram": instagram,
            "youtube": youtube,
            "elapsed_seconds": elapsed,
            "eta_seconds": eta,
            "speed_per_minute": speed,
        }

    @staticmethod
    def _normaliser_telephone(numero):
        compact = re.sub(r"\D", "", str(numero or ""))
        if len(compact) == 10 and compact.startswith("0"):
            return " ".join(
                compact[i:i + 2]
                for i in range(0, 10, 2)
            )
        return str(numero or "").strip()

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
            if compact.startswith(
                ("01", "02", "03", "04", "05", "09")
            ):
                return (1, compact)
            return (2, compact)

        return sorted(values, key=order)

    @staticmethod
    def _valid(result):
        return bool(
            result
            and result.get("confidence") == "validated"
        )

    def enrichir(
        self,
        database_path,
        limite=None,
        progress_callback=None,
        should_stop=None,
        wait_if_paused=None,
    ):
        """Entrée synchrone conservée pour le Worker Qt.

        Toute la couche navigateur s'exécute désormais avec Playwright Async.
        """
        return asyncio.run(
            self._enrichir_async(
                database_path,
                limite=limite,
                progress_callback=progress_callback,
                should_stop=should_stop,
                wait_if_paused=wait_if_paused,
            )
        )

    async def _enrichir_async(
        self,
        database_path,
        limite=None,
        progress_callback=None,
        should_stop=None,
        wait_if_paused=None,
    ):
        conn = connect_database(database_path)
        self._ensure_social_columns(conn)

        prospects = self._charger_prospects(
            conn,
            limite,
        )
        total = len(prospects)
        started_at = time.monotonic()
        traites = 0
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
        }

        if total == 0:
            conn.close()
            return {
                "total": 0,
                "traites": 0,
                "erreurs": 0,
                "interrompu": False,
                **compteurs,
                "elapsed_seconds": 0.0,
            }

        try:
            await self.google.ouvrir()
            await self.pages_jaunes.ouvrir()

            cur = conn.cursor()

            for index, prospect in enumerate(
                prospects,
                start=1,
            ):
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
                ) = prospect

                identity = {
                    "entreprise": entreprise or "",
                    "siret": siret or "",
                    "siren": siren or "",
                    "adresse": adresse or "",
                    "code_postal": code_postal or "",
                    "ville": ville or "",
                    "code_naf": code_naf or "",
                }

                try:
                    if progress_callback:
                        progress_callback(
                            self._format_progress_stats(
                                index=index,
                                total=total,
                                entreprise=entreprise,
                                message=(
                                    "Google Maps : recherche "
                                    "et contrôle d’identité..."
                                ),
                                started_at=started_at,
                                traites=traites,
                                erreurs=erreurs,
                                **compteurs,
                            )
                        )

                    google_result = await self.google.rechercher(
                        identity
                    )

                    need_pages_jaunes = (
                        not self._valid(google_result)
                        or not google_result.get("telephones")
                        or not google_result.get("site_web")
                    )

                    pages_result = None

                    if need_pages_jaunes:
                        if progress_callback:
                            progress_callback(
                                self._format_progress_stats(
                                    index=index,
                                    total=total,
                                    entreprise=entreprise,
                                    message=(
                                        "PagesJaunes : "
                                        "recherche complémentaire..."
                                    ),
                                    started_at=started_at,
                                    traites=traites,
                                    erreurs=erreurs,
                                    **compteurs,
                                )
                            )

                        pages_result = (
                            await self.pages_jaunes.rechercher(
                                identity
                            )
                        )

                    valid = [
                        result
                        for result in (
                            google_result,
                            pages_result,
                        )
                        if self._valid(result)
                    ]

                    if not valid:
                        cur.execute(
                            """
                            UPDATE prospects
                            SET
                                statut_enrichissement = ?,
                                date_collecte = ?
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

                        if progress_callback:
                            progress_callback(
                                self._format_progress_stats(
                                    index=index,
                                    total=total,
                                    entreprise=entreprise,
                                    message=(
                                        "Aucun résultat suffisamment "
                                        "fiable : aucune donnée ajoutée."
                                    ),
                                    started_at=started_at,
                                    traites=traites,
                                    erreurs=erreurs,
                                    **compteurs,
                                )
                            )
                        continue

                    phones = self._fusionner_telephones(
                        *(
                            result.get("telephones") or []
                            for result in valid
                        )
                    )
                    telephone = "\n".join(phones)

                    valid.sort(
                        key=lambda result: int(
                            result.get("match_score") or 0
                        ),
                        reverse=True,
                    )

                    site_web = next(
                        (
                            result.get("site_web")
                            for result in valid
                            if result.get("site_web")
                        ),
                        "",
                    )

                    email = ""
                    reseaux = {
                        "facebook": "",
                        "linkedin": "",
                        "instagram": "",
                        "twitter": "",
                        "youtube": "",
                        "other_urls": [],
                    }

                    if site_web:
                        if progress_callback:
                            progress_callback(
                                self._format_progress_stats(
                                    index=index,
                                    total=total,
                                    entreprise=entreprise,
                                    message=(
                                        "Site validé : recherche "
                                        "email et réseaux sociaux..."
                                    ),
                                    started_at=started_at,
                                    traites=traites,
                                    erreurs=erreurs,
                                    **compteurs,
                                )
                            )

                        # Ces services utilisent requests et restent synchrones.
                        # Ils sont volontairement exécutés dans un thread afin
                        # de ne pas bloquer la boucle Playwright Async.
                        email = await asyncio.to_thread(
                            self.email_finder.chercher,
                            site_web,
                        )
                        reseaux = await asyncio.to_thread(
                            self.social_finder.chercher,
                            site_web,
                        )

                    cur.execute(
                        """
                        UPDATE prospects
                        SET
                            telephone =
                                CASE WHEN COALESCE(TRIM(?),'') != ''
                                THEN ? ELSE telephone END,
                            site_web =
                                CASE WHEN COALESCE(TRIM(?),'') != ''
                                THEN ? ELSE site_web END,
                            email =
                                CASE WHEN COALESCE(TRIM(?),'') != ''
                                THEN ? ELSE email END,
                            facebook =
                                CASE WHEN COALESCE(TRIM(?),'') != ''
                                THEN ? ELSE facebook END,
                            linkedin =
                                CASE WHEN COALESCE(TRIM(?),'') != ''
                                THEN ? ELSE linkedin END,
                            instagram =
                                CASE WHEN COALESCE(TRIM(?),'') != ''
                                THEN ? ELSE instagram END,
                            twitter =
                                CASE WHEN COALESCE(TRIM(?),'') != ''
                                THEN ? ELSE twitter END,
                            youtube =
                                CASE WHEN COALESCE(TRIM(?),'') != ''
                                THEN ? ELSE youtube END,
                            social_other_urls =
                                CASE WHEN COALESCE(TRIM(?),'') != ''
                                THEN ? ELSE social_other_urls END,
                            statut_enrichissement = ?,
                            date_collecte = ?
                        WHERE id = ?
                        """,
                        (
                            telephone,
                            telephone,
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
                            "\n".join(
                                reseaux.get("other_urls") or []
                            ),
                            "\n".join(
                                reseaux.get("other_urls") or []
                            ),
                            self.ENRICHED_STATUS,
                            str(date.today()),
                            prospect_id,
                        ),
                    )

                    ScoringService.score_prospect_with_connection(
                        conn,
                        prospect_id,
                    )
                    conn.commit()
                    traites += 1

                    if telephone:
                        compteurs["telephones"] += 1
                    if site_web:
                        compteurs["sites"] += 1
                    if email:
                        compteurs["emails"] += 1

                    for key in (
                        "facebook",
                        "linkedin",
                        "instagram",
                        "youtube",
                    ):
                        if reseaux.get(key):
                            compteurs[key] += 1

                    if progress_callback:
                        sources = " + ".join(
                            result["source"]
                            for result in valid
                        )
                        progress_callback(
                            self._format_progress_stats(
                                index=index,
                                total=total,
                                entreprise=entreprise,
                                message=(
                                    f"{sources} | "
                                    f"Tél: {len(phones)} numéro(s) | "
                                    f"Site: {site_web or '—'} | "
                                    f"Email: {email or '—'}"
                                ),
                                started_at=started_at,
                                traites=traites,
                                erreurs=erreurs,
                                **compteurs,
                            )
                        )

                except Exception as exc:
                    erreurs += 1
                    cur.execute(
                        """
                        UPDATE prospects
                        SET
                            statut_enrichissement = ?,
                            date_collecte = ?
                        WHERE id = ?
                        """,
                        (
                            self.ERROR_STATUS,
                            str(date.today()),
                            prospect_id,
                        ),
                    )
                    conn.commit()

                    if progress_callback:
                        progress_callback(
                            self._format_progress_stats(
                                index=index,
                                total=total,
                                entreprise=entreprise,
                                message=(
                                    "Erreur, passage au prospect "
                                    f"suivant : {exc}"
                                ),
                                started_at=started_at,
                                traites=traites,
                                erreurs=erreurs,
                                **compteurs,
                            )
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
            "erreurs": erreurs,
            "interrompu": interrompu,
            **compteurs,
            "elapsed_seconds": max(
                0.0,
                time.monotonic() - started_at,
            ),
        }

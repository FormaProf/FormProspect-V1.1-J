import sqlite3
from core.sqlite_utils import connect_database
import time
from datetime import date

from modules.google_maps import GoogleMapsFinder
from modules.email_finder import EmailFinder
from modules.social_finder import SocialFinder
from services.scoring_service import ScoringService


class EnrichmentService:
    """Service d'enrichissement reprenable avec statistiques détaillées."""

    ENRICHED_STATUS = "Enrichi"
    ERROR_STATUS = "Erreur enrichissement"

    def __init__(self):
        self.google = GoogleMapsFinder()
        self.email_finder = EmailFinder()
        self.social_finder = SocialFinder()

    def compter_a_enrichir(self, database_path):
        conn = connect_database(database_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*)
                FROM prospects
                WHERE COALESCE(TRIM(statut_enrichissement), '') != ?
                  AND COALESCE(TRIM(entreprise), '') != ''
                """,
                (self.ENRICHED_STATUS,),
            )
            return int(cur.fetchone()[0])
        finally:
            conn.close()

    def _charger_prospects(self, conn, limite=None):
        cur = conn.cursor()
        requete = """
            SELECT id, entreprise, code_postal, ville
            FROM prospects
            WHERE COALESCE(TRIM(statut_enrichissement), '') != ?
              AND COALESCE(TRIM(entreprise), '') != ''
            ORDER BY id ASC
        """
        params = [self.ENRICHED_STATUS]

        if limite is not None:
            limite = int(limite)
            if limite <= 0:
                return []
            requete += " LIMIT ?"
            params.append(limite)

        cur.execute(requete, params)
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
        speed_per_minute = (completed / elapsed) * 60 if elapsed > 0 and completed > 0 else 0.0
        remaining = max(0, total - completed)
        eta_seconds = (remaining / speed_per_minute) * 60 if speed_per_minute > 0 else None
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
            "eta_seconds": eta_seconds,
            "speed_per_minute": speed_per_minute,
        }

    def enrichir(
        self,
        database_path,
        limite=None,
        progress_callback=None,
        should_stop=None,
        wait_if_paused=None,
    ):
        """Enrichit les prospects non encore enrichis.

        ``progress_callback`` reçoit un dictionnaire complet de statistiques.
        ``should_stop`` retourne True lorsqu'un arrêt est demandé.
        ``wait_if_paused`` bloque proprement tant que le traitement est en pause.
        """
        conn = connect_database(database_path)
        prospects = self._charger_prospects(conn, limite=limite)
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

        self.google.ouvrir()

        try:
            cur = conn.cursor()

            for index, prospect in enumerate(prospects, start=1):
                if wait_if_paused:
                    wait_if_paused()

                if should_stop and should_stop():
                    interrompu = True
                    break

                prospect_id, entreprise, code_postal, ville = prospect

                if progress_callback:
                    progress_callback(
                        self._format_progress_stats(
                            index=index,
                            total=total,
                            entreprise=entreprise,
                            message="Recherche Google Maps...",
                            started_at=started_at,
                            traites=traites,
                            erreurs=erreurs,
                            **compteurs,
                        )
                    )

                try:
                    infos = self.google.rechercher(
                        entreprise or "",
                        code_postal or "",
                        ville or "",
                    )

                    telephone = infos.get("telephone", "")
                    site_web = infos.get("site_web", "")
                    email = ""
                    reseaux = {
                        "facebook": "",
                        "linkedin": "",
                        "instagram": "",
                        "youtube": "",
                    }

                    if site_web:
                        if progress_callback:
                            progress_callback(
                                self._format_progress_stats(
                                    index=index,
                                    total=total,
                                    entreprise=entreprise,
                                    message="Recherche email et réseaux sociaux...",
                                    started_at=started_at,
                                    traites=traites,
                                    erreurs=erreurs,
                                    **compteurs,
                                )
                            )

                        email = self.email_finder.chercher(site_web)
                        reseaux = self.social_finder.chercher(site_web)

                    cur.execute(
                        """
                        UPDATE prospects
                        SET
                            telephone = CASE WHEN COALESCE(TRIM(?), '') != '' THEN ? ELSE telephone END,
                            site_web = CASE WHEN COALESCE(TRIM(?), '') != '' THEN ? ELSE site_web END,
                            email = CASE WHEN COALESCE(TRIM(?), '') != '' THEN ? ELSE email END,
                            facebook = CASE WHEN COALESCE(TRIM(?), '') != '' THEN ? ELSE facebook END,
                            linkedin = CASE WHEN COALESCE(TRIM(?), '') != '' THEN ? ELSE linkedin END,
                            instagram = CASE WHEN COALESCE(TRIM(?), '') != '' THEN ? ELSE instagram END,
                            youtube = CASE WHEN COALESCE(TRIM(?), '') != '' THEN ? ELSE youtube END,
                            statut_enrichissement = ?,
                            date_collecte = ?
                        WHERE id = ?
                        """,
                        (
                            telephone, telephone,
                            site_web, site_web,
                            email, email,
                            reseaux.get("facebook", ""), reseaux.get("facebook", ""),
                            reseaux.get("linkedin", ""), reseaux.get("linkedin", ""),
                            reseaux.get("instagram", ""), reseaux.get("instagram", ""),
                            reseaux.get("youtube", ""), reseaux.get("youtube", ""),
                            self.ENRICHED_STATUS,
                            str(date.today()),
                            prospect_id,
                        ),
                    )
                    ScoringService.score_prospect_with_connection(conn, prospect_id)
                    conn.commit()
                    traites += 1

                    if telephone:
                        compteurs["telephones"] += 1
                    if site_web:
                        compteurs["sites"] += 1
                    if email:
                        compteurs["emails"] += 1
                    for reseau in ("facebook", "linkedin", "instagram", "youtube"):
                        if reseaux.get(reseau):
                            compteurs[reseau] += 1

                    if progress_callback:
                        progress_callback(
                            self._format_progress_stats(
                                index=index,
                                total=total,
                                entreprise=entreprise,
                                message=(
                                    f"Tél: {telephone or '—'} | Site: {site_web or '—'} | "
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
                        SET statut_enrichissement = ?, date_collecte = ?
                        WHERE id = ?
                        """,
                        (self.ERROR_STATUS, str(date.today()), prospect_id),
                    )
                    conn.commit()

                    if progress_callback:
                        progress_callback(
                            self._format_progress_stats(
                                index=index,
                                total=total,
                                entreprise=entreprise,
                                message=f"Erreur, passage au prospect suivant : {exc}",
                                started_at=started_at,
                                traites=traites,
                                erreurs=erreurs,
                                **compteurs,
                            )
                        )

        finally:
            self.google.fermer()
            conn.close()

        return {
            "total": total,
            "traites": traites,
            "erreurs": erreurs,
            "interrompu": interrompu,
            **compteurs,
            "elapsed_seconds": max(0.0, time.monotonic() - started_at),
        }

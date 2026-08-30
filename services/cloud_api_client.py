from __future__ import annotations

from dataclasses import dataclass
import mimetypes
from pathlib import Path
from typing import Any

import requests

from models.cloud_user import CloudUser, CloudUserDataError


class CloudAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class PageResult:
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class ProjectImportResponse:
    total_prospects: int
    imported_prospects: int
    failed_prospects: int
    created: int = 0
    updated: int = 0
    ignored: int = 0
    warnings: tuple[str, ...] = ()

    @property
    def success(self) -> bool:
        """
        Indique si l'ensemble du lot a été importé sans échec.
        """
        return self.failed_prospects == 0

    @property
    def success_rate(self) -> float:
        """
        Retourne le taux de réussite de l'import entre 0.0 et 1.0.

        Un lot vide est considéré comme réussi.
        """
        if self.total_prospects == 0:
            return 1.0

        return self.imported_prospects / self.total_prospects


class CloudAPIClient:
    """Authenticated client for the Form@Prospect FastAPI backend."""

    def __init__(
        self,
        auth_service,
        base_url: str,
        timeout: int = 20,
    ):
        self.auth_service = auth_service
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.http = requests.Session()

    def _headers(self) -> dict[str, str]:
        session = self.auth_service.session

        if session is None:
            raise CloudAPIError(
                "La session Cloud a expiré. Reconnectez-vous.",
                status_code=401,
            )

        headers = {
            "Authorization": f"Bearer {session.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if session.organization_id:
            headers["X-Organization-ID"] = session.organization_id

        return headers

    def _ensure_fresh_session(self) -> None:
        """Refresh an access token shortly before expiry, when supported."""
        ensure = getattr(self.auth_service, "ensure_session_fresh", None)
        if ensure is None:
            return
        try:
            ensure(margin_seconds=120)
        except Exception as exc:
            raise CloudAPIError(
                "Votre session Cloud n'a pas pu être renouvelée. "
                "Veuillez vous reconnecter.",
                status_code=401,
            ) from exc

    def _refresh_after_401(self) -> None:
        """Perform exactly one token refresh before retrying an unauthorized call."""
        refresh = getattr(self.auth_service, "refresh_session", None)
        if refresh is None:
            raise CloudAPIError(
                "Votre session Cloud a expiré. Reconnectez-vous.",
                status_code=401,
            )
        try:
            refresh()
        except Exception as exc:
            raise CloudAPIError(
                "Votre session Cloud a expiré. Veuillez vous reconnecter.",
                status_code=401,
            ) from exc

    def request(
        self,
        method: str,
        path: str,
        *,
        params=None,
        json=None,
        expected=(200,),
    ) -> requests.Response:
        self._ensure_fresh_session()

        response = None
        for attempt in range(2):
            try:
                response = self.http.request(
                    method,
                    f"{self.base_url}/{path.lstrip('/')}",
                    headers=self._headers(),
                    params=params,
                    json=json,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                raise CloudAPIError(
                    "Impossible de joindre Form@Prospect Cloud. "
                    "Vérifiez votre connexion."
                ) from exc

            if response.status_code in expected:
                return response

            if response.status_code == 401 and attempt == 0:
                self._refresh_after_401()
                continue
            break

        assert response is not None

        message = None

        try:
            payload = response.json()
            detail = (
                payload.get("detail")
                if isinstance(payload, dict)
                else None
            )

            if isinstance(detail, list):
                message = "; ".join(
                    str(item.get("msg", item))
                    for item in detail
                )
            else:
                message = str(
                    detail
                    or payload.get("message")
                    or ""
                )

        except (ValueError, AttributeError):
            message = response.text.strip()

        if response.status_code == 401:
            message = (
                "Votre session Cloud a expiré. "
                "Reconnectez-vous."
            )

        elif response.status_code == 403 and not message:
            message = (
                "Vous n'avez pas l'autorisation "
                "d'effectuer cette action."
            )

        raise CloudAPIError(
            message
            or (
                "L'API Form@Prospect a refusé la requête "
                f"({response.status_code})."
            ),
            status_code=response.status_code,
        )

    def get_json(
        self,
        path: str,
        *,
        params=None,
    ):
        return self.request(
            "GET",
            path,
            params=params,
        ).json()

    def post_json(
        self,
        path: str,
        payload: dict,
        *,
        expected=(200, 201),
    ):
        return self.request(
            "POST",
            path,
            json=payload,
            expected=expected,
        ).json()

    def patch_json(
        self,
        path: str,
        payload: dict,
    ):
        return self.request(
            "PATCH",
            path,
            json=payload,
        ).json()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def list_users(
        self,
        *,
        active_only: bool = True,
    ) -> list[CloudUser]:
        """Return validated users of the active Cloud organization."""

        payload = self.get_json(
            "/users",
            params={
                "active_only": str(active_only).lower(),
            },
        )

        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné "
                "une liste d'utilisateurs invalide."
            )

        users: list[CloudUser] = []

        try:
            for item in payload:
                users.append(
                    CloudUser.from_payload(item)
                )

        except CloudUserDataError as exc:
            raise CloudAPIError(str(exc)) from exc

        return users

    # ------------------------------------------------------------------
    # Prospects
    # ------------------------------------------------------------------

    def list_prospects(
        self,
        **params,
    ) -> PageResult:
        clean = {
            key: value
            for key, value in params.items()
            if value not in (None, "")
        }

        response = self.request(
            "GET",
            "/prospects",
            params=clean,
        )

        items = response.json()

        return PageResult(
            items=items,
            total=int(
                response.headers.get(
                    "X-Total-Count",
                    len(items),
                )
            ),
            limit=int(
                response.headers.get(
                    "X-Limit",
                    clean.get("limit", 100),
                )
            ),
            offset=int(
                response.headers.get(
                    "X-Offset",
                    clean.get("offset", 0),
                )
            ),
        )



    def get_prospect_stats(
        self,
        *,
        project_id: str | None = None,
    ) -> dict[str, int]:
        """
        Retourne les compteurs CRM calculés directement par PostgreSQL.
        """

        payload = self.get_json(
            "/prospects/stats",
            params={"project_id": project_id} if project_id else None,
        )

        if not isinstance(payload, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné "
                "des statistiques CRM invalides."
            )

        try:
            return {
                "total": int(payload.get("total", 0)),
                "with_phone": int(
                    payload.get("with_phone", 0)
                ),
                "with_email": int(
                    payload.get("with_email", 0)
                ),
                "with_website": int(
                    payload.get("with_website", 0)
                ),
            }
        except (TypeError, ValueError) as exc:
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné "
                "des statistiques CRM illisibles."
            ) from exc

    def get_prospect_filter_options(
        self,
        *,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Retourne les options de filtres CRM calculées directement
        par le backend, sans télécharger les prospects.
        """

        payload = self.get_json(
            "/prospects/filter-options",
            params={"project_id": project_id} if project_id else None,
        )

        if not isinstance(payload, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné "
                "des options de filtres invalides."
            )

        return {
            "pipelines": list(
                payload.get("pipelines") or []
            ),
            "priorities": list(
                payload.get("priorities") or []
            ),
            "cities": list(
                payload.get("cities") or []
            ),
            "owners": list(
                payload.get("owners") or []
            ),
        }

    def get_prospect(
        self,
        prospect_id: str,
    ) -> dict:
        return self.get_json(
            f"/prospects/{prospect_id}"
        )

    def update_prospect(
        self,
        prospect_id: str,
        payload: dict,
    ) -> dict:
        return self.patch_json(
            f"/prospects/{prospect_id}",
            payload,
        )

    def change_stage(
        self,
        prospect_id: str,
        pipeline_stage: str,
        note: str = "",
    ) -> dict:
        return self.post_json(
            f"/prospects/{prospect_id}/stage",
            {
                "pipeline_stage": pipeline_stage,
                "note": note,
            },
            expected=(200,),
        )

    def list_stages(
        self,
    ) -> list[dict]:
        return self.get_json(
            "/pipeline/stages"
        )

    def list_activities(
        self,
        prospect_id: str,
        status: str | None = None,
    ) -> list[dict]:
        params = (
            {"status": status}
            if status
            else None
        )

        return self.get_json(
            f"/prospects/{prospect_id}/activities",
            params=params,
        )

    def create_activity(
        self,
        prospect_id: str,
        payload: dict,
    ) -> dict:
        return self.post_json(
            f"/prospects/{prospect_id}/activities",
            payload,
        )

    def due_activities(
        self,
        overdue_only: bool = False,
    ) -> list[dict]:
        return self.get_json(
            "/activities/due",
            params={
                "overdue_only": str(overdue_only).lower(),
            },
        )

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def list_projects(
        self,
        **params,
    ) -> PageResult:
        clean = {
            key: value
            for key, value in params.items()
            if value not in (None, "")
        }

        response = self.request(
            "GET",
            "/projects",
            params=clean,
        )

        items = response.json()

        return PageResult(
            items=items,
            total=int(
                response.headers.get(
                    "X-Total-Count",
                    len(items),
                )
            ),
            limit=int(
                response.headers.get(
                    "X-Limit",
                    clean.get("limit", 100),
                )
            ),
            offset=int(
                response.headers.get(
                    "X-Offset",
                    clean.get("offset", 0),
                )
            ),
        )

    def get_project(
        self,
        project_id: str,
    ) -> dict:
        return self.get_json(
            f"/projects/{project_id}",
        )

    def create_project(
        self,
        payload: dict,
    ) -> dict:
        return self.post_json(
            "/projects",
            payload,
            expected=(201,),
        )

    def update_project(
        self,
        project_id: str,
        payload: dict,
    ) -> dict:
        return self.patch_json(
            f"/projects/{project_id}",
            payload,
        )

    def archive_project(
        self,
        project_id: str,
    ) -> dict[str, Any]:
        """Archive logiquement un projet Cloud standard."""
        response = self.request(
            "POST",
            f"/projects/{project_id}/archive",
            expected=(200,),
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un projet archivé invalide."
            )
        return payload

    def restore_project(
        self,
        project_id: str,
    ) -> dict[str, Any]:
        """Restaure un projet Cloud précédemment archivé."""
        response = self.request(
            "POST",
            f"/projects/{project_id}/restore",
            expected=(200,),
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un projet restauré invalide."
            )
        return payload

    def import_project_prospects(
        self,
        project_id: str,
        prospects: list[dict],
    ) -> ProjectImportResponse:
        """Importe un lot de prospects et normalise le contrat backend."""

        data = self.post_json(
            f"/projects/{project_id}/import",
            {"prospects": prospects},
            expected=(200,),
        )

        created = int(data.get("created", 0))
        updated = int(data.get("updated", 0))
        ignored = int(data.get("ignored", 0))
        errors = int(data.get("errors", 0))
        processed = int(
            data.get("processed", created + updated + ignored + errors)
        )

        return ProjectImportResponse(
            total_prospects=int(data.get("total_prospects", processed)),
            imported_prospects=int(
                data.get("imported_prospects", created + updated)
            ),
            failed_prospects=int(data.get("failed_prospects", errors)),
            created=created,
            updated=updated,
            ignored=ignored,
            warnings=tuple(str(item) for item in data.get("warnings", [])),
        )

    # ------------------------------------------------------------------
    # Cloud documents
    # ------------------------------------------------------------------

    def _multipart_json(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, str],
        file_path: str | Path,
        expected=(200, 201),
    ) -> dict:
        """Send a multipart request without exposing Cloud credentials."""
        source = Path(file_path)
        if not source.is_file():
            raise CloudAPIError(f"Le fichier est introuvable : {source}")

        self._ensure_fresh_session()
        mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"

        response = None
        for attempt in range(2):
            headers = self._headers()
            headers.pop("Content-Type", None)
            try:
                # Re-open the file for a retry so the upload restarts from byte 0.
                with source.open("rb") as handle:
                    response = self.http.request(
                        method,
                        f"{self.base_url}/{path.lstrip('/')}",
                        headers=headers,
                        data=data,
                        files={
                            "file": (
                                source.name,
                                handle,
                                mime_type,
                            )
                        },
                        timeout=max(self.timeout, 60),
                    )
            except (OSError, requests.RequestException) as exc:
                raise CloudAPIError(
                    "Impossible d'envoyer le document à Form@Prospect Cloud."
                ) from exc

            if response.status_code in expected:
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
                raise CloudAPIError(
                    "Form@Prospect Cloud a retourné une réponse documentaire invalide."
                )

            if response.status_code == 401 and attempt == 0:
                self._refresh_after_401()
                continue
            break

        assert response is not None

        message = None
        try:
            payload = response.json()
            detail = payload.get("detail") if isinstance(payload, dict) else None
            if isinstance(detail, list):
                message = "; ".join(
                    str(item.get("msg", item))
                    for item in detail
                )
            else:
                message = str(
                    detail
                    or (payload.get("message") if isinstance(payload, dict) else "")
                    or ""
                )
        except (ValueError, AttributeError):
            message = response.text.strip()

        if response.status_code == 401:
            message = "Votre session Cloud a expiré. Reconnectez-vous."
        elif response.status_code == 403 and not message:
            message = "Vous n'avez pas l'autorisation d'effectuer cette action."

        raise CloudAPIError(
            message
            or f"L'API Form@Prospect a refusé la requête ({response.status_code}).",
            status_code=response.status_code,
        )

    def list_cloud_trainers(
        self,
        *,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        payload = self.get_json(
            "/trainers",
            params={"include_inactive": str(include_inactive).lower()},
        )
        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un annuaire de formateurs invalide."
            )
        return payload

    def get_cloud_trainer(self, trainer_id: str) -> dict[str, Any]:
        payload = self.get_json(f"/trainers/{trainer_id}")
        if not isinstance(payload, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une fiche formateur invalide."
            )
        return payload


    def create_cloud_trainer(
        self,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.post_json(
            "/trainers",
            payload,
            expected=(201,),
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une création de formateur invalide."
            )
        return result

    def update_cloud_trainer(
        self,
        trainer_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.patch_json(
            f"/trainers/{trainer_id}",
            payload,
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une mise à jour de formateur invalide."
            )
        return result

    def link_cloud_trainer_user(
        self,
        trainer_id: str,
        user_id: str | None,
    ) -> dict[str, Any]:
        """Relie explicitement une fiche formateur à un compte Cloud Formateur."""
        result = self.patch_json(
            f"/trainers/{trainer_id}/link-user",
            {"user_id": user_id or None},
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un rattachement de compte invalide."
            )
        return result

    def get_my_cloud_trainer_profile(self) -> dict[str, Any]:
        payload = self.get_json("/trainers/me")
        if not isinstance(payload, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un profil formateur invalide."
            )
        return payload

    def list_my_cloud_trainer_sessions(self) -> list[dict[str, Any]]:
        payload = self.get_json("/trainers/me/sessions")
        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné des sessions formateur invalides."
            )
        return payload


    def list_document_trainings(
        self,
        *,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        payload = self.get_json(
            "/documents/trainings",
            params={"include_inactive": str(include_inactive).lower()},
        )
        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un catalogue de formations invalide."
            )
        return payload

    def create_document_training(self, payload: dict) -> dict:
        return self.post_json(
            "/documents/trainings",
            payload,
            expected=(201,),
        )

    def update_document_training(
        self,
        training_id: str,
        payload: dict,
    ) -> dict:
        return self.patch_json(
            f"/documents/trainings/{training_id}",
            payload,
        )

    def delete_document_training(
        self,
        training_id: str,
    ) -> None:
        self.request(
            "DELETE",
            f"/documents/trainings/{training_id}",
            expected=(204,),
        )

    def create_document_session(self, payload: dict) -> dict:
        return self.post_json(
            "/documents/sessions",
            payload,
            expected=(201,),
        )

    def update_document_session(
        self,
        session_id: str,
        payload: dict,
    ) -> dict:
        return self.patch_json(
            f"/documents/sessions/{session_id}",
            payload,
        )

    def list_document_generation_sessions(
        self,
        prospect_id: str,
    ) -> list[dict[str, Any]]:
        payload = self.get_json(
            "/documents/generation-sessions",
            params={"prospect_id": prospect_id},
        )
        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné des sessions documentaires invalides."
            )
        return payload

    def generate_cloud_documents(
        self,
        session_id: str,
        document_types: list[str],
    ) -> list[dict[str, Any]]:
        payload = self.post_json(
            "/documents/generate",
            {
                "session_id": session_id,
                "document_types": document_types,
            },
            expected=(201,),
        )
        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une génération invalide."
            )
        return payload

    def list_cloud_documents(
        self,
        *,
        prospect_id: str | None = None,
        document_type: str | None = None,
        include_history: bool = False,
        include_archived: bool = False,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        params = {
            "prospect_id": prospect_id,
            "document_type": document_type,
            "include_history": str(include_history).lower(),
            "include_archived": str(include_archived).lower(),
            "limit": int(limit),
            "offset": int(offset),
        }
        payload = self.get_json(
            "/documents",
            params={
                key: value
                for key, value in params.items()
                if value not in (None, "")
            },
        )
        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un historique documentaire invalide."
            )
        return payload

    def get_cloud_document_download_url(
        self,
        document_id: str,
    ) -> dict[str, Any]:
        payload = self.get_json(
            f"/documents/{document_id}/download-url"
        )
        if not isinstance(payload, dict) or not payload.get("download_url"):
            raise CloudAPIError(
                "Form@Prospect Cloud n'a retourné aucun lien de téléchargement."
            )
        return payload

    def download_cloud_document(
        self,
        document_id: str,
        destination: str | Path,
    ) -> Path:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        signed = self.get_cloud_document_download_url(document_id)

        try:
            response = requests.get(
                str(signed["download_url"]),
                timeout=max(self.timeout, 60),
                allow_redirects=True,
            )
            response.raise_for_status()
            target.write_bytes(response.content)
        except (OSError, requests.RequestException) as exc:
            target.unlink(missing_ok=True)
            raise CloudAPIError(
                "Le document n'a pas pu être téléchargé."
            ) from exc

        return target

    @staticmethod
    def _safe_client_folder_name(value: str) -> str:
        import re
        safe = re.sub(r'[<>:"/\\\\|?*]+', "_", str(value or "").strip())
        safe = re.sub(r"\\s+", " ", safe).strip(" .")
        return safe or "CLIENT"

    def download_cloud_client_folder(
        self,
        *,
        prospect_id: str,
        client_name: str,
        destination_root: str | Path,
    ) -> tuple[Path, int]:
        root = Path(destination_root) / self._safe_client_folder_name(client_name)
        folders = {
            "Devis": "01 - Devis",
            "Convention": "02 - Conventions",
            "Programme": "03 - Programmes",
            "Convocation": "04 - Convocations",
            "Facture": "05 - Factures",
            "Attestation de formation": "06 - Attestations",
        }
        for folder in folders.values():
            (root / folder).mkdir(parents=True, exist_ok=True)

        documents = self.list_cloud_documents(
            prospect_id=prospect_id,
            include_history=False,
            include_archived=False,
            limit=500,
        )
        count = 0
        for item in documents:
            document_type = str(item.get("document_type") or "")
            if document_type not in folders or str(item.get("status") or "") != "available":
                continue
            filename = str(
                item.get("original_filename")
                or item.get("document_number")
                or "document.docx"
            ).strip()
            target = root / folders[document_type] / filename
            if target.exists():
                stem, suffix = target.stem, target.suffix
                index = 2
                while target.exists():
                    target = target.with_name(f"{stem}_{index}{suffix}")
                    index += 1
            self.download_cloud_document(str(item["id"]), target)
            count += 1
        return root, count

    def upload_cloud_administrative_document(
        self,
        *,
        prospect_id: str,
        document_type: str,
        file_path: str | Path,
        document_number: str = "",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "prospect_id": prospect_id,
            "document_type": document_type,
            "document_number": document_number.strip(),
        }
        if session_id:
            data["session_id"] = session_id
        return self._multipart_json(
            "POST",
            "/documents/admin-upload",
            data=data,
            file_path=file_path,
            expected=(201,),
        )

    def upload_cloud_signed_document(
        self,
        *,
        prospect_id: str,
        document_type: str,
        file_path: str | Path,
        document_number: str = "",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Upload a signed PDF for a prospect visible to the connected user."""
        source = Path(file_path)
        if source.suffix.lower() != ".pdf":
            raise CloudAPIError(
                "Seuls les fichiers PDF sont autorisés pour les documents signés."
            )

        data = {
            "prospect_id": prospect_id,
            "document_type": document_type,
            "document_number": document_number.strip(),
        }
        if session_id:
            data["session_id"] = session_id

        return self._multipart_json(
            "POST",
            "/documents/signed-upload",
            data=data,
            file_path=source,
            expected=(201,),
        )

    def upload_cloud_document_template(
        self,
        *,
        document_type: str,
        file_path: str | Path,
        name: str = "",
        training_id: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "document_type": document_type,
            "name": name.strip(),
        }
        if training_id:
            data["training_id"] = training_id
        return self._multipart_json(
            "POST",
            "/documents/templates/admin-upload",
            data=data,
            file_path=file_path,
            expected=(201,),
        )
    # ------------------------------------------------------------------
    # Commercial profiles
    # ------------------------------------------------------------------

    def list_cloud_commercial_profiles(
        self,
        *,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        payload = self.get_json(
            "/commercial-profiles",
            params={"include_inactive": str(include_inactive).lower()},
        )
        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un annuaire commercial invalide."
            )
        return payload

    def get_cloud_commercial_profile(
        self,
        profile_id: str,
    ) -> dict[str, Any]:
        payload = self.get_json(f"/commercial-profiles/{profile_id}")
        if not isinstance(payload, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une fiche commerciale invalide."
            )
        return payload

    def create_cloud_commercial_profile(
        self,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.post_json(
            "/commercial-profiles",
            payload,
            expected=(201,),
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une création commerciale invalide."
            )
        return result

    def update_cloud_commercial_profile(
        self,
        profile_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.patch_json(
            f"/commercial-profiles/{profile_id}",
            payload,
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une mise à jour commerciale invalide."
            )
        return result

    # ------------------------------------------------------------------
    # Quote / invoice requests
    # ------------------------------------------------------------------

    def list_cloud_quote_requests(
        self,
        *,
        request_status: str | None = None,
        prospect_id: str | None = None,
        document_type: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {
            "request_status": request_status,
            "prospect_id": prospect_id,
            "document_type": document_type,
        }
        payload = self.get_json(
            "/quote-requests",
            params={
                key: value
                for key, value in params.items()
                if value not in (None, "")
            },
        )
        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné des demandes Devis / Facture invalides."
            )
        return payload

    def create_cloud_quote_request(
        self,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.post_json(
            "/quote-requests",
            payload,
            expected=(201,),
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une demande documentaire invalide."
            )
        return result

    def update_cloud_quote_request_status(
        self,
        request_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.patch_json(
            f"/quote-requests/{request_id}/status",
            payload,
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un statut de demande invalide."
            )
        return result

    def attach_cloud_quote_document(
        self,
        request_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.patch_json(
            f"/quote-requests/{request_id}/document",
            payload,
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une association de document invalide."
            )
        return result

    # ------------------------------------------------------------------
    # Sales / commissions
    # ------------------------------------------------------------------

    def list_cloud_sales(
        self,
        *,
        year: int | None = None,
        month: int | None = None,
        commercial_user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {
            "year": year,
            "month": month,
            "commercial_user_id": commercial_user_id,
        }
        payload = self.get_json(
            "/sales",
            params={
                key: value
                for key, value in params.items()
                if value not in (None, "")
            },
        )
        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une liste de ventes invalide."
            )
        return payload

    def get_cloud_sales_summary(
        self,
        *,
        year: int,
        month: int,
        commercial_user_id: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "year": int(year),
            "month": int(month),
            "commercial_user_id": commercial_user_id,
        }
        payload = self.get_json(
            "/sales/summary",
            params={
                key: value
                for key, value in params.items()
                if value not in (None, "")
            },
        )
        if not isinstance(payload, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un récapitulatif des ventes invalide."
            )
        return payload

    def preview_cloud_sale_commission(
        self,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.post_json(
            "/sales/commission-preview",
            payload,
            expected=(200,),
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un aperçu de commission invalide."
            )
        return result

    def create_cloud_sale(
        self,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.post_json(
            "/sales",
            payload,
            expected=(201,),
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une vente invalide."
            )
        return result

    def mark_cloud_sale_client_paid(
        self,
        sale_id: str,
        *,
        reference: str = "",
        paid_at: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "reference": str(reference or "").strip(),
        }
        if paid_at:
            payload["paid_at"] = paid_at

        result = self.patch_json(
            f"/sales/{sale_id}/client-payment",
            payload,
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un règlement client invalide."
            )
        return result

    def mark_cloud_sale_commission_paid(
        self,
        sale_id: str,
        *,
        reference: str = "",
        paid_at: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "reference": str(reference or "").strip(),
        }
        if paid_at:
            payload["paid_at"] = paid_at

        result = self.patch_json(
            f"/sales/{sale_id}/commission-payment",
            payload,
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un règlement de commission invalide."
            )
        return result

    def cancel_cloud_sale(
        self,
        sale_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.post_json(
            f"/sales/{sale_id}/cancel",
            payload,
            expected=(200,),
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une annulation de vente invalide."
            )
        return result

    # ------------------------------------------------------------------
    # Commission invoices
    # ------------------------------------------------------------------

    def list_cloud_commission_invoices(
        self,
        *,
        year: int | None = None,
        commercial_user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {
            "year": year,
            "commercial_user_id": commercial_user_id,
        }
        payload = self.get_json(
            "/commission-invoices",
            params={
                key: value
                for key, value in params.items()
                if value not in (None, "")
            },
        )
        if not isinstance(payload, list):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une liste de factures de commission invalide."
            )
        return payload

    def get_cloud_commission_invoice(
        self,
        invoice_id: str,
    ) -> dict[str, Any]:
        payload = self.get_json(f"/commission-invoices/{invoice_id}")
        if not isinstance(payload, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une facture de commission invalide."
            )
        return payload

    def create_cloud_commission_invoice(
        self,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.post_json(
            "/commission-invoices",
            payload,
            expected=(201,),
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une facture de commission invalide."
            )
        return result

    def mark_cloud_commission_invoice_paid(
        self,
        invoice_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        result = self.patch_json(
            f"/commission-invoices/{invoice_id}/payment",
            payload,
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné un paiement de facture de commission invalide."
            )
        return result
    # ------------------------------------------------------------------
    # Admin statistics
    # ------------------------------------------------------------------

    def get_admin_statistics(
        self,
        *,
        year: int | None = None,
    ) -> dict[str, Any]:
        params = {}
        if year is not None:
            params["year"] = int(year)

        payload = self.get_json(
            "/admin-statistics",
            params=params or None,
        )
        if not isinstance(payload, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné des statistiques administrateur invalides."
            )
        return payload
    def create_commission_invoice(
        self,
        *,
        year: int,
        month: int,
    ) -> dict[str, Any]:
        payload = {
            "year": int(year),
            "month": int(month),
        }
        result = self.post_json(
            "/commission-invoices",
            payload,
            expected=(201,),
        )
        if not isinstance(result, dict):
            raise CloudAPIError(
                "Form@Prospect Cloud a retourné une facture de commission invalide."
            )
        return result
    # ------------------------------------------------------------------
    # Compatibility aliases - commission invoice dialog
    # ------------------------------------------------------------------

    def list_commission_invoices(
        self,
        *,
        year: int | None = None,
        commercial_user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Compatibilité avec CommissionInvoicesDialog."""
        return self.list_cloud_commission_invoices(
            year=year,
            commercial_user_id=commercial_user_id,
        )







from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class CloudAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class PageResult:
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class CloudAPIClient:
    """Authenticated client for the Form@Prospect FastAPI backend."""

    def __init__(self, auth_service, base_url: str, timeout: int = 20):
        self.auth_service = auth_service
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.http = requests.Session()

    def _headers(self) -> dict[str, str]:
        session = self.auth_service.session
        if session is None:
            raise CloudAPIError("La session Cloud a expiré. Reconnectez-vous.", status_code=401)
        headers = {
            "Authorization": f"Bearer {session.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if session.organization_id:
            headers["X-Organization-ID"] = session.organization_id
        return headers

    def request(self, method: str, path: str, *, params=None, json=None, expected=(200,)) -> requests.Response:
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
            raise CloudAPIError("Impossible de joindre Form@Prospect Cloud. Vérifiez votre connexion.") from exc
        if response.status_code in expected:
            return response
        message = None
        try:
            payload = response.json()
            detail = payload.get("detail") if isinstance(payload, dict) else None
            if isinstance(detail, list):
                message = "; ".join(str(item.get("msg", item)) for item in detail)
            else:
                message = str(detail or payload.get("message") or "")
        except (ValueError, AttributeError):
            message = response.text.strip()
        if response.status_code == 401:
            message = "Votre session Cloud a expiré. Reconnectez-vous."
        elif response.status_code == 403 and not message:
            message = "Vous n'avez pas l'autorisation d'effectuer cette action."
        raise CloudAPIError(message or f"L'API Form@Prospect a refusé la requête ({response.status_code}).", status_code=response.status_code)

    def get_json(self, path: str, *, params=None):
        return self.request("GET", path, params=params).json()

    def post_json(self, path: str, payload: dict, *, expected=(200, 201)):
        return self.request("POST", path, json=payload, expected=expected).json()

    def patch_json(self, path: str, payload: dict):
        return self.request("PATCH", path, json=payload).json()

    def list_prospects(self, **params) -> PageResult:
        clean = {key: value for key, value in params.items() if value not in (None, "")}
        response = self.request("GET", "/prospects", params=clean)
        items = response.json()
        return PageResult(
            items=items,
            total=int(response.headers.get("X-Total-Count", len(items))),
            limit=int(response.headers.get("X-Limit", clean.get("limit", 100))),
            offset=int(response.headers.get("X-Offset", clean.get("offset", 0))),
        )

    def get_prospect(self, prospect_id: str) -> dict:
        return self.get_json(f"/prospects/{prospect_id}")

    def update_prospect(self, prospect_id: str, payload: dict) -> dict:
        return self.patch_json(f"/prospects/{prospect_id}", payload)

    def change_stage(self, prospect_id: str, pipeline_stage: str, note: str = "") -> dict:
        return self.post_json(f"/prospects/{prospect_id}/stage", {"pipeline_stage": pipeline_stage, "note": note}, expected=(200,))

    def list_stages(self) -> list[dict]:
        return self.get_json("/pipeline/stages")

    def list_activities(self, prospect_id: str, status: str | None = None) -> list[dict]:
        params = {"status": status} if status else None
        return self.get_json(f"/prospects/{prospect_id}/activities", params=params)

    def create_activity(self, prospect_id: str, payload: dict) -> dict:
        return self.post_json(f"/prospects/{prospect_id}/activities", payload)

    def due_activities(self, overdue_only: bool = False) -> list[dict]:
        return self.get_json("/activities/due", params={"overdue_only": str(overdue_only).lower()})

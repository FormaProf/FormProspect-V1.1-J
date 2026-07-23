from __future__ import annotations

import uuid

import httpx
from fastapi import Depends

from backend.app.core.config import Settings, get_settings


class SupabaseAdminError(RuntimeError):
    pass


class SupabaseAdminService:
    """Client d'administration Supabase exécuté uniquement par l'API."""

    def __init__(self, settings: Settings, timeout: float = 15.0):
        self.url = settings.supabase_url.rstrip("/")
        self.key = settings.supabase_service_role_key
        self.timeout = timeout
        if not self.url or not self.key:
            raise SupabaseAdminError("L'administration Supabase n'est pas configurée sur le serveur.")

    @property
    def headers(self) -> dict[str, str]:
        return {"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    def invite_user(self, email: str, first_name: str, last_name: str) -> uuid.UUID:
        response = httpx.post(
            f"{self.url}/auth/v1/invite", headers=self.headers,
            json={"email": email, "data": {"first_name": first_name, "last_name": last_name}},
            timeout=self.timeout,
        )
        payload = self._payload(response, "Impossible d'inviter cet utilisateur.")
        try:
            return uuid.UUID(str(payload["id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise SupabaseAdminError("Réponse Supabase incomplète.") from exc

    def delete_user(self, auth_user_id: uuid.UUID) -> None:
        response = httpx.delete(f"{self.url}/auth/v1/admin/users/{auth_user_id}", headers=self.headers, timeout=self.timeout)
        if response.status_code not in (200, 204, 404):
            self._payload(response, "Impossible d'annuler la création du compte.")

    def send_password_reset(self, email: str) -> None:
        response = httpx.post(f"{self.url}/auth/v1/recover", headers=self.headers, json={"email": email}, timeout=self.timeout)
        self._payload(response, "Impossible d'envoyer l'e-mail de réinitialisation.")

    @staticmethod
    def _payload(response: httpx.Response, fallback: str) -> dict:
        if response.is_success:
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                return {}
        try:
            detail = response.json().get("msg") or response.json().get("message")
        except ValueError:
            detail = None
        raise SupabaseAdminError(detail or fallback)


def get_supabase_admin(settings: Settings = Depends(get_settings)) -> SupabaseAdminService:
    return SupabaseAdminService(settings)

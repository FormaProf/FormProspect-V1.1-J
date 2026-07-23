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
            raise SupabaseAdminError(
                "L'administration Supabase n'est pas configurée sur le serveur."
            )

    @property
    def headers(self) -> dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    def invite_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
    ) -> uuid.UUID:
        response = httpx.post(
            f"{self.url}/auth/v1/invite",
            headers=self.headers,
            params={
                "redirect_to": "https://auth.forma-prof.fr/accept-invite/"
            },
            json={
                "email": email,
                "data": {
                    "first_name": first_name,
                    "last_name": last_name,
                },
            },
            timeout=self.timeout,
        )

        payload = self._payload(
            response,
            "Impossible d'inviter cet utilisateur.",
        )

        try:
            return uuid.UUID(str(payload["id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise SupabaseAdminError(
                "Réponse Supabase incomplète."
            ) from exc

    def delete_user(self, auth_user_id: uuid.UUID) -> None:
        response = httpx.delete(
            f"{self.url}/auth/v1/admin/users/{auth_user_id}",
            headers=self.headers,
            timeout=self.timeout,
        )

        if response.status_code not in (200, 204, 404):
            self._payload(
                response,
                "Impossible d'annuler la création du compte.",
            )

    def provision_member(
        self,
        auth_user_id: uuid.UUID,
        organization_id: uuid.UUID,
        email: str,
        first_name: str,
        last_name: str,
        role: str,
    ) -> tuple[uuid.UUID, uuid.UUID]:
        profile_id = uuid.uuid4()
        membership_id = uuid.uuid4()

        profile = httpx.post(
            f"{self.url}/rest/v1/user_profiles",
            headers={
                **self.headers,
                "Prefer": "return=minimal",
            },
            json={
                "id": str(profile_id),
                "auth_user_id": str(auth_user_id),
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": "",
                "status": "active",
            },
            timeout=self.timeout,
        )

        self._payload(
            profile,
            "Impossible de créer le profil Cloud.",
        )

        membership = httpx.post(
            f"{self.url}/rest/v1/organization_memberships",
            headers={
                **self.headers,
                "Prefer": "return=minimal",
            },
            json={
                "id": str(membership_id),
                "organization_id": str(organization_id),
                "user_id": str(profile_id),
                "role": role,
                "is_active": True,
            },
            timeout=self.timeout,
        )

        if not membership.is_success:
            self.cleanup_member(profile_id, membership_id)
            self._payload(
                membership,
                "Impossible de rattacher le profil à l'organisation.",
            )

        return profile_id, membership_id

    def cleanup_member(
        self,
        profile_id: uuid.UUID,
        membership_id: uuid.UUID,
    ) -> None:
        httpx.delete(
            f"{self.url}/rest/v1/organization_memberships",
            headers=self.headers,
            params={
                "id": f"eq.{membership_id}",
            },
            timeout=self.timeout,
        )

        httpx.delete(
            f"{self.url}/rest/v1/user_profiles",
            headers=self.headers,
            params={
                "id": f"eq.{profile_id}",
            },
            timeout=self.timeout,
        )

    def send_password_reset(self, email: str) -> None:
        response = httpx.post(
            f"{self.url}/auth/v1/recover",
            headers=self.headers,
            params={
                "redirect_to": "https://auth.forma-prof.fr/reset-password/"
            },
            json={
                "email": email,
            },
            timeout=self.timeout,
        )

        self._payload(
            response,
            "Impossible d'envoyer l'e-mail de réinitialisation.",
        )

    @staticmethod
    def _payload(
        response: httpx.Response,
        fallback: str,
    ) -> dict:
        if response.is_success:
            if not response.content:
                return {}

            try:
                return response.json()
            except ValueError:
                return {}

        try:
            error_payload = response.json()
            detail = (
                error_payload.get("msg")
                or error_payload.get("message")
                or error_payload.get("error_description")
            )
        except ValueError:
            detail = None

        raise SupabaseAdminError(detail or fallback)


def get_supabase_admin(
    settings: Settings = Depends(get_settings),
) -> SupabaseAdminService:
    return SupabaseAdminService(settings)
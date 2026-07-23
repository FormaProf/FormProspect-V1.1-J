from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

import requests

from core.session import AuthenticatedUser
from services.auth_service import AuthService

try:
    import keyring
except ImportError:  # pragma: no cover - protected failure mode on unsupported builds
    keyring = None


API_BASE_URL = "https://api.forma-prof.fr/api/v1"
SUPABASE_URL = "https://vlpsjcqlljrvojkpdhke.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_497OoUIK8IITjPOlEsYGSw_jn9Zi73N"
KEYRING_SERVICE = "Form@Prospect Cloud"
KEYRING_ACCOUNT = "refresh-token"

ROLE_LABELS = {
    "admin": "Administrateur",
    "manager": "Manager",
    "commercial": "Commercial",
    "trainer": "Formateur",
    "admin_assistant": "Assistant administratif",
}


class CloudAuthError(RuntimeError):
    pass


class AccountDisabledError(CloudAuthError):
    pass


@dataclass
class CloudSession:
    access_token: str
    refresh_token: str
    expires_at: datetime
    organization_id: str = ""


class CloudAuthService:
    """Supabase authentication plus server-side tenant authorization."""

    is_cloud = True

    def __init__(self, local_profiles: AuthService | None = None, timeout: int = 15):
        self.local_profiles = local_profiles or AuthService()
        self.timeout = timeout
        self.session: CloudSession | None = None
        self.current_user: AuthenticatedUser | None = None

    def __getattr__(self, name):
        # Photos/licence remain local until their dedicated Cloud migrations.
        return getattr(self.local_profiles, name)

    def list_users(self) -> list[dict]:
        response = requests.get(f"{API_BASE_URL}/admin/users", headers=self._api_headers(), timeout=self.timeout)
        self._raise_api_error(response)
        return [self._map_admin_user(item) for item in response.json()]

    def create_user(self, username="", password="", *, first_name="", last_name="", email="", role="Commercial"):
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        response = requests.post(
            f"{API_BASE_URL}/admin/users", headers=self._api_headers(), timeout=self.timeout,
            json={"email": email.strip().lower(), "first_name": first_name.strip(), "last_name": last_name.strip(), "role": self._role_code(role)},
        )
        self._raise_api_error(response)
        return self._map_admin_user(response.json())

    def set_active(self, membership_id, active: bool):
        return self._update_user(membership_id, {"active": bool(active)})

    def set_role(self, membership_id, role: str):
        return self._update_user(membership_id, {"role": self._role_code(role)})

    def reset_password(self, membership_id, new_password=""):
        response = requests.post(
            f"{API_BASE_URL}/admin/users/{membership_id}/password-reset",
            headers=self._api_headers(), timeout=self.timeout,
        )
        self._raise_api_error(response)

    def list_audit(self, limit: int = 100) -> list[dict]:
        response = requests.get(
            f"{API_BASE_URL}/admin/audit", headers=self._api_headers(),
            params={"limit": limit}, timeout=self.timeout,
        )
        self._raise_api_error(response)
        return response.json()

    def _update_user(self, membership_id, payload: dict) -> dict:
        response = requests.patch(
            f"{API_BASE_URL}/admin/users/{membership_id}", headers=self._api_headers(),
            json=payload, timeout=self.timeout,
        )
        self._raise_api_error(response)
        return self._map_admin_user(response.json())

    def _api_headers(self) -> dict[str, str]:
        if self.session is None or not self.session.organization_id:
            raise CloudAuthError("Session Cloud indisponible.")
        return {
            "Authorization": f"Bearer {self.session.access_token}",
            "X-Organization-ID": self.session.organization_id,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _role_code(label: str) -> str:
        reverse = {value: key for key, value in ROLE_LABELS.items()}
        if label in ROLE_LABELS:
            return label
        if label not in reverse:
            raise ValueError("Rôle utilisateur invalide.")
        return reverse[label]

    @staticmethod
    def _map_admin_user(item: dict) -> dict:
        return {
            "id": item["id"],
            "username": item["email"],
            "first_name": item.get("first_name", ""),
            "last_name": item.get("last_name", ""),
            "email": item["email"],
            "role": ROLE_LABELS.get(item["role"], item["role"]),
            "active": bool(item.get("active")),
            "created_at": item.get("created_at", ""),
            "last_login": item.get("last_login"),
        }

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {"apikey": SUPABASE_PUBLISHABLE_KEY, "Content-Type": "application/json"}

    def authenticate(
        self, email: str, password: str, *, remember_session: bool = True
    ) -> AuthenticatedUser | None:
        email = email.strip().lower()
        if not email or not password:
            return None
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers=self._auth_headers,
            json={"email": email, "password": password},
            timeout=self.timeout,
        )
        if response.status_code in (400, 401):
            return None
        self._raise_auth_error(response)
        self._accept_token_payload(response.json(), remember_session=remember_session)
        return self._load_authorized_identity()

    def restore_session(self) -> AuthenticatedUser | None:
        refresh_token = self._read_refresh_token()
        if not refresh_token:
            return None
        try:
            self._refresh(refresh_token, remember_session=True)
            return self._load_authorized_identity()
        except (CloudAuthError, requests.RequestException):
            self._clear_refresh_token()
            return None

    def heartbeat(self) -> AuthenticatedUser:
        if self.session is None:
            raise CloudAuthError("Aucune session Cloud active.")
        if self.session.expires_at <= datetime.now(timezone.utc) + timedelta(minutes=2):
            self._refresh(self.session.refresh_token, remember_session=self._has_saved_session())
        return self._load_authorized_identity()

    def logout(self) -> None:
        if self.session:
            try:
                requests.post(
                    f"{SUPABASE_URL}/auth/v1/logout",
                    headers={**self._auth_headers, "Authorization": f"Bearer {self.session.access_token}"},
                    timeout=self.timeout,
                )
            except requests.RequestException:
                pass
        self._clear_refresh_token()
        self.session = None
        self.current_user = None

    def request_password_reset(self, email: str) -> None:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/recover",
            headers=self._auth_headers,
            json={"email": email.strip().lower()},
            params={"redirect_to": "https://auth.forma-prof.fr/reset-password"},
            timeout=self.timeout,
        )
        self._raise_auth_error(response)

    def change_password(self, user_id: int, current_password: str, new_password: str) -> None:
        if self.current_user is None or not self.current_user.email:
            raise CloudAuthError("Session utilisateur indisponible.")
        if self.authenticate(self.current_user.email, current_password, remember_session=True) is None:
            raise ValueError("Le mot de passe actuel est incorrect.")
        if len(new_password) < 8:
            raise ValueError("Le nouveau mot de passe doit contenir au moins 8 caractères.")
        response = requests.put(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={**self._auth_headers, "Authorization": f"Bearer {self.session.access_token}"},
            json={"password": new_password},
            timeout=self.timeout,
        )
        self._raise_auth_error(response)

    def _refresh(self, refresh_token: str, *, remember_session: bool) -> None:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
            headers=self._auth_headers,
            json={"refresh_token": refresh_token},
            timeout=self.timeout,
        )
        self._raise_auth_error(response)
        self._accept_token_payload(response.json(), remember_session=remember_session)

    def _accept_token_payload(self, payload: dict, *, remember_session: bool) -> None:
        try:
            access_token = payload["access_token"]
            refresh_token = payload["refresh_token"]
            expires_in = int(payload.get("expires_in", 3600))
        except (KeyError, TypeError, ValueError) as exc:
            raise CloudAuthError("Réponse d'authentification incomplète.") from exc
        self.session = CloudSession(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        )
        if remember_session:
            self._save_refresh_token(refresh_token)
        else:
            self._clear_refresh_token()

    def _load_authorized_identity(self) -> AuthenticatedUser:
        if self.session is None:
            raise CloudAuthError("Session Cloud absente.")
        headers = {"Authorization": f"Bearer {self.session.access_token}"}
        response = requests.get(
            f"{API_BASE_URL}/identity/memberships", headers=headers, timeout=self.timeout
        )
        if response.status_code in (401, 403):
            self.logout()
            raise AccountDisabledError("Ce compte est désactivé ou n'appartient à aucune organisation active.")
        self._raise_api_error(response)
        memberships = response.json()
        if len(memberships) != 1:
            raise CloudAuthError(
                "Aucune organisation active n'est disponible pour ce compte."
                if not memberships
                else "Ce compte appartient à plusieurs organisations ; la sélection sera disponible prochainement."
            )
        membership = memberships[0]
        self.session.organization_id = membership["organization_id"]
        me_response = requests.get(
            f"{API_BASE_URL}/identity/me",
            headers={**headers, "X-Organization-ID": self.session.organization_id},
            timeout=self.timeout,
        )
        if me_response.status_code in (401, 403):
            self.logout()
            raise AccountDisabledError("Le compte ou son accès à l'organisation a été désactivé.")
        self._raise_api_error(me_response)
        me = me_response.json()
        local = self.local_profiles.sync_cloud_user(
            cloud_user_id=membership["user_id"],
            email=membership["email"],
            first_name=membership.get("first_name", ""),
            last_name=membership.get("last_name", ""),
            role=ROLE_LABELS.get(me["role"], me["role"]),
        )
        self.current_user = replace(
            local,
            cloud_user_id=membership["user_id"],
            organization_id=membership["organization_id"],
            organization_name=membership["organization_name"],
            permissions=tuple(me.get("permissions", [])),
        )
        return self.current_user

    @staticmethod
    def _raise_auth_error(response: requests.Response) -> None:
        if response.ok:
            return
        try:
            message = response.json().get("msg") or response.json().get("error_description")
        except ValueError:
            message = None
        raise CloudAuthError(message or "Le service d'authentification est momentanément indisponible.")

    @staticmethod
    def _raise_api_error(response: requests.Response) -> None:
        if response.ok:
            return
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        raise CloudAuthError(detail or f"L'API Form@Prospect a refusé la requête ({response.status_code}).")

    def _save_refresh_token(self, token: str) -> None:
        if keyring is None:
            raise CloudAuthError("Le stockage sécurisé Windows n'est pas disponible.")
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, token)
        except Exception as exc:
            raise CloudAuthError("Impossible d'enregistrer la session dans le coffre Windows.") from exc

    @staticmethod
    def _read_refresh_token() -> str | None:
        if keyring is None:
            return None
        try:
            return keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
        except Exception:
            return None

    @staticmethod
    def _clear_refresh_token() -> None:
        if keyring is None:
            return
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
        except Exception:
            pass

    def _has_saved_session(self) -> bool:
        return bool(self._read_refresh_token())

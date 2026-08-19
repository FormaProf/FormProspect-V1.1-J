from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import os
import platform
import uuid

import requests

from core.session import AuthenticatedUser
from services.auth_service import AuthService
from services.cloud_api_client import CloudAPIClient

try:
    import keyring
except ImportError:  # pragma: no cover - protected failure mode on unsupported builds
    keyring = None


API_BASE_URL = os.getenv("FORMAPROSPECT_API_BASE_URL", "https://api.forma-prof.fr/api/v1").rstrip("/")
SUPABASE_URL = os.getenv("FORMAPROSPECT_SUPABASE_URL", "https://vlpsjcqlljrvojkpdhke.supabase.co").rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.getenv("FORMAPROSPECT_SUPABASE_PUBLISHABLE_KEY", "sb_publishable_497OoUIK8IITjPOlEsYGSw_jn9Zi73N")
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
        self.api = CloudAPIClient(self, API_BASE_URL, timeout=max(timeout, 20))

    def __getattr__(self, name):
        # Photos/licence remain local until their dedicated Cloud migrations.
        return getattr(self.local_profiles, name)

    def list_users(self) -> list[dict]:
        """Return every organization member visible to the administrator.

        The previous implementation returned only the local shadow profile of
        the connected user, which made every other Cloud account disappear.
        """
        if self.current_user is None:
            return []

        payload = self.api.get_json('/admin/users')
        if not isinstance(payload, list):
            raise CloudAuthError(
                "Form@Prospect Cloud a retourné une liste d'utilisateurs invalide."
            )

        users = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            email = str(item.get('email') or '')
            users.append(
                {
                    'id': str(item.get('id') or ''),
                    'username': email,
                    'first_name': str(item.get('first_name') or ''),
                    'last_name': str(item.get('last_name') or ''),
                    'email': email,
                    'role': ROLE_LABELS.get(str(item.get('role') or ''), str(item.get('role') or '')),
                    'active': bool(item.get('active')),
                    'created_at': str(item.get('created_at') or ''),
                    'last_login': str(item.get('last_login') or '') or None,
                    'last_seen_at': str(item.get('last_seen_at') or '') or None,
                    'presence_status': str(item.get('presence_status') or 'offline'),
                }
            )
        return users

    def update_profile_identity(self, first_name: str, last_name: str) -> AuthenticatedUser:
        """Save the user's display identity in the local Cloud shadow profile.

        The Cloud backend currently exposes first/last name as read-only identity
        data. Keeping the values in the local shadow profile gives the desktop
        application a stable personal display name without changing roles, e-mail
        or authentication data. Server-provided names remain authoritative when
        they are present.
        """
        if self.current_user is None:
            raise CloudAuthError('Session utilisateur indisponible.')

        first_name = first_name.strip()
        last_name = last_name.strip()
        if not first_name:
            raise ValueError('Le prénom est obligatoire.')
        if not last_name:
            raise ValueError('Le nom est obligatoire.')
        if len(first_name) > 100 or len(last_name) > 100:
            raise ValueError('Le prénom et le nom sont limités à 100 caractères.')

        # AuthService does not yet expose a dedicated identity-edit method.
        # We update only the local shadow profile used by the Windows client.
        with self.local_profiles._connect() as conn:
            cursor = conn.execute(
                'UPDATE users SET first_name = ?, last_name = ? WHERE id = ?',
                (first_name, last_name, self.current_user.id),
            )
            if cursor.rowcount == 0:
                raise CloudAuthError("Le profil local de l'utilisateur est introuvable.")

        refreshed = self.local_profiles.get_user(self.current_user.id)
        if refreshed is None:
            raise CloudAuthError("Le profil local n'a pas pu être rechargé.")

        self.current_user = replace(
            refreshed,
            cloud_user_id=self.current_user.cloud_user_id,
            organization_id=self.current_user.organization_id,
            organization_name=self.current_user.organization_name,
            permissions=self.current_user.permissions,
        )
        return self.current_user

    def _local_identity_fallback(self, cloud_user_id: str, email: str) -> tuple[str, str]:
        """Read a previously entered display name before Cloud sync overwrites it."""
        try:
            with self.local_profiles._connect() as conn:
                row = conn.execute(
                    "SELECT first_name, last_name FROM users "
                    "WHERE cloud_user_id = ? OR username = ? COLLATE NOCASE LIMIT 1",
                    (cloud_user_id, email.strip().lower()),
                ).fetchone()
        except Exception:
            return '', ''
        if not row:
            return '', ''
        return str(row['first_name'] or ''), str(row['last_name'] or '')

    @staticmethod
    def _cloud_role_value(role: str) -> str:
        normalized = str(role or "").strip()
        reverse = {label: value for value, label in ROLE_LABELS.items()}
        if normalized in ROLE_LABELS:
            return normalized
        if normalized in reverse:
            return reverse[normalized]
        raise ValueError("Rôle utilisateur invalide.")

    def create_user(
        self,
        *,
        email: str,
        first_name: str = "",
        last_name: str = "",
        role: str = "Commercial",
    ) -> dict:
        if self.current_user is None:
            raise CloudAuthError("Session utilisateur indisponible.")

        email = str(email or "").strip().lower()
        first_name = str(first_name or "").strip()
        last_name = str(last_name or "").strip()

        if not email or "@" not in email:
            raise ValueError("Une adresse e-mail valide est obligatoire.")
        if len(first_name) > 100 or len(last_name) > 100:
            raise ValueError("Le prénom et le nom sont limités à 100 caractères.")

        payload = self.api.post_json(
            "/admin/users",
            {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": self._cloud_role_value(role),
            },
            expected=(201,),
        )
        if not isinstance(payload, dict):
            raise CloudAuthError(
                "Form@Prospect Cloud n'a pas confirmé la création du compte."
            )
        return payload

    def set_active(self, membership_id: str, active: bool) -> dict:
        if self.current_user is None:
            raise CloudAuthError("Session utilisateur indisponible.")

        payload = self.api.patch_json(
            f"/admin/users/{str(membership_id).strip()}",
            {"active": bool(active)},
        )
        if not isinstance(payload, dict):
            raise CloudAuthError(
                "Form@Prospect Cloud n'a pas confirmé la modification du compte."
            )
        return payload

    def reset_password(self, membership_id: str, *_args, **_kwargs) -> None:
        if self.current_user is None:
            raise CloudAuthError("Session utilisateur indisponible.")

        self.api.request(
            "POST",
            f"/admin/users/{str(membership_id).strip()}/password-reset",
            json={},
            expected=(204,),
        )

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
        user = self._load_authorized_identity()
        self.register_login_event()
        return user

    def restore_session(self) -> AuthenticatedUser | None:
        refresh_token = self._read_refresh_token()
        if not refresh_token:
            return None
        try:
            self._refresh(refresh_token, remember_session=True)
            user = self._load_authorized_identity()
            self.register_login_event()
            return user
        except (CloudAuthError, requests.RequestException):
            self._clear_refresh_token()
            return None

    @staticmethod
    def _device_name() -> str:
        """Nom lisible du poste Windows utilisé."""
        return (platform.node() or "Windows").strip()[:160]

    @staticmethod
    def _device_fingerprint() -> str:
        """Empreinte stable du poste, sans transmettre l'adresse MAC brute."""
        raw = f"{platform.node()}|{uuid.getnode()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _presence_payload(self) -> dict[str, str]:
        return {
            "device_fingerprint": self._device_fingerprint(),
            "device_name": self._device_name(),
        }

    def register_login_event(self) -> None:
        """Enregistre l'ouverture d'une session Form@Prospect côté Cloud."""
        if self.session is None or self.current_user is None:
            return
        self.api.post_json(
            "/identity/login-event",
            self._presence_payload(),
            expected=(200,),
        )

    def send_presence_heartbeat(self) -> None:
        """Envoie uniquement le signe de vie du poste, sans recharger l'identité."""
        if self.session is None or self.current_user is None:
            return
        if self.session.expires_at <= datetime.now(timezone.utc) + timedelta(minutes=2):
            self._refresh(
                self.session.refresh_token,
                remember_session=self._has_saved_session(),
            )
        self.api.post_json(
            "/identity/heartbeat",
            self._presence_payload(),
            expected=(200,),
        )

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

        cloud_user_id = str(membership["user_id"])
        email = str(membership["email"])
        first_name = str(membership.get("first_name") or "").strip()
        last_name = str(membership.get("last_name") or "").strip()

        # Some existing Cloud accounts were created before first/last name were
        # populated. Preserve a name entered from "Mon compte" when the server
        # still returns blanks.
        if not first_name or not last_name:
            local_first, local_last = self._local_identity_fallback(cloud_user_id, email)
            first_name = first_name or local_first
            last_name = last_name or local_last

        local = self.local_profiles.sync_cloud_user(
            cloud_user_id=cloud_user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
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
        raise CloudAuthError(f"L'API Form@Prospect a refusé la requête ({response.status_code}).")

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

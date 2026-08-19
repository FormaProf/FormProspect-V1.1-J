from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


class CloudUserDataError(ValueError):
    """Raised when the Cloud user payload is missing required information."""


@dataclass(frozen=True, slots=True)
class CloudUser:
    """Immutable representation of an organization user returned by the Cloud."""

    id: str
    membership_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    role: str
    status: str
    is_active: bool
    manager_user_id: str | None
    can_create_prospect_manually: bool
    last_login_at: datetime | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "CloudUser":
        """Build and validate a CloudUser from the backend JSON payload."""

        if not isinstance(payload, dict):
            raise CloudUserDataError(
                "Les données utilisateur reçues du Cloud sont invalides."
            )

        user_id = cls._required_text(payload, "id")
        membership_id = cls._required_text(payload, "membership_id")
        email = cls._required_text(payload, "email")
        role = cls._required_text(payload, "role")
        status = cls._required_text(payload, "status")

        return cls(
            id=user_id,
            membership_id=membership_id,
            first_name=cls._optional_text(payload.get("first_name")),
            last_name=cls._optional_text(payload.get("last_name")),
            email=email,
            phone=cls._optional_text(payload.get("phone")),
            role=role,
            status=status,
            is_active=bool(payload.get("is_active", False)),
            manager_user_id=cls._optional_identifier(
                payload.get("manager_user_id")
            ),
            can_create_prospect_manually=bool(
                payload.get("can_create_prospect_manually", False)
            ),
            last_login_at=cls._parse_datetime(payload.get("last_login_at")),
        )

    @property
    def full_name(self) -> str:
        """Return the user's first and last name, or their email as fallback."""

        value = f"{self.first_name} {self.last_name}".strip()
        return value or self.email

    @property
    def display_name(self) -> str:
        """Return a label suitable for combo boxes and user lists."""

        return f"{self.full_name} ({self.role_label})"

    @property
    def role_label(self) -> str:
        labels = {
            "admin": "Administrateur",
            "manager": "Manager",
            "commercial": "Commercial",
            "trainer": "Formateur",
            "admin_assistant": "Assistant administratif",
        }
        return labels.get(self.role, self.role.replace("_", " ").title())

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_manager(self) -> bool:
        return self.role == "manager"

    @property
    def is_commercial(self) -> bool:
        return self.role == "commercial"

    @property
    def is_assignable_to_project(self) -> bool:
        """Return whether the user can be offered as a project assignee."""

        return self.is_active and self.status == "active" and self.is_commercial

    @staticmethod
    def _required_text(payload: dict[str, Any], field: str) -> str:
        value = str(payload.get(field) or "").strip()
        if not value:
            raise CloudUserDataError(
                f"Le champ utilisateur Cloud '{field}' est manquant."
            )
        return value

    @staticmethod
    def _optional_text(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _optional_identifier(value: Any) -> str | None:
        identifier = str(value or "").strip()
        return identifier or None

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value in (None, ""):
            return None

        if isinstance(value, datetime):
            return value

        text = str(value).strip()
        if not text:
            return None

        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CloudUserDataError(
                "La date de dernière connexion de l'utilisateur est invalide."
            ) from exc

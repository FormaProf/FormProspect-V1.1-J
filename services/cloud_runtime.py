from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.cloud_auth_service import CloudAuthService


class CloudRuntime:
    """Process-wide access to the authenticated Cloud session.

    Desktop services use this small registry so the existing UI can progressively
    switch from SQLite repositories to the Cloud API without coupling widgets to
    authentication details.
    """

    _auth_service: CloudAuthService | None = None

    @classmethod
    def configure(cls, auth_service: CloudAuthService) -> None:
        cls._auth_service = auth_service

    @classmethod
    def clear(cls) -> None:
        cls._auth_service = None

    @classmethod
    def is_active(cls) -> bool:
        return bool(cls._auth_service and cls._auth_service.session and cls._auth_service.current_user)

    @classmethod
    def auth_service(cls) -> CloudAuthService:
        if not cls.is_active() or cls._auth_service is None:
            raise RuntimeError("Aucune session Form@Prospect Cloud active.")
        return cls._auth_service

    @classmethod
    def api(cls):
        return cls.auth_service().api

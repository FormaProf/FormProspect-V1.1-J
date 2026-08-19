from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    role: str
    photo_path: str = ""
    cloud_user_id: str = ""
    organization_id: str = ""
    organization_name: str = ""
    permissions: tuple[str, ...] = ()

    @property
    def display_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.username


class SessionState:
    current_user: AuthenticatedUser | None = None

    @classmethod
    def login(cls, user: AuthenticatedUser) -> None:
        cls.current_user = user

    @classmethod
    def logout(cls) -> None:
        cls.current_user = None

    @classmethod
    def user(cls) -> AuthenticatedUser | None:
        return cls.current_user

    @classmethod
    def is_authenticated(cls) -> bool:
        return cls.current_user is not None

    @classmethod
    def has_role(cls, *roles: str) -> bool:
        return bool(cls.current_user and cls.current_user.role in roles)

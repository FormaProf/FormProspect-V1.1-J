from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeploymentOptions:
    """
    Options choisies par l'utilisateur avant le déploiement
    d'un projet dans Form@Prospect Cloud.
    """

    description: str = ""
    assigned_to: str | None = None

    def __post_init__(self) -> None:
        normalized_description = self.description.strip()

        normalized_assigned_to = (
            self.assigned_to.strip()
            if isinstance(self.assigned_to, str)
            and self.assigned_to.strip()
            else None
        )

        object.__setattr__(
            self,
            "description",
            normalized_description,
        )

        object.__setattr__(
            self,
            "assigned_to",
            normalized_assigned_to,
        )
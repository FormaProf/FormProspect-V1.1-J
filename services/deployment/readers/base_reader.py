from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Generic, TypeVar

from services.deployment.deployment_batch import DeploymentBatch
from services.deployment.deployment_context import DeploymentContext

T = TypeVar("T")


class DeploymentReader(ABC, Generic[T]):
    """Port de lecture locale, indépendant de SQLite et du réseau."""

    @abstractmethod
    def count(self, context: DeploymentContext) -> int:
        """Retourne le nombre total d'éléments à déployer."""
        raise NotImplementedError

    @abstractmethod
    def iter_batches(
        self,
        context: DeploymentContext,
        *,
        start_offset: int = 0,
    ) -> Iterator[DeploymentBatch[T]]:
        """Parcourt les données par lots sans tout charger en mémoire."""
        raise NotImplementedError

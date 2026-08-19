from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from repositories.prospect_repository import ProspectRepository
from services.deployment.deployment_batch import DeploymentBatch
from services.deployment.deployment_context import DeploymentContext

from .base_reader import DeploymentReader


class ProspectDeploymentReader(DeploymentReader[Any]):
    """
    Adaptateur entre le moteur de déploiement et ProspectRepository.

    Cette classe ne contient aucune requête SQL. Le repository reste l'unique
    point d'accès à la table locale `prospects`.
    """

    def __init__(self, repository: ProspectRepository) -> None:
        self.repository = repository

    def count(self, context: DeploymentContext) -> int:
        return int(self.repository.count_all())

    def iter_batches(
        self,
        context: DeploymentContext,
        *,
        start_offset: int = 0,
    ) -> Iterator[DeploymentBatch[Any]]:
        yield from self.repository.iterate_deployment_batches(
            batch_size=context.batch_size,
            start_offset=start_offset,
        )

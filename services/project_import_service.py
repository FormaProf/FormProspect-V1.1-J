from __future__ import annotations

from dataclasses import dataclass

from repositories.prospect_repository import ProspectRepository
from services.cloud_api_client import CloudAPIClient
from services.prospect_mapper import ProspectMapper


@dataclass(frozen=True)
class ProjectImportResult:
    """
    Résultat global de l'import des prospects vers un projet Cloud.

    Attributes:
        total_batches:
            Nombre total de lots parcourus.

        processed_batches:
            Nombre de lots ayant reçu une réponse du backend.

        last_successful_batch:
            Numéro du dernier lot entièrement importé sans échec.
            La valeur reste à 0 si aucun lot n'a entièrement réussi.

        total_prospects:
            Nombre total de prospects pris en compte par le backend.

        imported_prospects:
            Nombre total de prospects importés avec succès.

        failed_prospects:
            Nombre total de prospects signalés en échec.
    """

    total_batches: int
    processed_batches: int
    last_successful_batch: int
    total_prospects: int
    imported_prospects: int
    failed_prospects: int


class ProjectImportService:
    """
    Orchestre l'import des prospects locaux vers un projet Cloud.

    Le service :

    1. lit les prospects SQLite par lots ;
    2. convertit chaque lot avec ProspectMapper ;
    3. envoie le lot au backend Form@Prospect ;
    4. construit les statistiques globales à partir des réponses
    réellement retournées par le backend.
    """

    DEFAULT_BATCH_SIZE = 150
    MAX_BATCH_SIZE = 200

    def __init__(
        self,
        repository: ProspectRepository,
        api: CloudAPIClient,
    ):
        if repository is None:
            raise ValueError(
                "Le repository des prospects est obligatoire."
            )

        if api is None:
            raise ValueError(
                "Le client API Cloud est obligatoire."
            )

        self.repository = repository
        self.api = api

    def import_project(
        self,
        project_id: str,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> ProjectImportResult:
        """
        Importe les prospects locaux dans un projet Cloud.

        Args:
            project_id:
                Identifiant UUID du projet déjà créé dans le Cloud.

            batch_size:
                Nombre maximal de prospects envoyés dans chaque lot.

        Returns:
            ProjectImportResult:
                Statistiques globales établies à partir des réponses
                retournées par le backend.

        Raises:
            ValueError:
                Si l'identifiant du projet est vide ou si la taille
                des lots est invalide.

            CloudAPIError:
                Si le backend est inaccessible ou refuse l'import.

            Exception:
                Si la lecture locale ou le mapping rencontre une erreur.
        """

        normalized_project_id = str(project_id or "").strip()

        if not normalized_project_id:
            raise ValueError(
                "L'identifiant du projet Cloud est obligatoire."
            )

        if not isinstance(batch_size, int):
            raise ValueError(
                "La taille des lots doit être un nombre entier."
            )

        if batch_size <= 0:
            raise ValueError(
                "La taille des lots doit être strictement positive."
            )

        if batch_size > self.MAX_BATCH_SIZE:
            raise ValueError(
                "La taille des lots ne peut pas dépasser "
                f"{self.MAX_BATCH_SIZE} prospects."
            )

        total_batches = 0
        processed_batches = 0
        last_successful_batch = 0

        total_prospects = 0
        imported_prospects = 0
        failed_prospects = 0

        for batch in self.repository.iterate_deployment_batches(
            batch_size=batch_size,
        ):
            total_batches += 1

            mapped_prospects = ProspectMapper.from_batch(
                batch.items
            )

            response = self.api.import_project_prospects(
                normalized_project_id,
                mapped_prospects,
            )

            processed_batches += 1

            total_prospects += response.total_prospects
            imported_prospects += response.imported_prospects
            failed_prospects += response.failed_prospects

            if response.success:
                last_successful_batch = total_batches

        return ProjectImportResult(
            total_batches=total_batches,
            processed_batches=processed_batches,
            last_successful_batch=last_successful_batch,
            total_prospects=total_prospects,
            imported_prospects=imported_prospects,
            failed_prospects=failed_prospects,
        )
from __future__ import annotations

from dataclasses import dataclass

from core.workspace_state import CloudProject
from services.cloud_api_client import CloudAPIError


@dataclass(frozen=True)
class CommercialProjectOverview:
    id: str
    name: str
    projects: tuple[CloudProject, ...]
    prospect_count: int
    lead_chaud_count: int
    lead_chaud_by_project: dict[str, int]


@dataclass(frozen=True)
class CommercialNavigationDecision:
    mode: str
    project_id: str | None = None
    parent_id: str | None = None

@dataclass(frozen=True)
class CommercialLandingLink:
    id: str
    project_id: str
    organization_id: str
    token: str
    is_active: bool

class CommercialProjectWorkspaceService:
    def __init__(self, api):
        self.api = api

    def _project_prospect_count(self, project: CloudProject) -> int:
        """Return the live Cloud prospect count for one project.

        ``project.prospect_count`` comes from the project listing payload and can
        legitimately be stale after a portfolio reassignment.  The CRM itself
        uses the prospects endpoint/stats, so the workspace counters must use
        the same live source of truth.
        """
        project_id = str(getattr(project, "id", "") or "").strip()
        if not project_id:
            return 0

        get_stats = getattr(self.api, "get_prospect_stats", None)
        if callable(get_stats):
            stats = get_stats(project_id=project_id)
            try:
                return max(0, int((stats or {}).get("total", 0) or 0))
            except (AttributeError, TypeError, ValueError):
                pass

        # Compatibility fallback for older/fake API clients.
        page = self.api.list_prospects(
            project_id=project_id,
            limit=1,
            offset=0,
        )
        return max(0, int(getattr(page, "total", 0) or 0))

    def resolve_initial_navigation(self, parents) -> CommercialNavigationDecision:
        parents = list(parents or [])
        if not parents:
            return CommercialNavigationDecision(mode="empty")

        if len(parents) > 1:
            return CommercialNavigationDecision(mode="show_parents")

        parent = parents[0]
        projects = tuple(getattr(parent, "projects", ()) or ())

        if len(projects) == 1:
            project_id = str(getattr(projects[0], "id", "") or "").strip()
            if project_id:
                return CommercialNavigationDecision(mode="open_project", project_id=project_id)

        parent_id = str(getattr(parent, "id", "") or "").strip() or None

        if len(projects) > 1:
            return CommercialNavigationDecision(mode="show_children", parent_id=parent_id)

        return CommercialNavigationDecision(mode="empty", parent_id=parent_id)

    @staticmethod
    def _landing(payload: dict) -> CommercialLandingLink:
        return CommercialLandingLink(
            id=str(payload.get("id") or "").strip(),
            project_id=str(payload.get("project_id") or "").strip(),
            organization_id=str(payload.get("organization_id") or "").strip(),
            token=str(payload.get("token") or "").strip(),
            is_active=bool(payload.get("is_active", False)),
        )

    def get_landing(self, project_id: str) -> CommercialLandingLink | None:
        project_id = str(project_id or "").strip()
        try:
            payload = self.api.get_my_commercial_landing_link(project_id)
        except CloudAPIError as exc:
            if exc.status_code == 404:
                return None
            raise
        return self._landing(payload)

    def ensure_landing(self, project_id: str) -> CommercialLandingLink:
        project_id = str(project_id or "").strip()
        payload = self.api.ensure_my_commercial_landing_link(project_id)
        return self._landing(payload)

    def set_landing_active(
        self, project_id: str, active: bool,
    ) -> CommercialLandingLink:
        project_id = str(project_id or "").strip()
        payload = self.api.set_my_commercial_landing_link_active(
            project_id,
            bool(active),
        )
        return self._landing(payload)

    def list_for_manager(self) -> list[CommercialProjectOverview]:
        parents = self.api.list_commercial_projects()
        result = self.api.list_projects(
            sort_by="updated_at",
            sort_direction="desc",
            limit=100,
            offset=0,
        )

        visible_projects = [
            CloudProject.from_mapping(raw_project)
            for raw_project in result.items
        ]

        overviews = []
        for parent in parents:
            parent_id = str(parent.get("id") or "").strip()
            parent_name = str(parent.get("name") or "").strip()
            if not parent_id or not parent_name:
                continue

            projects = tuple(
                project
                for project in visible_projects
                if str(
                    project.metadata.get("commercial_project_id") or ""
                ).strip()
                == parent_id
            )

            prospect_count = sum(
                self._project_prospect_count(project)
                for project in projects
            )

            lead_chaud_by_project = {
                project.id: self.api.list_prospects(
                    project_id=project.id,
                    pipeline_stage="lead_chaud",
                    limit=1,
                    offset=0,
                ).total
                for project in projects
            }
            lead_chaud_count = sum(lead_chaud_by_project.values())

            overviews.append(
                CommercialProjectOverview(
                    id=parent_id,
                    name=parent_name,
                    projects=projects,
                    prospect_count=prospect_count,
                    lead_chaud_count=lead_chaud_count,
                    lead_chaud_by_project=lead_chaud_by_project,
                )
            )

        return overviews

    def list_for_commercial(self, user_id: str) -> list[CommercialProjectOverview]:
        user_id = str(user_id or "").strip()
        if not user_id:
            return []

        parents = self.api.list_commercial_projects()
        result = self.api.list_projects(
            assigned_to=user_id,
            sort_by="updated_at",
            sort_direction="desc",
            limit=100,
            offset=0,
        )

        visible_projects = []
        for raw_project in result.items:
            project = CloudProject.from_mapping(raw_project)
            if project.assigned_to != user_id:
                continue
            visible_projects.append(project)

        overviews = []
        for parent in parents:
            parent_id = str(parent.get("id") or "").strip()
            parent_name = str(parent.get("name") or "").strip()
            if not parent_id or not parent_name:
                continue

            projects = tuple(
                project
                for project in visible_projects
                if str(project.metadata.get("commercial_project_id") or "").strip() == parent_id
            )

            prospect_count = sum(
                self._project_prospect_count(project)
                for project in projects
            )

            lead_chaud_by_project = {
                project.id: self.api.list_prospects(
                    project_id=project.id,
                    pipeline_stage="lead_chaud",
                    limit=1,
                    offset=0,
                ).total
                for project in projects
            }
            lead_chaud_count = sum(lead_chaud_by_project.values())

            overviews.append(
                CommercialProjectOverview(
                    id=parent_id,
                    name=parent_name,
                    projects=projects,
                    prospect_count=prospect_count,
                    lead_chaud_count=lead_chaud_count,
                    lead_chaud_by_project=lead_chaud_by_project,
                )
            )

        return overviews

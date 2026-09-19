from __future__ import annotations

from dataclasses import dataclass

from core.workspace_state import CloudProject


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

class CommercialProjectWorkspaceService:
    def __init__(self, api):
        self.api = api

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
                project.prospect_count or 0
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
                project.prospect_count or 0
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

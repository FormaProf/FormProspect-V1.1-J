from __future__ import annotations

from dataclasses import dataclass

from core.workspace_state import CloudProject


@dataclass(frozen=True)
class CommercialProjectOverview:
    id: str
    name: str
    projects: tuple[CloudProject, ...]
    prospect_count: int


class CommercialProjectWorkspaceService:
    def __init__(self, api):
        self.api = api

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

            overviews.append(
                CommercialProjectOverview(
                    id=parent_id,
                    name=parent_name,
                    projects=projects,
                    prospect_count=prospect_count,
                )
            )

        return overviews

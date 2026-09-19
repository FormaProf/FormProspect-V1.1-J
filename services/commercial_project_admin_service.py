from __future__ import annotations

from dataclasses import dataclass

from services.cloud_api_client import CloudAPIError


@dataclass(frozen=True, slots=True)
class AdminCommercial:
    id: str
    name: str
    email: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class AdminChildProject:
    id: str
    name: str
    status: str
    commercial_project_id: str | None
    assigned_to: str | None


@dataclass(frozen=True, slots=True)
class AdminLandingLink:
    id: str
    commercial_user_id: str
    project_id: str
    organization_id: str
    token: str
    is_active: bool

@dataclass(frozen=True, slots=True)
class AdminParentProject:
    id: str
    name: str
    description: str
    is_active: bool
    assigned_commercials: tuple[AdminCommercial, ...]
    projects: tuple[AdminChildProject, ...]


@dataclass(frozen=True, slots=True)
class CommercialProjectAdminSnapshot:
    parents: tuple[AdminParentProject, ...]
    commercials: tuple[AdminCommercial, ...]
    ungrouped_projects: tuple[AdminChildProject, ...]


class CommercialProjectAdminService:
    def __init__(self, api):
        self.api = api

    @staticmethod
    def _commercial(user) -> AdminCommercial:
        return AdminCommercial(
            id=str(getattr(user, "id", "") or "").strip(),
            name=str(getattr(user, "full_name", "") or "").strip(),
            email=str(getattr(user, "email", "") or "").strip(),
            is_active=bool(getattr(user, "is_active", False)),
        )

    @staticmethod
    def _project(payload: dict) -> AdminChildProject:
        parent_id = str(payload.get("commercial_project_id") or "").strip() or None
        return AdminChildProject(
            id=str(payload.get("id") or "").strip(),
            name=str(payload.get("name") or "").strip(),
            status=str(payload.get("status") or "").strip(),
            commercial_project_id=parent_id,
            assigned_to=str(payload.get("assigned_to") or "").strip() or None,
        )

    def load(self) -> CommercialProjectAdminSnapshot:
        parent_rows = self.api.list_commercial_projects(include_inactive=True)
        users = self.api.list_users(active_only=False)
        page = self.api.list_projects(include_archived=True, limit=500, offset=0)

        commercials = tuple(
            self._commercial(user)
            for user in users
            if str(getattr(user, "role", "") or "").strip().lower() == "commercial"
        )
        commercials_by_id = {item.id: item for item in commercials}

        projects = tuple(self._project(row) for row in page.items)
        projects_by_parent: dict[str, list[AdminChildProject]] = {}
        ungrouped: list[AdminChildProject] = []

        for project in projects:
            if project.commercial_project_id:
                projects_by_parent.setdefault(project.commercial_project_id, []).append(project)
            else:
                ungrouped.append(project)

        parents = []
        for row in parent_rows:
            parent_id = str(row.get("id") or "").strip()
            assignments = self.api.list_commercial_project_assignments(parent_id)
            assigned = tuple(
                commercials_by_id[user_id]
                for assignment in assignments
                if (user_id := str(assignment.get("user_id") or "").strip()) in commercials_by_id
            )
            parents.append(AdminParentProject(
                id=parent_id,
                name=str(row.get("name") or "").strip(),
                description=str(row.get("description") or "").strip(),
                is_active=bool(row.get("is_active", False)),
                assigned_commercials=assigned,
                projects=tuple(projects_by_parent.get(parent_id, ())),
            ))

        return CommercialProjectAdminSnapshot(
            parents=tuple(parents),
            commercials=commercials,
            ungrouped_projects=tuple(ungrouped),
        )

    @staticmethod
    def _landing(payload: dict, commercial_user_id: str) -> AdminLandingLink:
        return AdminLandingLink(
            id=str(payload.get("id") or "").strip(),
            commercial_user_id=str(commercial_user_id or "").strip(),
            project_id=str(payload.get("project_id") or "").strip(),
            organization_id=str(payload.get("organization_id") or "").strip(),
            token=str(payload.get("token") or "").strip(),
            is_active=bool(payload.get("is_active", False)),
        )

    def get_landing(
        self, project_id: str, commercial_user_id: str,
    ) -> AdminLandingLink | None:
        try:
            payload = self.api.get_admin_commercial_landing_link(
                str(commercial_user_id).strip(),
                str(project_id).strip(),
            )
        except CloudAPIError as exc:
            if exc.status_code == 404:
                return None
            raise
        return self._landing(payload, commercial_user_id)

    def ensure_landing(self, project_id: str, commercial_user_id: str) -> AdminLandingLink:
        payload = self.api.ensure_admin_commercial_landing_link(
            str(commercial_user_id).strip(),
            str(project_id).strip(),
        )
        return self._landing(payload, commercial_user_id)

    def set_landing_active(
        self, project_id: str, commercial_user_id: str, active: bool,
    ) -> AdminLandingLink:
        payload = self.api.set_admin_commercial_landing_link_active(
            str(commercial_user_id).strip(),
            str(project_id).strip(),
            bool(active),
        )
        return self._landing(payload, commercial_user_id)

    def create_parent(self, name: str, description: str = ""):
        return self.api.create_commercial_project({
            "name": str(name or "").strip(),
            "description": str(description or "").strip(),
        })

    def update_parent(self, parent_id: str, name: str, description: str = ""):
        return self.api.update_commercial_project(str(parent_id).strip(), {
            "name": str(name or "").strip(),
            "description": str(description or "").strip(),
        })

    def set_parent_active(self, parent_id: str, active: bool):
        return self.api.set_commercial_project_status(str(parent_id).strip(), bool(active))

    def assign_commercial(self, parent_id: str, user_id: str):
        return self.api.add_commercial_project_assignment(str(parent_id).strip(), str(user_id).strip())

    def remove_commercial(self, parent_id: str, user_id: str):
        return self.api.remove_commercial_project_assignment(str(parent_id).strip(), str(user_id).strip())

    def attach_project(self, parent_id: str, project_id: str):
        return self.api.set_project_commercial_parent(
            str(project_id).strip(),
            str(parent_id).strip(),
        )

    def detach_project(self, project_id: str):
        return self.api.set_project_commercial_parent(
            str(project_id).strip(),
            None,
        )

    def assign_project_to_commercial(self, project_id: str, commercial_user_id: str):
        return self.api.update_project(
            str(project_id).strip(),
            {"assigned_to": str(commercial_user_id).strip()},
        )

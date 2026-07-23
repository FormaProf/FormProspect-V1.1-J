from core.project import Project


class ApplicationState:
    current_project: Project | None = None

    @classmethod
    def set_project(cls, project: Project):
        cls.current_project = project

    @classmethod
    def get_project(cls):
        return cls.current_project

    @classmethod
    def has_project(cls):
        return cls.current_project is not None
"""Run Alembic migrations without depending on CLI argument parsing."""
from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    config = Config(str(project_root / "backend" / "alembic.ini"))
    config.set_main_option(
        "script_location",
        str(project_root / "backend" / "migrations"),
    )
    command.upgrade(config, "head")


if __name__ == "__main__":
    main()

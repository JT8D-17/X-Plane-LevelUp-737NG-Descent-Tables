#!/usr/bin/env python3
"""
Prepare or build a Briefcase project for the current platform.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from build_payload import prepare_payload, repo_root, reset_dir


APP_MODULE = "levelup_vnav_installer"
APP_NAME = "levelup-vnav-installer"
FORMAL_NAME = "LevelUp VNAV Installer"


PYPROJECT = f"""[tool.briefcase]
project_name = "LevelUp VNAV Installer"
bundle = "org.wahltho"
version = "0.1.0"
url = "https://github.com/JT8D-17/X-Plane-LevelUp-737NG-Descent-Tables"
author = "Thomas Wahl"
author_email = "noreply@example.com"

[tool.briefcase.app.{APP_NAME}]
formal_name = "{FORMAL_NAME}"
description = "Installer for LevelUp 737NG VNAV descent table packages"
sources = ["src/{APP_MODULE}"]
requires = []
"""


APP_WRAPPER = """from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    app_dir = Path(__file__).resolve().parent
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    from LevelUpVNAVInstaller import main as gui_main

    return int(gui_main() or 0)
"""


APP_MAIN = """from __future__ import annotations

from .app import main


if __name__ == "__main__":
    raise SystemExit(main())
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or run Briefcase packaging.")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=repo_root() / "build" / "briefcase_project",
        help="Generated Briefcase project directory.",
    )
    parser.add_argument("--run", action="store_true", help="Run Briefcase after preparing the project.")
    parser.add_argument(
        "--commands",
        nargs="+",
        default=["create", "build", "package"],
        help="Briefcase commands to run when --run is used.",
    )
    return parser


def prepare_project(project_dir: Path) -> Path:
    reset_dir(project_dir)
    source_dir = project_dir / "src" / APP_MODULE
    prepare_payload(source_dir, gui_as_py=True, include_launchers=False)
    (source_dir / "__init__.py").write_text("", encoding="utf-8")
    (source_dir / "__main__.py").write_text(APP_MAIN, encoding="utf-8")
    (source_dir / "app.py").write_text(APP_WRAPPER, encoding="utf-8")
    (project_dir / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    return project_dir


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = prepare_project(args.project_dir.resolve())
    print(f"Briefcase project prepared: {project_dir}")
    print(f"pyproject.toml: {project_dir / 'pyproject.toml'}")

    if not args.run:
        print("Run with --run to execute Briefcase commands.")
        return 0

    for command in args.commands:
        result = subprocess.run([sys.executable, "-m", "briefcase", command], cwd=project_dir)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

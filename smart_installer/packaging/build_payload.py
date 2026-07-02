#!/usr/bin/env python3
"""
Prepare the installer payload shared by PyInstaller and Briefcase builds.
"""

from __future__ import annotations

import shutil
from pathlib import Path


PACKAGE_FILES = (
    "B738.a_fms_levelup_tables.lua",
    "Add_to_take_alt_dist.txt",
    "Add_to_take_alt_dist_mach.txt",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def smart_root() -> Path:
    return repo_root() / "smart_installer"


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_package_files(source_root: Path, destination_root: Path) -> None:
    destination_root.mkdir(parents=True, exist_ok=True)
    for file_name in PACKAGE_FILES:
        copy_file(source_root / file_name, destination_root / file_name)


def prepare_payload(destination: Path, gui_as_py: bool = False, include_launchers: bool = True) -> Path:
    root = repo_root()
    smart = smart_root()
    reset_dir(destination)

    copy_file(smart / "install_vnav_descent_tables.py", destination / "install_vnav_descent_tables.py")
    gui_destination = destination / ("LevelUpVNAVInstaller.py" if gui_as_py else "LevelUpVNAVInstaller.pyw")
    copy_file(smart / "LevelUpVNAVInstaller.pyw", gui_destination)
    copy_file(smart / "README.md", destination / "README.md")

    if include_launchers:
        for file_name in (
            "Launch_LevelUp_VNAV_Installer.command",
            "Launch_LevelUp_VNAV_Installer.bat",
            "Launch_LevelUp_VNAV_Installer.sh",
        ):
            copy_file(smart / file_name, destination / file_name)

    copy_package_files(root, destination / "complete")
    copy_package_files(root / "levelup_only", destination / "levelup_only")
    return destination

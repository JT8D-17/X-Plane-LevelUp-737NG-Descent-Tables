#!/usr/bin/env python3
"""
Build a native PyInstaller bundle for the current platform.

Run this from the repository root or from the packaging folder.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from build_payload import prepare_payload, repo_root


APP_NAME = "LevelUpVNAVInstaller"


def data_arg(source: Path, destination: str) -> str:
    separator = ";" if os.name == "nt" else ":"
    return f"{source}{separator}{destination}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the LevelUp VNAV installer with PyInstaller.")
    parser.add_argument("--onefile", action="store_true", help="Build a single-file executable.")
    parser.add_argument("--console", action="store_true", help="Keep a console window for diagnostics.")
    parser.add_argument("--no-clean", action="store_true", help="Do not pass --clean to PyInstaller.")
    parser.add_argument("--dry-run", action="store_true", help="Print the PyInstaller command without running it.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    build_root = root / "build" / "pyinstaller"
    payload_dir = build_root / "payload"
    dist_dir = root / "dist" / "native" / "pyinstaller"
    work_dir = build_root / "work"
    spec_dir = build_root / "spec"

    prepare_payload(payload_dir, gui_as_py=False, include_launchers=False)
    dist_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(spec_dir),
        "--add-data",
        data_arg(payload_dir / "complete", "complete"),
        "--add-data",
        data_arg(payload_dir / "levelup_only", "levelup_only"),
        "--add-data",
        data_arg(payload_dir / "README.md", "."),
    ]
    if not args.no_clean:
        command.append("--clean")
    if not args.console:
        command.append("--windowed")
    if args.onefile:
        command.append("--onefile")

    command.append(str(payload_dir / "LevelUpVNAVInstaller.pyw"))

    print(" ".join(command))
    if args.dry_run:
        return 0
    return subprocess.run(command).returncode


if __name__ == "__main__":
    raise SystemExit(main())

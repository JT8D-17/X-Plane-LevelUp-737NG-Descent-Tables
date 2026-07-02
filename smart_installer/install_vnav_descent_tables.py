#!/usr/bin/env python3
"""
Smart installer for the VNAV descent table package.

The script patches the user's local B738.a_fms.lua in-place. It does not
distribute or create a complete modified Lua file.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


LUA_FILE_NAME = "B738.a_fms.lua"
TABLE_FILE_NAME = "B738.a_fms_levelup_tables.lua"
ALT_DIST_FILE_NAME = "Add_to_take_alt_dist.txt"
ALT_DIST_MACH_FILE_NAME = "Add_to_take_alt_dist_mach.txt"

DOFILE_LINE = f'dofile("{TABLE_FILE_NAME}")'
ALT_DIST_FUNC = "function take_alt_dist(x_idx_alt, x_spd_alt, x_spd_wnd_alt, x_flap)"
ALT_DIST_MACH_FUNC = "function take_alt_dist_mach(x_idx_alt, x_spd_alt, x_spd_wnd_alt)"
ALT_DIST_MARKER = "pcall(B738_variant_test_take_alt_dist,"
ALT_DIST_MACH_MARKER = "pcall(B738_variant_test_take_alt_dist_mach,"


class InstallerError(RuntimeError):
    pass


@dataclass(frozen=True)
class PackageFiles:
    root: Path
    table: Path
    alt_dist: Path
    alt_dist_mach: Path


@dataclass(frozen=True)
class TargetFiles:
    root: Path
    lua: Path
    table: Path
    alt_dist: Path
    alt_dist_mach: Path


@dataclass
class Plan:
    package_kind: str
    target: TargetFiles
    package: PackageFiles
    actions: list[str]


def fail(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def timestamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def same_file_content(a: Path, b: Path) -> bool:
    if not a.exists() or not b.exists() or a.stat().st_size != b.stat().st_size:
        return False
    return sha256_file(a) == sha256_file(b)


def backup_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.backup.{timestamp()}")


def backup_file(path: Path, dry_run: bool) -> Path | None:
    if not path.exists():
        return None
    destination = backup_path(path)
    if dry_run:
        print(f"DRY-RUN: would create backup {destination}")
        return destination
    shutil.copy2(path, destination)
    print(f"Backup created: {destination}")
    return destination


def detect_eol(data: bytes) -> str:
    crlf_count = data.count(b"\r\n")
    lf_only_count = data.count(b"\n") - crlf_count
    return "\r\n" if crlf_count > lf_only_count else "\n"


def split_lines(data: bytes) -> tuple[list[str], str, bool]:
    eol = detect_eol(data)
    has_final_eol = data.endswith(b"\n") or data.endswith(b"\r")
    text = data.decode("utf-8", errors="strict")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if has_final_eol and lines and lines[-1] == "":
        lines = lines[:-1]
    return lines, eol, has_final_eol


def join_lines(lines: list[str], eol: str, has_final_eol: bool) -> bytes:
    payload = eol.join(lines)
    if has_final_eol:
        payload += eol
    return payload.encode("utf-8")


def read_logical_lines(path: Path) -> list[str]:
    lines, _, _ = split_lines(path.read_bytes())
    return lines


def is_commented(line: str) -> bool:
    return line.lstrip().startswith("--")


def line_has_non_commented(line: str, search_text: str) -> bool:
    return search_text in line and not is_commented(line)


def find_non_commented_line(lines: list[str], search_text: str) -> int:
    for index, line in enumerate(lines):
        if line_has_non_commented(line, search_text):
            return index
    return -1


def contains_non_commented_line(lines: list[str], search_text: str) -> bool:
    return find_non_commented_line(lines, search_text) >= 0


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        fail(f"{label} not found: {path}", 2)
    if not path.is_file():
        fail(f"{label} is not a file: {path}", 2)


def resolve_package_dir(path: Path | None) -> PackageFiles:
    root = (path or Path(__file__).resolve().parent).expanduser().resolve()
    files = PackageFiles(
        root=root,
        table=root / TABLE_FILE_NAME,
        alt_dist=root / ALT_DIST_FILE_NAME,
        alt_dist_mach=root / ALT_DIST_MACH_FILE_NAME,
    )
    require_file(files.table, "table file")
    require_file(files.alt_dist, "take_alt_dist hook file")
    require_file(files.alt_dist_mach, "take_alt_dist_mach hook file")
    return files


def candidate_lua_paths(base: Path) -> list[Path]:
    base = base.expanduser()
    if base.is_file():
        return [base] if base.name == LUA_FILE_NAME else []

    direct = base / LUA_FILE_NAME
    if direct.exists():
        return [direct]

    canonical = base / "plugins" / "xlua" / "scripts" / "B738.a_fms" / LUA_FILE_NAME
    if canonical.exists():
        return [canonical]

    if not base.exists() or not base.is_dir():
        return []

    return sorted(base.rglob(f"plugins/xlua/scripts/B738.a_fms/{LUA_FILE_NAME}"))


def resolve_target(path: Path | None) -> TargetFiles:
    base = (path or Path.cwd()).expanduser()
    candidates = candidate_lua_paths(base)
    if not candidates:
        fail(
            "Could not find B738.a_fms.lua. Run from the B738.a_fms folder "
            "or pass --target /path/to/B738.a_fms.",
            2,
        )
    if len(candidates) > 1:
        print("Multiple B738.a_fms.lua candidates found:", file=sys.stderr)
        for candidate in candidates:
            print(f"  {candidate}", file=sys.stderr)
        fail("Pass --target with the exact B738.a_fms folder.", 2)

    lua = candidates[0].resolve()
    root = lua.parent
    return TargetFiles(
        root=root,
        lua=lua,
        table=root / TABLE_FILE_NAME,
        alt_dist=root / ALT_DIST_FILE_NAME,
        alt_dist_mach=root / ALT_DIST_MACH_FILE_NAME,
    )


def detect_package_kind(package: PackageFiles) -> str:
    text = package.table.read_text(encoding="utf-8", errors="strict")
    zibo_markers = ("B738_variant_test_zibo_800_variant", "B738DR_73x", "Zibo 737-800X")
    if any(marker in text for marker in zibo_markers):
        return "complete"
    return "levelup-only"


def copy_package_file(source: Path, destination: Path, dry_run: bool, actions: list[str]) -> None:
    if source.resolve() == destination.resolve():
        actions.append(f"{destination.name}: already in target folder")
        return

    if destination.exists() and same_file_content(source, destination):
        actions.append(f"{destination.name}: already up to date")
        return

    if destination.exists():
        backup_file(destination, dry_run)

    if dry_run:
        actions.append(f"{destination.name}: would copy from package")
        return

    shutil.copy2(source, destination)
    actions.append(f"{destination.name}: copied from package")


def known_hook_block_at(lines: list[str], start: int, content: list[str]) -> bool:
    if start < 0 or start + len(content) > len(lines):
        return False
    for offset, expected in enumerate(content):
        if lines[start + offset].strip() != expected.strip():
            return False
    return True


def remove_known_hook(lines: list[str], marker: str, content: list[str]) -> tuple[bool, int]:
    start = find_non_commented_line(lines, marker)
    if start < 0:
        return False, -1
    if not known_hook_block_at(lines, start, content):
        raise InstallerError(
            f"Existing hook marker '{marker}' was found, but the surrounding block "
            "does not match this installer. Refusing to edit it automatically."
        )
    del lines[start : start + len(content)]
    return True, start


def remove_dofile(lines: list[str]) -> bool:
    index = find_non_commented_line(lines, DOFILE_LINE)
    if index < 0:
        return False
    del lines[index]
    return True


def insert_after(lines: list[str], search_text: str, content: list[str]) -> int:
    index = find_non_commented_line(lines, search_text)
    if index < 0:
        raise InstallerError(f"Could not find non-commented line: {search_text}")
    lines[index + 1 : index + 1] = content
    return index + 1


def run_luac(path: Path) -> bool:
    luac = shutil.which("luac")
    if not luac:
        print("luac not found; syntax check skipped.")
        return True

    result = subprocess.run([luac, "-p", str(path)], text=True, capture_output=True)
    if result.returncode != 0:
        message = result.stderr or result.stdout or "luac failed"
        print(message.rstrip(), file=sys.stderr)
        return False
    print(f"luac -p: OK ({path.name})")
    return True


def analyze_install_state(target: TargetFiles, package: PackageFiles) -> dict[str, bool]:
    lines, _, _ = split_lines(target.lua.read_bytes())
    alt_dist_content = read_logical_lines(package.alt_dist)
    alt_dist_mach_content = read_logical_lines(package.alt_dist_mach)
    alt_dist_idx = find_non_commented_line(lines, ALT_DIST_MARKER)
    alt_dist_mach_idx = find_non_commented_line(lines, ALT_DIST_MACH_MARKER)
    return {
        "table_present": target.table.exists(),
        "table_matches_package": target.table.exists() and same_file_content(package.table, target.table),
        "dofile_present": contains_non_commented_line(lines, DOFILE_LINE),
        "alt_dist_hook_present": alt_dist_idx >= 0,
        "alt_dist_hook_matches": alt_dist_idx >= 0 and known_hook_block_at(lines, alt_dist_idx, alt_dist_content),
        "alt_dist_mach_hook_present": alt_dist_mach_idx >= 0,
        "alt_dist_mach_hook_matches": alt_dist_mach_idx >= 0
        and known_hook_block_at(lines, alt_dist_mach_idx, alt_dist_mach_content),
    }


def print_check(target: TargetFiles, package: PackageFiles, package_kind: str) -> int:
    state = analyze_install_state(target, package)
    print(f"Package: {package_kind}")
    print(f"Package folder: {package.root}")
    print(f"Target folder: {target.root}")
    for key, value in state.items():
        print(f"{key}: {'yes' if value else 'no'}")
    syntax_ok = run_luac(target.lua)
    if target.table.exists():
        syntax_ok = run_luac(target.table) and syntax_ok
    return 0 if syntax_ok and all(
        state[key]
        for key in (
            "table_present",
            "table_matches_package",
            "dofile_present",
            "alt_dist_hook_present",
            "alt_dist_hook_matches",
            "alt_dist_mach_hook_present",
            "alt_dist_mach_hook_matches",
        )
    ) else 1


def install(target: TargetFiles, package: PackageFiles, package_kind: str, dry_run: bool, replace_hooks: bool) -> int:
    actions: list[str] = []
    print(f"Package: {package_kind}")
    print(f"Package folder: {package.root}")
    print(f"Target folder: {target.root}")

    for source, destination in (
        (package.table, target.table),
        (package.alt_dist, target.alt_dist),
        (package.alt_dist_mach, target.alt_dist_mach),
    ):
        copy_package_file(source, destination, dry_run, actions)

    if not dry_run and not run_luac(target.table):
        return 1

    original_data = target.lua.read_bytes()
    lines, eol, has_final_eol = split_lines(original_data)
    alt_dist_content = read_logical_lines(package.alt_dist)
    alt_dist_mach_content = read_logical_lines(package.alt_dist_mach)
    changed = False

    try:
        if replace_hooks:
            removed, _ = remove_known_hook(lines, ALT_DIST_MARKER, alt_dist_content)
            if removed:
                verb = "would remove for replacement" if dry_run else "removed for replacement"
                actions.append(f"take_alt_dist hook: {verb}")
                changed = True
            removed, _ = remove_known_hook(lines, ALT_DIST_MACH_MARKER, alt_dist_mach_content)
            if removed:
                verb = "would remove for replacement" if dry_run else "removed for replacement"
                actions.append(f"take_alt_dist_mach hook: {verb}")
                changed = True

        if contains_non_commented_line(lines, DOFILE_LINE):
            actions.append("dofile hook: already present")
        else:
            insert_after(lines, "jit.off()", [DOFILE_LINE])
            verb = "would insert" if dry_run else "inserted"
            actions.append(f"dofile hook: {verb}")
            changed = True

        if contains_non_commented_line(lines, ALT_DIST_MARKER):
            actions.append("take_alt_dist hook: already present")
        else:
            insert_after(lines, ALT_DIST_FUNC, alt_dist_content)
            verb = "would insert" if dry_run else "inserted"
            actions.append(f"take_alt_dist hook: {verb}")
            changed = True

        if contains_non_commented_line(lines, ALT_DIST_MACH_MARKER):
            actions.append("take_alt_dist_mach hook: already present")
        else:
            insert_after(lines, ALT_DIST_MACH_FUNC, alt_dist_mach_content)
            verb = "would insert" if dry_run else "inserted"
            actions.append(f"take_alt_dist_mach hook: {verb}")
            changed = True
    except InstallerError as exc:
        fail(str(exc))

    for action in actions:
        print(action)

    if not changed:
        print("B738.a_fms.lua: already installed; no Lua changes required.")
        return 0

    new_data = join_lines(lines, eol, has_final_eol)
    if dry_run:
        print("DRY-RUN: would update B738.a_fms.lua")
        return 0

    backup_file(target.lua, dry_run=False)
    target.lua.write_bytes(new_data)
    print(f"Installed hooks into {target.lua}")

    if not (run_luac(target.lua) and run_luac(target.table)):
        target.lua.write_bytes(original_data)
        print("Syntax check failed; restored original B738.a_fms.lua.", file=sys.stderr)
        return 1

    return 0


def uninstall(target: TargetFiles, package: PackageFiles, dry_run: bool, remove_table: bool) -> int:
    actions: list[str] = []
    original_data = target.lua.read_bytes()
    lines, eol, has_final_eol = split_lines(original_data)
    alt_dist_content = read_logical_lines(package.alt_dist)
    alt_dist_mach_content = read_logical_lines(package.alt_dist_mach)
    changed = False

    try:
        if remove_dofile(lines):
            actions.append("dofile hook: removed")
            changed = True
        removed, _ = remove_known_hook(lines, ALT_DIST_MARKER, alt_dist_content)
        if removed:
            actions.append("take_alt_dist hook: removed")
            changed = True
        removed, _ = remove_known_hook(lines, ALT_DIST_MACH_MARKER, alt_dist_mach_content)
        if removed:
            actions.append("take_alt_dist_mach hook: removed")
            changed = True
    except InstallerError as exc:
        fail(str(exc))

    for action in actions:
        print(action)

    if changed:
        if dry_run:
            print("DRY-RUN: would update B738.a_fms.lua")
        else:
            backup_file(target.lua, dry_run=False)
            target.lua.write_bytes(join_lines(lines, eol, has_final_eol))
            print(f"Removed hooks from {target.lua}")
            if not run_luac(target.lua):
                target.lua.write_bytes(original_data)
                print("Syntax check failed; restored original B738.a_fms.lua.", file=sys.stderr)
                return 1
    else:
        print("B738.a_fms.lua: no installed hooks found.")

    if remove_table:
        for path in (target.table, target.alt_dist, target.alt_dist_mach):
            if path.exists():
                if dry_run:
                    print(f"DRY-RUN: would remove {path}")
                else:
                    backup_file(path, dry_run=False)
                    path.unlink()
                    print(f"Removed {path}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install, check, or uninstall the VNAV descent table package."
    )
    parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        help="B738.a_fms folder, B738.a_fms.lua file, or aircraft root. Defaults to current directory.",
    )
    parser.add_argument(
        "--package-dir",
        type=Path,
        help="Folder containing the table file and hook snippets. Defaults to the installer folder.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Inspect the target and run syntax check without changing files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned install or uninstall actions without writing files.",
    )
    parser.add_argument(
        "--replace-hooks",
        action="store_true",
        help="Replace existing known hook blocks with the hook snippets from the package.",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the installer hooks from B738.a_fms.lua.",
    )
    parser.add_argument(
        "--remove-table",
        action="store_true",
        help="With --uninstall, also remove package files after backing them up.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    package = resolve_package_dir(args.package_dir)
    target = resolve_target(args.target)
    package_kind = detect_package_kind(package)

    if args.check:
        return print_check(target, package, package_kind)
    if args.uninstall:
        return uninstall(target, package, args.dry_run, args.remove_table)
    return install(target, package, package_kind, args.dry_run, args.replace_hooks)


if __name__ == "__main__":
    raise SystemExit(main())

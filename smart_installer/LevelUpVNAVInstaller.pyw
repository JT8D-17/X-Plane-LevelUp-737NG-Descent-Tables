#!/usr/bin/env python3
"""
Double-click friendly GUI for the VNAV descent table installer.
"""

from __future__ import annotations

import contextlib
import io
import os
import queue
import sys
import threading
import traceback
from pathlib import Path

try:
    from tkinter import (
        BOTH,
        DISABLED,
        END,
        LEFT,
        NORMAL,
        RIGHT,
        X,
        Button,
        Checkbutton,
        Frame,
        IntVar,
        Label,
        Listbox,
        Radiobutton,
        Scrollbar,
        StringVar,
        Tk,
        filedialog,
        messagebox,
    )
    from tkinter.scrolledtext import ScrolledText
except Exception as exc:  # pragma: no cover - depends on local Python build
    TKINTER_IMPORT_ERROR = exc
else:
    TKINTER_IMPORT_ERROR = None

import install_vnav_descent_tables as core


APP_TITLE = "LevelUp VNAV Descent Table Installer"
SUPPORTED_XPLANE_NAMES = ("X-Plane 12", "X-Plane 11")


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).lower() if sys.platform == "win32" else str(resolved)
        if key not in seen:
            seen.add(key)
            result.append(resolved)
    return result


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)).resolve()
    return Path(__file__).resolve().parent


def likely_xplane_roots() -> list[Path]:
    home = Path.home()
    roots: list[Path] = []

    for name in SUPPORTED_XPLANE_NAMES:
        roots.extend(
            [
                Path.cwd() / name,
                home / name,
                home / "Desktop" / name,
                home / "Downloads" / name,
                home / "Documents" / name,
                home / "Games" / name,
            ]
        )

    if sys.platform == "darwin":
        for name in SUPPORTED_XPLANE_NAMES:
            roots.append(Path("/Applications") / name)
        volumes = Path("/Volumes")
        if volumes.exists():
            for volume in volumes.iterdir():
                for name in SUPPORTED_XPLANE_NAMES:
                    roots.append(volume / name)
    elif sys.platform == "win32":
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{letter}:/")
            if drive.exists():
                for name in SUPPORTED_XPLANE_NAMES:
                    roots.extend(
                        [
                            drive / name,
                            drive / "X-Plane" / name,
                            drive / "Games" / name,
                            drive / "SteamLibrary" / "steamapps" / "common" / name,
                            drive / "Program Files (x86)" / "Steam" / "steamapps" / "common" / name,
                        ]
                    )
    else:
        for name in SUPPORTED_XPLANE_NAMES:
            roots.extend(
                [
                    Path("/opt") / name,
                    Path("/usr/local/games") / name,
                    home / ".steam" / "steam" / "steamapps" / "common" / name,
                    home / ".local" / "share" / "Steam" / "steamapps" / "common" / name,
                ]
            )
        for mount_root in (Path("/mnt"), Path("/media") / home.name):
            if mount_root.exists():
                for mount in mount_root.iterdir():
                    for name in SUPPORTED_XPLANE_NAMES:
                        roots.append(mount / name)

    return [path for path in unique_paths(roots) if path.exists()]


def discover_lua_targets(extra_roots: list[Path] | None = None) -> list[core.TargetFiles]:
    app_dir = runtime_dir()
    roots = [Path.cwd(), app_dir, app_dir.parent]
    roots.extend(likely_xplane_roots())
    if extra_roots:
        roots.extend(extra_roots)

    lua_paths: list[Path] = []
    for root in unique_paths(roots):
        try:
            lua_paths.extend(core.candidate_lua_paths(root))
        except OSError:
            continue

    targets: list[core.TargetFiles] = []
    for lua in unique_paths(lua_paths):
        try:
            targets.append(core.resolve_target(lua))
        except SystemExit:
            continue
    return sorted(targets, key=lambda target: target.root.as_posix().lower())


def path_contains_levelup(path: Path) -> bool:
    lowered = path.as_posix().lower()
    return "levelup" in lowered or "737ng series" in lowered or "737ng" in lowered


def target_label(target: core.TargetFiles) -> str:
    parts = target.root.parts
    aircraft = None
    for index, part in enumerate(parts):
        if part.lower() == "aircraft" and index + 1 < len(parts):
            aircraft = parts[index + 1]
            break
    prefix = "[LevelUp] " if path_contains_levelup(target.root) else ""
    if aircraft:
        return f"{prefix}{aircraft} - {target.root}"
    return f"{prefix}{target.root}"


def package_candidates(script_dir: Path) -> dict[str, list[Path]]:
    app_resources = script_dir.parent / "Resources"
    return {
        "levelup-only": [
            script_dir,
            script_dir / "levelup_only",
            app_resources / "levelup_only",
            script_dir.parent / "levelup_only",
            script_dir.parent,
        ],
        "complete": [
            script_dir,
            script_dir / "complete",
            app_resources / "complete",
            script_dir.parent,
        ],
    }


def resolve_package_for_kind(kind: str) -> core.PackageFiles:
    script_dir = runtime_dir()
    candidates = package_candidates(script_dir).get(kind, [])
    for candidate in candidates:
        if not (
            (candidate / core.TABLE_FILE_NAME).is_file()
            and (candidate / core.ALT_DIST_FILE_NAME).is_file()
            and (candidate / core.ALT_DIST_MACH_FILE_NAME).is_file()
        ):
            continue
        try:
            package = core.resolve_package_dir(candidate)
            if core.detect_package_kind(package) == kind:
                return package
        except SystemExit:
            continue
    raise RuntimeError(f"Could not find package files for '{kind}'.")


class InstallerApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("980x700")
        self.targets: list[core.TargetFiles] = []
        self.queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self.package_kind = StringVar(value="levelup-only")
        self.replace_hooks = IntVar(value=0)
        self.remove_table = IntVar(value=0)
        self.status_text = StringVar(value="Ready.")

        self.build_ui()
        self.root.after(100, self.process_queue)
        self.scan_targets()

    def build_ui(self) -> None:
        top = Frame(self.root, padx=12, pady=10)
        top.pack(fill=X)

        Label(top, text="Package:").pack(side=LEFT)
        Radiobutton(
            top,
            text="LevelUp only",
            variable=self.package_kind,
            value="levelup-only",
            command=self.refresh_status,
        ).pack(side=LEFT, padx=(8, 0))
        Radiobutton(
            top,
            text="Complete",
            variable=self.package_kind,
            value="complete",
            command=self.refresh_status,
        ).pack(side=LEFT, padx=(8, 20))

        Checkbutton(top, text="Replace known existing hooks", variable=self.replace_hooks).pack(side=LEFT)
        Checkbutton(top, text="Remove package files on uninstall", variable=self.remove_table).pack(
            side=LEFT, padx=(12, 0)
        )

        Button(top, text="Rescan", command=self.scan_targets).pack(side=RIGHT)
        Button(top, text="Choose Folder...", command=self.choose_folder).pack(side=RIGHT, padx=(0, 8))

        mid = Frame(self.root, padx=12)
        mid.pack(fill=BOTH, expand=False)
        Label(mid, text="Detected B738.a_fms targets:").pack(anchor="w")

        list_frame = Frame(mid)
        list_frame.pack(fill=BOTH, expand=False)
        self.target_list = Listbox(list_frame, height=10, exportselection=False)
        scrollbar = Scrollbar(list_frame, orient="vertical", command=self.target_list.yview)
        self.target_list.configure(yscrollcommand=scrollbar.set)
        self.target_list.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill="y")
        self.target_list.bind("<<ListboxSelect>>", lambda _event: self.refresh_status())

        buttons = Frame(self.root, padx=12, pady=10)
        buttons.pack(fill=X)
        Button(buttons, text="Install / Update", command=self.install_selected, width=18).pack(side=LEFT)
        Button(buttons, text="Check", command=self.check_selected, width=12).pack(side=LEFT, padx=(8, 0))
        Button(buttons, text="Uninstall", command=self.uninstall_selected, width=12).pack(side=LEFT, padx=(8, 0))
        Button(buttons, text="Open Target Folder", command=self.open_target_folder, width=18).pack(
            side=LEFT, padx=(8, 0)
        )

        Label(self.root, textvariable=self.status_text, padx=12).pack(fill=X, anchor="w")

        self.log = ScrolledText(self.root, height=18, padx=8, pady=8)
        self.log.pack(fill=BOTH, expand=True, padx=12, pady=(0, 12))
        self.log.configure(state=DISABLED)

    def log_line(self, text: str = "") -> None:
        self.log.configure(state=NORMAL)
        self.log.insert(END, text + "\n")
        self.log.see(END)
        self.log.configure(state=DISABLED)

    def selected_target(self) -> core.TargetFiles | None:
        selection = self.target_list.curselection()
        if not selection:
            return None
        index = int(selection[0])
        if index < 0 or index >= len(self.targets):
            return None
        return self.targets[index]

    def selected_package(self) -> core.PackageFiles:
        return resolve_package_for_kind(self.package_kind.get())

    def set_busy(self, busy: bool, message: str) -> None:
        self.status_text.set(message)
        state = DISABLED if busy else NORMAL
        for child in self.root.winfo_children():
            self.set_child_state(child, state)
        self.log.configure(state=DISABLED)

    def set_child_state(self, widget, state: str) -> None:  # noqa: ANN001
        try:
            if widget is not self.log:
                widget.configure(state=state)
        except Exception:
            pass
        for child in widget.winfo_children():
            self.set_child_state(child, state)

    def scan_targets(self) -> None:
        self.run_task("Scanning common X-Plane locations...", self._scan_targets)

    def _scan_targets(self) -> None:
        targets = discover_lua_targets()
        self.queue.put(("targets", targets))

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select X-Plane, aircraft, or B738.a_fms folder")
        if not folder:
            return
        self.run_task(f"Scanning {folder}...", lambda: self.queue.put(("targets", discover_lua_targets([Path(folder)]))))

    def refresh_target_list(self, targets: list[core.TargetFiles]) -> None:
        self.targets = targets
        self.target_list.delete(0, END)
        for target in targets:
            self.target_list.insert(END, target_label(target))
        if targets:
            first_levelup = next((idx for idx, target in enumerate(targets) if path_contains_levelup(target.root)), 0)
            self.target_list.selection_set(first_levelup)
            self.target_list.see(first_levelup)
            self.status_text.set(f"Found {len(targets)} target(s).")
        else:
            self.status_text.set("No target found. Use Choose Folder.")
        self.refresh_status()

    def refresh_status(self) -> None:
        target = self.selected_target()
        if not target:
            return
        try:
            package = self.selected_package()
            state = core.analyze_install_state(target, package)
            installed = all(
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
            )
            if installed:
                self.status_text.set(f"{self.package_kind.get()} package is installed for selected target.")
            else:
                self.status_text.set(f"{self.package_kind.get()} package is not fully installed for selected target.")
        except Exception as exc:
            self.status_text.set(str(exc))

    def capture_operation(self, operation) -> tuple[int, str]:  # noqa: ANN001
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                result = operation()
            except SystemExit as exc:
                code = int(exc.code) if isinstance(exc.code, int) else 1
                return code, output.getvalue()
            except Exception:
                traceback.print_exc()
                return 1, output.getvalue()
        return int(result or 0), output.getvalue()

    def install_selected(self) -> None:
        target = self.selected_target()
        if not target:
            messagebox.showinfo(APP_TITLE, "Select a target first.")
            return
        package = self.selected_package()
        kind = core.detect_package_kind(package)

        def operation() -> int:
            return core.install(target, package, kind, dry_run=False, replace_hooks=bool(self.replace_hooks.get()))

        self.run_operation("Installing package...", operation)

    def check_selected(self) -> None:
        target = self.selected_target()
        if not target:
            messagebox.showinfo(APP_TITLE, "Select a target first.")
            return
        package = self.selected_package()
        kind = core.detect_package_kind(package)

        def operation() -> int:
            return core.print_check(target, package, kind)

        self.run_operation("Checking installation...", operation)

    def uninstall_selected(self) -> None:
        target = self.selected_target()
        if not target:
            messagebox.showinfo(APP_TITLE, "Select a target first.")
            return
        if not messagebox.askyesno(APP_TITLE, "Remove VNAV descent table hooks from the selected target?"):
            return
        package = self.selected_package()

        def operation() -> int:
            return core.uninstall(
                target,
                package,
                dry_run=False,
                remove_table=bool(self.remove_table.get()),
            )

        self.run_operation("Uninstalling package...", operation)

    def open_target_folder(self) -> None:
        target = self.selected_target()
        if not target:
            messagebox.showinfo(APP_TITLE, "Select a target first.")
            return
        path = target.root
        if sys.platform == "darwin":
            subprocess = __import__("subprocess")
            subprocess.Popen(["open", str(path)])
        elif sys.platform == "win32":
            import os

            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess = __import__("subprocess")
            subprocess.Popen(["xdg-open", str(path)])

    def run_operation(self, busy_message: str, operation) -> None:  # noqa: ANN001
        def worker() -> None:
            code, text = self.capture_operation(operation)
            self.queue.put(("operation", (code, text)))

        self.set_busy(True, busy_message)
        threading.Thread(target=worker, daemon=True).start()

    def run_task(self, busy_message: str, task) -> None:  # noqa: ANN001
        def worker() -> None:
            try:
                task()
            except Exception:
                self.queue.put(("error", traceback.format_exc()))

        self.set_busy(True, busy_message)
        threading.Thread(target=worker, daemon=True).start()

    def process_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "targets":
                    self.set_busy(False, "Ready.")
                    self.refresh_target_list(payload)  # type: ignore[arg-type]
                    self.log_line(f"Scan complete: {len(payload)} target(s) found.")
                elif kind == "operation":
                    self.set_busy(False, "Ready.")
                    code, text = payload  # type: ignore[misc]
                    if text:
                        self.log_line(text.rstrip())
                    if code == 0:
                        self.log_line("Operation completed successfully.")
                    else:
                        self.log_line(f"Operation failed with exit code {code}.")
                    self.refresh_status()
                elif kind == "error":
                    self.set_busy(False, "Ready.")
                    self.log_line(str(payload))
                    messagebox.showerror(APP_TITLE, str(payload))
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    if os.environ.get("LEVELUP_VNAV_INSTALLER_SELFTEST") == "1":
        print(f"runtime_dir={runtime_dir()}")
        for kind in ("levelup-only", "complete"):
            package = resolve_package_for_kind(kind)
            print(f"{kind}={package.root}")
        return 0

    if TKINTER_IMPORT_ERROR is not None:
        print("The graphical installer requires Python with Tkinter support.", file=sys.stderr)
        print(f"Tkinter error: {TKINTER_IMPORT_ERROR}", file=sys.stderr)
        print("Install Python from https://www.python.org/downloads/ or use the command-line installer.", file=sys.stderr)
        return 2

    app = InstallerApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

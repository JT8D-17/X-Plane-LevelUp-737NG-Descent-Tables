# Native packaging preparation

This folder prepares native end-user builds for the graphical installer.

## PyInstaller

PyInstaller is the fastest path to a clickable native app or executable on each
platform.

Install build dependency:

```bash
python -m pip install -r smart_installer/packaging/requirements-pyinstaller.txt
```

Build for the current platform:

```bash
python smart_installer/packaging/build_pyinstaller.py
```

Optional single-file build:

```bash
python smart_installer/packaging/build_pyinstaller.py --onefile
```

Output:

```text
dist/native/pyinstaller/
```

PyInstaller builds must be produced on the target platform:

- macOS build on macOS
- Windows build on Windows
- Linux build on Linux

A draft GitHub Actions workflow for platform-matrix builds is stored at:

```text
smart_installer/packaging/github-workflows/native-installer.yml
```

Copy it to `.github/workflows/native-installer.yml` when the native build path
should become active in the repository.

## Briefcase

Briefcase is the more native packaging path and can produce platform-native app
bundles or installers. The build script generates a temporary Briefcase project
from the same installer payload.

Install build dependency:

```bash
python -m pip install -r smart_installer/packaging/requirements-briefcase.txt
```

Prepare the generated Briefcase project:

```bash
python smart_installer/packaging/build_briefcase.py
```

Prepare and run Briefcase:

```bash
python smart_installer/packaging/build_briefcase.py --run
```

Output project:

```text
build/briefcase_project/
```

Briefcase configuration follows the standard `pyproject.toml` format documented
by BeeWare.

Briefcase signing/notarization and installer branding are intentionally not
configured yet. Those should be added only when the distribution identity is
settled.

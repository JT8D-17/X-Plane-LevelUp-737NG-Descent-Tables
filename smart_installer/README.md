# Smart VNAV descent table installer

This is a local prototype for a platform-independent installer.

It does not distribute a modified `B738.a_fms.lua`. It patches the user's local
file in-place, preserves LF/CRLF line endings, creates timestamped backups, and
uses `luac -p` when available.

## Double-click use

For normal users, start the graphical installer:

- macOS: double-click `Launch_LevelUp_VNAV_Installer.command`
- Windows: double-click `Launch_LevelUp_VNAV_Installer.bat`
- Linux: run or double-click `Launch_LevelUp_VNAV_Installer.sh`

This script-based GUI requires Python 3 with Tkinter. The launcher checks this
before starting the installer and prints a clear message if the local Python
installation is incomplete.

The graphical installer searches common X-Plane 12/11 locations automatically,
lists detected `B738.a_fms` targets, and installs the selected package with one
button.

The user can also choose the X-Plane folder, an aircraft folder, or the exact
`B738.a_fms` folder manually.

For a fully self-contained end-user release, this GUI can later be bundled as
native macOS/Windows/Linux executables so users do not need to install Python.

## Command-line use

From the folder that contains `B738.a_fms.lua`:

```bash
python3 install_vnav_descent_tables.py --package-dir /path/to/package
```

Or pass the target explicitly:

```bash
python3 install_vnav_descent_tables.py \
  --package-dir /path/to/package \
  /path/to/plugins/xlua/scripts/B738.a_fms
```

The target may be:

- the `B738.a_fms` folder,
- the `B738.a_fms.lua` file,
- or an aircraft root that contains `plugins/xlua/scripts/B738.a_fms/B738.a_fms.lua`.

## Useful commands

Dry-run:

```bash
python3 install_vnav_descent_tables.py --dry-run --package-dir /path/to/package /path/to/B738.a_fms
```

Check installation state:

```bash
python3 install_vnav_descent_tables.py --check --package-dir /path/to/package /path/to/B738.a_fms
```

Replace known existing hook blocks:

```bash
python3 install_vnav_descent_tables.py --replace-hooks --package-dir /path/to/package /path/to/B738.a_fms
```

Uninstall hooks:

```bash
python3 install_vnav_descent_tables.py --uninstall --package-dir /path/to/package /path/to/B738.a_fms
```

Uninstall hooks and remove package files after backing them up:

```bash
python3 install_vnav_descent_tables.py --uninstall --remove-table --package-dir /path/to/package /path/to/B738.a_fms
```

## Package detection

The installer detects whether the selected package is:

- `complete`: LevelUp tables plus custom Zibo 737-800X profile,
- `levelup-only`: only LevelUp variants via `zibomod/b737_variant`.

The package kind is printed before any install/check/uninstall action.

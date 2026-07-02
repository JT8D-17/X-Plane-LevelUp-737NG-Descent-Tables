# LevelUp-only VNAV descent tables for the LevelUp 737NG Series

## Scope

This package adds variant-specific VNAV descent tables for the LevelUp 737NG Series only.

It is intentionally different from the complete package:

- It supports only LevelUp variants exposed through `zibomod/b737_variant`.
- It does not add a custom Zibo 737-800X profile.
- It does not use the legacy Zibo `B738DR_73x` variant fallback.
- If `zibomod/b737_variant` is missing or does not map to a known LevelUp variant, the original Lua calculation continues unchanged.

Supported LevelUp variant IDs:

- `0`: LevelUp 737-800NG
- `1`: LevelUp 737-900NG
- `2`: LevelUp 737-700NG
- `3`: LevelUp 737-600NG
- `4`: LevelUp 737-900ER

## Background

The LevelUp 737NG uses `B738.a_fms.lua` for its VNAV descent distance calculation. The original table set is based on the 737-800 profile, which is not appropriate for every LevelUp NG variant.

This package installs source-backed descent distance tables for the LevelUp variants while leaving any non-LevelUp aircraft on the original Lua logic.

## Contents

- `B738.a_fms_levelup_tables.lua`: LevelUp-only variant table package.
- `Add_to_take_alt_dist.txt`: Hook block for `take_alt_dist`.
- `Add_to_take_alt_dist_mach.txt`: Hook block for `take_alt_dist_mach`.
- `z_Install.py`: Python installer that preserves LF/CRLF line endings, creates a backup, avoids duplicate hooks, and runs `luac -p` when available.

## Installation

1. Copy these files into the LevelUp `plugins/xlua/scripts/B738.a_fms` folder:

   - `B738.a_fms_levelup_tables.lua`
   - `Add_to_take_alt_dist.txt`
   - `Add_to_take_alt_dist_mach.txt`
   - `z_Install.py`

2. Run the installer from that folder:

   ```bash
   python3 z_Install.py
   ```

   On Windows, use:

   ```bat
   py z_Install.py
   ```

3. Load the LevelUp 737NG and check `Log.txt` for:

   ```text
   LevelUp VNAV descent tables loaded!
   ```

## Notes

The installer edits the local `B738.a_fms.lua` file in-place. This avoids distributing a modified Zibo/LevelUp Lua file.

After every update that replaces `B738.a_fms.lua`, run the installer again.

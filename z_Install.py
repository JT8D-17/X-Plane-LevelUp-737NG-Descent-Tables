#!/usr/bin/env python3
"""
Modifies B738.a_fms.lua:
1. Creates a backup of the original file.
2. Inserts dofile("B738.a_fms_levelup_tables.lua") after the non-commented jit.off() line.
3. Inserts content from Add_to_take_alt_dist.txt after the non-commented
   function take_alt_dist(x_idx_alt, x_spd_alt, x_spd_wnd_alt, x_flap) line.
4. Inserts content from Add_to_take_alt_dist_mach.txt after the non-commented
   function take_alt_dist_mach(x_idx_alt, x_spd_alt, x_spd_wnd_alt) line.
"""

import shutil
import sys

LUA_FILE = "B738.a_fms.lua"
BACKUP_FILE = "B738.a_fms.backup"
TABLE_FILE_ALT_DIST = "Add_to_take_alt_dist.txt"
TABLE_FILE_ALT_DIST_MACH = "Add_to_take_alt_dist_mach.txt"
DOFILE_LINE = 'dofile("B738.a_fms_levelup_tables.lua")'


def is_commented(line):
    """Return True if the Lua line is commented out (starts with -- after stripping whitespace)."""
    return line.lstrip().startswith("--")


def find_non_commented_line(lines, search_text):
    """
    Return the index of the first line containing search_text that is NOT commented out.
    Returns -1 if not found.
    """
    for i, line in enumerate(lines):
        if search_text in line and not is_commented(line):
            return i
    return -1


def read_lines_safe(filename):
    """Read all lines, ensuring the last line ends with a newline."""
    with open(filename, "r") as f:
        lines = f.readlines()
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return lines


def main():
    # -------------------------------------------------------------------
    # Step 1: Backup
    # -------------------------------------------------------------------
    print(f"[1/4] Creating backup: {LUA_FILE} -> {BACKUP_FILE}")
    shutil.copy2(LUA_FILE, BACKUP_FILE)

    # -------------------------------------------------------------------
    # Read source files
    # -------------------------------------------------------------------
    lua_lines = read_lines_safe(LUA_FILE)
    alt_dist_content = read_lines_safe(TABLE_FILE_ALT_DIST)
    alt_dist_mach_content = read_lines_safe(TABLE_FILE_ALT_DIST_MACH)

    # -------------------------------------------------------------------
    # Collect all insertions as (insert_after_index, content_lines)
    # -------------------------------------------------------------------
    insertions = []

    # --- Step 2: Insert dofile below jit.off() ---
    idx_jit = find_non_commented_line(lua_lines, "jit.off()")
    if idx_jit == -1:
        print("ERROR: Could not find a non-commented 'jit.off()' line in the Lua file.")
        sys.exit(1)
    insertions.append((idx_jit + 1, [DOFILE_LINE + "\n"]))
    print(f"[2/4] Found 'jit.off()' at line {idx_jit + 1}. "
          f"Will insert dofile line below it.")

    # --- Step 3: Insert alt_dist content below the function declaration ---
    func_3 = "function take_alt_dist(x_idx_alt, x_spd_alt, x_spd_wnd_alt, x_flap)"
    idx_func3 = find_non_commented_line(lua_lines, func_3)
    if idx_func3 == -1:
        print(f"ERROR: Could not find a non-commented line matching:\n  {func_3}")
        sys.exit(1)
    insertions.append((idx_func3 + 1, alt_dist_content))
    print(f"[3/4] Found function declaration at line {idx_func3 + 1}. "
          f"Will insert {len(alt_dist_content)} lines from {TABLE_FILE_ALT_DIST} below it.")

    # --- Step 4: Insert alt_dist_mach content below the function declaration ---
    func_4 = "function take_alt_dist_mach(x_idx_alt, x_spd_alt, x_spd_wnd_alt)"
    idx_func4 = find_non_commented_line(lua_lines, func_4)
    if idx_func4 == -1:
        print(f"ERROR: Could not find a non-commented line matching:\n  {func_4}")
        sys.exit(1)
    insertions.append((idx_func4 + 1, alt_dist_mach_content))
    print(f"[4/4] Found function declaration at line {idx_func4 + 1}. "
          f"Will insert {len(alt_dist_mach_content)} lines from {TABLE_FILE_ALT_DIST_MACH} below it.")

    # -------------------------------------------------------------------
    # Apply insertions from bottom to top (preserves line indices)
    # -------------------------------------------------------------------
    insertions.sort(key=lambda x: x[0], reverse=True)
    for insert_at, content in insertions:
        lua_lines[insert_at:insert_at] = content

    # -------------------------------------------------------------------
    # Write the modified Lua file
    # -------------------------------------------------------------------
    with open(LUA_FILE, "w") as f:
        f.writelines(lua_lines)

    print(f"\n✓ Done! Modified file written to {LUA_FILE}")
    print(f"✓ Original backup saved as {BACKUP_FILE}")


if __name__ == "__main__":
    main()

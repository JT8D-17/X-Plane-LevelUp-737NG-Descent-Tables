#!/usr/bin/env python3
"""
Extract patch blocks from B738.a_fms.35-levelup-ng-vnav-prototype.patch
and save them to separate files with proper headers/footers.
"""

from datetime import datetime


def read_patch_file(filepath):
    """Read the entire patch file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def extract_main_tables_block(content):
    """Extract the main LevelUp VNAV tables block (between BEGIN and END markers)."""
    begin_marker = '-- BEGIN UPSTREAM VARIANT TEST:'
    end_marker = '-- END UPSTREAM VARIANT TEST:'

    start_idx = None
    end_idx = None

    lines = content.split('\n')

    for i, line in enumerate(lines):
        # Check markers against the ORIGINAL line (with '+' prefix intact)
        if begin_marker in line:
            start_idx = i
        elif end_marker in line and start_idx is not None:
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        raise ValueError("Could not find BEGIN/END markers for tables block")

    # Extract all lines between markers (inclusive), strip '+' prefix only
    block_lines = []
    for line in lines[start_idx:end_idx + 1]:
        if line.startswith('+') and not line.startswith('+++'):
            block_lines.append(line[1:])  # Remove just the leading '+'
        elif line.startswith('-') and not line.startswith('---'):
            continue  # Skip deletion lines
        else:
            block_lines.append(line)

    return '\n'.join(block_lines)


def write_lua_file(filename, content):
    """Write Block 1 (tables) with header and footer."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')

    # Header with empty line above title and below timestamp
    header = f'''--[[

VNAV DESCENT TABLES FOR THE LEVELUP 737NG SERIES BY WAHLTHO & RANDOMUSER
Generated: {timestamp}

]]

'''

    # Footer with empty line above [[END OF FILE]]
    footer = '''

--[[END OF FILE]]
print("LevelUp VNAV descent tables loaded!")'''

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(header + content + footer)


def write_text_file(filename, content):
    """Write plain text block."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
        if content and not content.endswith('\n'):
            f.write('\n')


def main():
    input_file = 'B738.a_fms.35-levelup-ng-vnav-prototype.patch'

    print(f"Reading patch file: {input_file}")
    content = read_patch_file(input_file)

    # ── Step 1: Extract main tables block ──────────────────────
    print("\n=== Step 1: Extracting main tables block ===")
    tables_content = extract_main_tables_block(content)
    print(f"Tables block: {len(tables_content)} characters")
    write_lua_file('B738.a_fms_levelup_tables.lua', tables_content)
    print("✓ Wrote B738.a_fms_levelup_tables.lua")

    # ── Step 2 & 3: Extract the two insertion hunks ───────────
    print("\n=== Step 2 & 3: Identifying insertion hunks ===")
    lines = content.split('\n')

    # Collect ALL addition hunks first, assign by sequence number
    all_hunks_added = []
    current_hunk_lines = []
    current_context_line = None

    for i, line in enumerate(lines):
        # Detect hunk header (@@ ... @@)
        if line.startswith('@@'):
            # Save previous hunk if any additions were collected
            if current_hunk_lines:
                all_hunks_added.append(current_hunk_lines)
                current_hunk_lines = []

            # Scan ahead a bit to capture context line (the "-" lines)
            current_context_line = ''
            for j in range(i + 1, min(i + 10, len(lines))):
                curr_line = lines[j]
                if curr_line.startswith('-') and not curr_line.startswith('---'):
                    current_context_line += curr_line + '\n'
                elif curr_line.startswith('@@'):
                    break  # Next hunk started
            continue

        # Skip +++ and --- lines
        if line.startswith('+++') or line.startswith('---'):
            continue

        # Collect addition lines (single '+', not '+++' or '---')
        if line.startswith('+') and not line.startswith('+++'):
            stripped = line[1:]
            current_hunk_lines.append(stripped)

    # Don't forget the last hunk
    if current_hunk_lines:
        all_hunks_added.append(current_hunk_lines)

    print(f"  Found {len(all_hunks_added)} addition hunk(s)")

    # Now filter to only keep small insertion hunks (not the large tables block)
    # The tables block has hundreds of lines, insertion hunks have ~4 lines each
    insertion_hunks = []
    for idx, hunk in enumerate(all_hunks_added):
        if len(hunk) <= 10:  # Small insertion hunks (<=10 lines)
            insertion_hunks.append((idx, hunk))
            print(f"  Hunk #{idx}: {len(hunk)} lines (small insertion)")
        else:
            print(f"  Skipped large hunk #{idx}: {len(hunk)} lines (tables)")

    # Assign by sequence: first small hunk = take_alt_dist, second = take_alt_dist_mach
    take_alt_hunk = None
    take_mach_hunk = None

    if len(insertion_hunks) >= 1:
        take_alt_hunk = insertion_hunks[0][1]
        print(f"\nAssigned: take_alt_dist <- Hunk #{insertion_hunks[0][0]} ({len(take_alt_hunk)} lines)")
    if len(insertion_hunks) >= 2:
        take_mach_hunk = insertion_hunks[1][1]
        print(f"Assigned: take_alt_dist_mach <- Hunk #{insertion_hunks[1][0]} ({len(take_mach_hunk)} lines)")

    # Clean up trailing empty lines
    if take_alt_hunk:
        while take_alt_hunk and not take_alt_hunk[-1].strip():
            take_alt_hunk.pop()
    if take_mach_hunk:
        while take_mach_hunk and not take_mach_hunk[-1].strip():
            take_mach_hunk.pop()

    # ── Write output files ─────────────────────────────────────
    print("\n=== Writing output files ===")

    take_alt_content = '\n'.join(take_alt_hunk) if take_alt_hunk else ''
    write_text_file('Add_to_take_alt_dist.txt', take_alt_content)
    print("✓ Wrote Add_to_take_alt_dist.txt")

    take_mach_content = '\n'.join(take_mach_hunk) if take_mach_hunk else ''
    write_text_file('Add_to_take_alt_dist_mach.txt', take_mach_content)
    print("✓ Wrote Add_to_take_alt_dist_mach.txt")

    print("\n=== Summary ===")
    print(f"  B738.a_fms_levelup_tables.lua ({len(tables_content)} chars)")
    print(f"  Add_to_take_alt_dist.txt ({len(take_alt_content)} chars)")
    print(f"  Add_to_take_alt_dist_mach.txt ({len(take_mach_content)} chars)")
    print("\nDone!")


if __name__ == '__main__':
    main()

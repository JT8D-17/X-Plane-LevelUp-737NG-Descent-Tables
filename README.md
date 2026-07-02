# Better VNAV descent tables for the LevelUp 737NG Series for X-Plane 12

&nbsp;

## Introduction

This repository provides a do-it-yourself installer that adds individual VNAV descent tables to the [LevelUp 737NG (v2)](https://forum.thresholdx.net/files/file/4108-737ng-series-for-x-plane-12/) for X-Plane 12. Any LevelUp 737 release for X-Plane 11 is not supported at all.

&nbsp;

## Background

The LevelUp 737NG uses the Lua scripts and the plugin from Zibo's Boeing 737-800X project for its systems. While there are some provisions to account for the different 737 variants included in the LevelUp package (737-600, -700, -800, -900, -900ER), the VNAV descent distance calculation tables are exclusively for the 737-800. When used with another variant that is not an -800, these tables will lead to implausible autopilot behaviour on descent.

Over the course of a conversation over the issue with Thomas W. (wahltho on X-Plane.org), he created variant-specific (737-600, -700, -800, 900, -900ER) descent distance tables, derived from a Flight Crew Operations Manual for the 737NG. This repository packages those tables as a Python-based installer, so users do not need to edit _B738.a_fms.lua_ with platform-specific diff tools.

The installer will likely stay relevant until Zibo incorporates these tables into the _B738.a_fms.lua_ script by default.

&nbsp;

## Disclaimer

Before you install or use this, you **must** acknowledge that:
- This only adds variant-specific descent distance calculation tables (Table: "Descent .78/280/25" in Boeing's FCOM) with wind corrections. Anything else in the FMS and autopilot system that is incorrect for non-800 variants in the LevelUp 737 Series is not touched or improved.  
- This installer is unofficial, which means it is not supported by LevelUp or Zibo!
- To avoid violating Zibo's copyright on the Lua files, _B738.a_fms.lua_ must be edited in order to use the VNAV descent tables (see the installation instructions). If you are not comfortable with that, **do not use this**!
- **After each and every(!) update to _B738.a_fms.lua_, the installation (see below) must be repeated(!).**

&nbsp;

## Usage

Once installed and working, 737NG variant detection is completely automatic, based on the "zibomod/b737_variant" dataref.
In case the variant-specific descent calculation fails, Zibo's default VNAV descent logic will be used as a fallback.

&nbsp;

## Content

This repository contains the following files and folders:
- "Patch_Converter" folder:   
Contains maintenance material for regenerating the installer source files from an older diff-based prototype. This folder is not required for installation and usage and therefore not part of a release.
- _Add_to_take_alt_dist.txt_ and _Add_to_take_alt_dist_mach.txt_:    
These files contain lines of code that must be added to _B738.a_fms.lua_. This is done automatically via Python script or via manual editing (see the installation instructions).
- _B738.a_fms_levelup_tables.lua_:    
This file contains the actual descent tables for the 737NG variants and must be present in the "B738.a_fms" folder.
- _z_Install.py_:    
A [Python](www.python.org) installation script that modifies _B738.a_fms.lua_, preserves the file's existing LF/CRLF line endings, creates a backup before modification and avoids duplicate hook insertion.
- "realbench_logger" folder:
Contains the Realbench logging package for descent-profile test flights. The installation and usage instructions are inside the ZIP.

&nbsp;

## Installation

1) Download a release from the "releases" page and unzip it.

2) Move these files into the _737NG Series_V2(...)/plugins/xlua/scripts/B738.a_fms_ folder:
	- _B738.a_fms_levelup_tables.lua_
	- _Add_to_take_alt_dist.txt_
	- _Add_to_take_alt_dist_mach.txt_
	- (Optionally) _z_Install.py_
	
3) Run _z_Install.py_, which will make a backup of _B738.a_fms.lua_ and perform all the required modifications for you. The installation is finished. Ignore step 4 below.

	From a terminal in the _B738.a_fms_ folder:

	```bash
	python3 z_Install.py
	```

	On Windows, use `py z_Install.py` or `python z_Install.py` if `python3` is not available.
	
4) Manual installation is only the fallback if Python is not available. Make a backup of _B738.a_fms.lua_ before you begin.
	- Open _B738.a_fms.lua_ with a text editor like Notepad or [Notepad++](https://notepad-plus-plus.org/) or similar.        
	- Add the line      
	```dofile("B738.a_fms_levelup_tables.lua")```      
 below `jit.off()`.    
	- Add all the lines from _Add_to_take_alt_dist.txt_ directly below   
`function take_alt_dist(x_idx_alt, x_spd_alt, x_spd_wnd_alt, x_flap)`    
 (Caution: The line must **not** start with a Lua comment mark (`--`, i.e. double dash)!!)    
and `local altitude_distance = 0`.
	- Add all the lines from _Add_to_take_alt_dist_mach.txt_ directly below    
`function take_alt_dist_mach(x_idx_alt, x_spd_alt, x_spd_wnd_alt)`    
(Caution: The line must **not** start with a Lua comment mark (`--`, i.e. double dash)!!)    
and `local altitude_distance = 0`.
	- Save and close _B738.a_fms.lua_.

If the installation has succeeded, you will find a "LevelUp VNAV descent tables loaded!" message in Log.txt after you've loaded the LevelUp 737NG.

&nbsp;

## Unstallation

Delete the modified _B738.a_fms.lua_ file and restore the backup that was created by the Python install script or yourself.

&nbsp;

## Dealing with Zibo Plugin and Script Updates

After each and every update of Zibo's plugin and Lua scripts, you must perform installation steps 2 to 4. 

&nbsp;

## Troubleshooting

If installation fails or behaves differently across operating systems, use _z_Install.py_ from a terminal instead of a text editor. The installer preserves the target file's line endings and checks for duplicate installation.

When "LevelUp VNAV descent tables loaded!" does not appear in Log.txt, installation steps 3 or 4 went wrong or you forgot to perform these steps after an update to Zibo's Lua scripts.

If there is a bug in the code for the new tables, _B738.a_fms.lua_ will at the earliest freeze during the VNAV calculations performed while preparing FMS on the ground. This will usually be accompanied by error messages in X-Plane's Developer Console or _Log.txt_. Check that all installation steps were performed correctly.

If VNAV descent works, but continues to exhibit lower than sensible vertical speeds in variants except the -800, make sure that the code for the new tables has been correctly hooked into   
`function take_alt_dist(x_idx_alt, x_spd_alt, x_spd_wnd_alt, x_flap)` and   
`function take_alt_dist_mach(x_idx_alt, x_spd_alt, x_spd_wnd_alt)` (see installation step 4).  

&nbsp;

## Credits

Thomas Wahl (wahltho) for the implementation of the descent tables for the 737NG series.

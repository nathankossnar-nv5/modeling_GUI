"""Compare file contents between two folders.
    This is where the GUI reads documenation from to show in the interface.  The parameters set up in the .yml file will also show up as variables in the GUI that can be set by the user.  See compare_paths_config.yml for an example of how to set up the .yml file for this script."""

from __future__ import annotations

import argparse
from pathlib import Path
import yaml
import filecmp
import sys


def main():
## GUI Set up requires arparse and yaml.safe_load to load config file.  Runs normally without --config arg.  No change in behavior, only allows variable setting in GUI to become compatiable in the NV5 Land Cover Script Interface.  See compare_paths_config.yml in the comment below
    """
    # First file or directory path to compare
    path1: <path>

    # Second file or directory path to compare
    path2: <path>
    """
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Create argument parser with description
    parser = argparse.ArgumentParser(description="Compare file contents between two folders")
    # Add optional --config argument to specify YAML config file path
    parser.add_argument("--config", type=str, help="Path to config file")
    # Parse command line arguments
    args = parser.parse_args()

    # If --config provided, load paths from YAML file
    if args.config:
        # Determine config file path
        config_path = Path(args.config)
        # Open config file in read mode
        with open(config_path, "r") as f:
            # Parse YAML content into Python dictionary
            config = yaml.safe_load(f)

    # Set the parameters set up in .yml and that you want to show up in GUI
        path1_value = config.get("path1")
        path2_value = config.get("path2")
        
        # Validate that paths are not None when config is provided
        if not path1_value or not path2_value:
            print("ERROR: path1 and path2 must be set in the config file.", flush=True)
            sys.exit(1)
        
        path1 = Path(path1_value)
        path2 = Path(path2_value)
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
## ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



    else:
##########################################################################################
##########################################################################################
    # No changes to normal behavior if --config not provided. Set paths directly here for typical usage.
        path1 = Path(r"W:\Tools\GUIs\Land_Cover_Script_Interface\dev\1")
        path2 = Path(r"W:\Tools\GUIs\Land_Cover_Script_Interface\dev\3")
##########################################################################################
##########################################################################################

    # Flush for real-time output in GUI
    print(f"Path 1: {path1}", flush=True)
    print(f"Path 2: {path2}", flush=True)

    #===================================================================================
    # INSERT YOUR SCRIPT PROCESS LOGIC BELOW
    #===================================================================================

    # Collect all file names from path1 directory (files only, no subdirectories)
    names1 = {p.name for p in path1.iterdir() if p.is_file()}
    # Collect all file names from path2 directory (files only, no subdirectories)
    names2 = {p.name for p in path2.iterdir() if p.is_file()}
    
    # Print file counts with immediate flush
    print(f"Count path1: {len(names1)}", flush=True)
    print(f"Count path2: {len(names2)}", flush=True)

    # Calculate differences using set operations
    missing_in_path2 = sorted(names1 - names2)  # Files in path1 but not path2
    missing_in_path1 = sorted(names2 - names1)  # Files in path2 but not path1
    common_names = sorted(names1 & names2)      # Files in both paths

    # Compare contents of common files
    different_contents = []
    for name in common_names:
        file1 = path1 / name
        file2 = path2 / name
        # Compare file contents byte-by-byte (shallow=False)
        if not filecmp.cmp(file1, file2, shallow=False):
            different_contents.append(name)

    # Report results
    if not missing_in_path2 and not missing_in_path1 and not different_contents:
        # All files match - success
        print("All files match (names and contents).", flush=True)
    else:
        # Differences found - report them
        if missing_in_path2:
            print("Missing in path2:", flush=True)
            for name in missing_in_path2:
                print(f"  {name}", flush=True)

        if missing_in_path1:
            print("Missing in path1:", flush=True)
            for name in missing_in_path1:
                print(f"  {name}", flush=True)

        if different_contents:
            print("Different contents:", flush=True)
            for name in different_contents:
                print(f"  {name}", flush=True)
        
        # Exit with non-zero code to signal failure to GUI
        sys.exit(1)
    
    #===================================================================================
    # END OF SCRIPT PROCESS LOGIC
    #===================================================================================


if __name__ == "__main__":
    main()

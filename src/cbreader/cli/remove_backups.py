"""Recursively walk a directory, find folders named backup and find cbr files in those backup folders
if a corresponding cbz file exists in the parent folder, delete the cbr file.
"""

import argparse
import os
from pathlib import Path
import shutil



def remove_backups_in_directory(directory: Path) -> None:
    """Remove CBR files in backup folders if a corresponding CBZ file exists in the parent folder.

    Args:
        directory (Path): The root directory to scan for backup folders.
    """
    print(f"Removing backup folders in: {directory}")
    for backup_folder in directory.glob("**/backups"):
        parent_folder = backup_folder.parent
        for cbr_file in backup_folder.glob("*.cbr"):
            # cbz_file = parent_folder / cbr_file.with_suffix(".cbz").name
            # if cbz_file.exists():
            #     print(f"Removing backup CBR file: {cbr_file}")
            #     cbr_file.unlink()
            cbr_file.unlink()
        for cbz_file in backup_folder.glob("*.cbz"):
            cbz_file.unlink()
        try:
            backup_folder.rmdir()
            print(f"Removed backup folder: {backup_folder}")
        except OSError:
            print(f"Could not remove non-empty backup folder: {backup_folder}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Remove backup CBR files if corresponding CBZ files exist.")
    parser.add_argument("root", type=Path, help="Root directory to scan for backup folders.")
    args = parser.parse_args()

    if not args.root.exists() or not args.root.is_dir():
        print(f"Directory not found: {args.root}")
        return

    remove_backups_in_directory(args.root)


if __name__ == "__main__":
    main()
    # for i in Path(r"C:\Users\json6\Downloads\complete").glob("**/backup"):


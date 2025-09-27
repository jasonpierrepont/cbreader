import os
from pathlib import Path

def delete_empty_folders(folder_path: str) -> None:
    # Use os.walk with topdown=False to process from bottom-up (deepest directories first)
    for root, _dirs, _files in os.walk(folder_path, topdown=False):
        # Skip hidden directories
        if os.path.basename(root).startswith('.'):
            continue

        if root == folder_path:
            # Skip the root folder itself
            continue

        current_dir = Path(root)

        # Check if the current directory is empty
        try:
            if not any(current_dir.iterdir()):
                current_dir.rmdir()
                print(f"Deleted empty folder: {current_dir}")
        except OSError:
            print(f"Failed to delete folder (may not be empty): {current_dir}")

if __name__ == "__main__":
    comicdirs = [
        # r"\\tower\Books\comics",
        r"\\tower\Books\comics\.import",
        r'C:\Users\json6\Desktop\temp_comics',
        r'C:\Users\json6\Desktop\temp_comics_organized',
        r"\\tower\Books\comics_unorganized",
        ]
    for comicdir in comicdirs:
        delete_empty_folders(comicdir)

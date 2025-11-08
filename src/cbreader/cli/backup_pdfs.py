"""If there is a pdf and a cbz, move the pdf to a backup folder."""
import shutil
from pathlib import Path

def backup_pdfs_in_directory(directory: Path, backup_dir: Path) -> None:
    """Move PDFs to a backup folder if a corresponding CBZ file exists.

    Args:
        directory (Path): The directory to scan for PDFs and CBZs.
        backup_dir (Path): The directory to move PDFs into.
    """
    for pdf_file in directory.glob("**/*.pdf"):
        cbz_file = pdf_file.with_suffix(".cbz")
        if cbz_file.exists():
            relpath = pdf_file.relative_to(directory)
            target_path = backup_dir / relpath
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(pdf_file), str(target_path))
            print(f"Moved {pdf_file} to {target_path}")

if __name__ == "__main__":
    directories_to_check = [
        Path(r"\\tower\Books\comics"),

    ]
    backup_dir = Path(r"\\tower\Books\comic_pdfs")

    for directory in directories_to_check:
        if directory.exists():
            backup_pdfs_in_directory(directory, backup_dir)
        else:
            print(f"Directory not found: {directory}")

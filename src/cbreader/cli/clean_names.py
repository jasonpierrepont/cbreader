#!/usr/bin/env python3
"""
pdf2cbz.py

Convert PDF comics to CBZ by extracting images (embedded images when present,
otherwise rendering pages) and packing them into a ZIP (.cbz) archive.

Primary strategy:
- Try to use PyMuPDF (fitz) to extract embedded images efficiently.
- If PyMuPDF isn't available, render pages to images using the builtin
  page rendering (also via PyMuPDF if available). We avoid pdf2image dependency
  to keep things simple; if PyMuPDF isn't available the script will instruct
  the user to install an appropriate package.

Usage:
  python pdf2cbz.py file.pdf
  python pdf2cbz.py /path/to/pdfs/  # converts all .pdf files in directory

Options:
  --overwrite    Overwrite existing .cbz files
  --no-backup    Do not create backups of original PDFs
  -v --verbose   Verbose logging
"""

from pathlib import Path
from typing import Optional
import argparse
import logging
import sys
import tempfile
import zipfile
import shutil
from datetime import datetime
import re





def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def find_tags(filepath:Path) -> list[str]:
    """Find tags in filename enclosed in parentheses."""
    pattern = r'\([^\(\)]*\)'
    number_pattern = r'\(\d+\)'
    alltags = re.findall(pattern, filepath.stem)
    tags = [tag for tag in alltags if not re.match(number_pattern, tag)]
    return tags




def scan_directory(directory: Path, recursive: bool = False, overwrite: bool = False,
                      create_backup: bool = True, embedded_only: bool = False,
                      ) -> set[str]:
    unique_tags = set()

    if not directory.exists() or not directory.is_dir():
        return unique_tags

    if recursive:
        cbz_files = list(directory.rglob('*.cbz'))
    else:
        cbz_files = list(directory.glob('*.cbz'))

    for cbz in cbz_files:
        tags = find_tags(cbz)
        unique_tags.update(tags)

    return unique_tags


def main() -> None:
    parser = argparse.ArgumentParser(description='Convert PDF files to CBZ archives')
    parser.add_argument('input', help='PDF file or directory containing PDFs')
    parser.add_argument('-r', '--recursive', action='store_true', help='Search directories recursively')
    parser.add_argument('--no-backup', action='store_true', help='Do not create backups')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing CBZ files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--backup-dir', help='Directory to place backups instead of default backups folder next to each file')

    args = parser.parse_args()
    _setup_logging(args.verbose)

    input_path = Path(args.input)
    if input_path.is_file():
        unique_tags = scan_directory(
            input_path.parent,
            recursive=False,
            overwrite=args.overwrite,
            create_backup=not args.no_backup,
        )
    elif input_path.is_dir():
        unique_tags = scan_directory(
            input_path,
            recursive=args.recursive,
            overwrite=args.overwrite,
            create_backup=not args.no_backup,
        )
    else:
        logging.error(f"Input path is neither a file nor a directory: {input_path}")
        sys.exit(1)

    for i in sorted(unique_tags):
        print(i)




if __name__ == '__main__':
    main()

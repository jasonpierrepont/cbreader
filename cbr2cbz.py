#!/usr/bin/env python3
"""
CBR to CBZ Converter

This script converts Comic Book Archive files from RAR format (.cbr) to ZIP format (.cbz).
It supports both individual file conversion and batch conversion of entire directories.

Features:
- Convert single CBR files to CBZ
- Batch convert all CBR files in a directory
- Preserve original file structure and metadata
- Move original CBRs to a backups folder after successful conversion
- Detect mis-labeled CBRs that are actually ZIP files and just rename to .cbz
- Command-line interface with comprehensive options
- Progress tracking for batch operations

Requirements:
- patool (for RAR extraction)
- Pillow (for image handling)
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import patoolib
except ImportError:
    print("Error: patool is required. Install with: pip install patool")
    sys.exit(1)

try:
    import importlib.util
    if importlib.util.find_spec("PIL") is None:
        raise ImportError("PIL not found")
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)


class CBRToCBZConverter:
    """Converts CBR files to CBZ format."""

    def __init__(self, create_backups: bool = True, overwrite: bool = False):
        """
        Initialize the converter.

        Args:
            create_backups: Whether to create backup copies of original CBR files
            overwrite: Whether to overwrite existing CBZ files
        """
        self.create_backups = create_backups
        self.overwrite = overwrite
        self.backup_dir = "backups"

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _is_image_file(self, filename: str) -> bool:
        """Check if a file is a supported image format."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        return Path(filename).suffix.lower() in image_extensions

    def _create_backup(self, cbr_path: Path) -> Optional[Path]:
        """Create a backup of the original CBR file."""
        if not self.create_backups:
            return None

        backup_dir = cbr_path.parent / self.backup_dir
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{cbr_path.stem}_backup_{timestamp}{cbr_path.suffix}"
        backup_path = backup_dir / backup_name

        try:
            shutil.copy2(cbr_path, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None

    def _move_original_to_backup(self, cbr_path: Path) -> Optional[Path]:
        """Move the original CBR file to the backups folder after success.

        Returns the destination path if moved successfully, otherwise None.
        """
        if not self.create_backups:
            return None

        backup_dir = cbr_path.parent / self.backup_dir
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{cbr_path.stem}_backup_{timestamp}{cbr_path.suffix}"
        dest_path = backup_dir / backup_name

        try:
            shutil.move(str(cbr_path), str(dest_path))
            self.logger.info(f"Moved original to backup: {dest_path}")
            return dest_path
        except Exception as e:
            self.logger.error(f"Failed to move original to backup: {e}")
            return None

    def _rename_to_cbz(self, cbr_path: Path) -> Tuple[bool, str]:
        """If the .cbr is actually a ZIP archive, rename it to .cbz.

        Respects the overwrite flag when a .cbz of the same name exists.

        Returns (success, message).
        """
        cbz_dest = cbr_path.with_suffix('.cbz')

        # Handle existing destination
        if cbz_dest.exists():
            if not self.overwrite:
                return False, f"CBZ already exists (use --overwrite to replace): {cbz_dest}"
            try:
                cbz_dest.unlink()
            except Exception as e:
                return False, f"Failed to remove existing CBZ before rename: {cbz_dest} ({e})"

        try:
            cbr_path.rename(cbz_dest)
            return True, f"File is a ZIP archive; renamed to: {cbz_dest}"
        except Exception as e:
            self.logger.error(f"Failed to rename CBR to CBZ: {e}")
            return False, f"Failed to rename to CBZ: {e}"

    def _extract_cbr(self, cbr_path: Path, extract_dir: Path) -> bool:
        """Extract CBR file to temporary directory.

        Tries patool first; if it fails, falls back to 7-Zip if available.
        """
        try:
            patoolib.extract_archive(str(cbr_path), outdir=str(extract_dir))
            return True
        except Exception as e:
            self.logger.warning(f"patool extraction failed for {cbr_path}: {e}")
            # Fallback to 7-Zip
            if self._extract_with_7z(cbr_path, extract_dir):
                self.logger.info("Extracted using 7-Zip fallback")
                return True
            self.logger.error(f"Failed to extract {cbr_path} with patool and 7-Zip fallback")
            return False

    def _find_7z(self) -> Optional[str]:
        """Find a 7-Zip executable on PATH or common install locations."""
        candidates = ["7z", "7za", "7zr"]
        for name in candidates:
            path = shutil.which(name)
            if path:
                return path
        # Common Windows locations
        common_paths = [
            r"C:\\Program Files\\7-Zip\\7z.exe",
            r"C:\\Program Files (x86)\\7-Zip\\7z.exe",
        ]
        for p in common_paths:
            if Path(p).exists():
                return p
        return None

    def _extract_with_7z(self, archive_path: Path, extract_dir: Path) -> bool:
        """Extract archive using 7-Zip if available."""
        sevenz = self._find_7z()
        if not sevenz:
            self.logger.debug("7-Zip not found on system PATH or common locations")
            return False
        cmd = [sevenz, "x", "-y", f"-o{str(extract_dir)}", str(archive_path)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return True
            self.logger.error(
                "7-Zip extraction failed (code %s): %s", result.returncode, (result.stderr or result.stdout)
            )
            return False
        except Exception as e:
            self.logger.error(f"Error running 7-Zip: {e}")
            return False

    def _create_cbz(self, source_dir: Path, cbz_path: Path) -> bool:
        """Create CBZ file from extracted images."""
        try:
            # Get all image files and sort them naturally
            image_files = []
            for root, _dirs, files in os.walk(source_dir):
                for file in files:
                    if self._is_image_file(file):
                        image_files.append(Path(root) / file)

            if not image_files:
                self.logger.warning(f"No image files found in {source_dir}")
                return False

            # Sort files naturally (handle numeric sequences properly)
            image_files.sort(key=lambda x: self._natural_sort_key(x.name))

            # Create CBZ archive
            with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as cbz:
                for img_path in image_files:
                    # Preserve directory structure relative to source_dir
                    arcname = img_path.relative_to(source_dir)
                    cbz.write(img_path, arcname)

            self.logger.info(f"Created CBZ with {len(image_files)} images: {cbz_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create CBZ {cbz_path}: {e}")
            return False

    def _natural_sort_key(self, text: str) -> List:
        """Generate a key for natural sorting (handles numbers in filenames)."""
        import re
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

    def convert_file(self, cbr_path: Path) -> Tuple[bool, str]:
        """
        Convert a single CBR file to CBZ.

        Args:
            cbr_path: Path to the CBR file

        Returns:
            Tuple of (success, message)
        """
        if not cbr_path.exists():
            return False, f"File not found: {cbr_path}"

        if cbr_path.suffix.lower() != '.cbr':
            return False, f"Not a CBR file: {cbr_path}"

        # If the .cbr is actually a ZIP archive, just rename to .cbz
        try:
            if zipfile.is_zipfile(cbr_path):
                return self._rename_to_cbz(cbr_path)
        except Exception as e:
            # If zipfile check itself errors, log and continue with normal flow
            self.logger.debug(f"zipfile check failed for {cbr_path}: {e}")

        cbz_path = cbr_path.with_suffix('.cbz')

        # Check if CBZ already exists
        if cbz_path.exists() and not self.overwrite:
            return False, f"CBZ already exists (use --overwrite to replace): {cbz_path}"

        self.logger.info(f"Converting: {cbr_path}")

        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Extract CBR
            if not self._extract_cbr(cbr_path, temp_path):
                return False, f"Failed to extract CBR: {cbr_path}"

            # Create CBZ
            if not self._create_cbz(temp_path, cbz_path):
                return False, f"Failed to create CBZ: {cbz_path}"

            # Move original to backups only after successful CBZ creation
            moved_path = self._move_original_to_backup(cbr_path)
            if self.create_backups and moved_path is None:
                # CBZ was created but original wasn't moved; report partial issue
                self.logger.warning("CBZ created but failed to move original to backups")

        return True, f"Successfully converted: {cbr_path} -> {cbz_path}"

    def convert_directory(self, directory: Path, recursive: bool = False) -> Tuple[int, int, List[str]]:
        """
        Convert all CBR files in a directory.

        Args:
            directory: Directory containing CBR files
            recursive: Whether to search subdirectories

        Returns:
            Tuple of (successful_conversions, failed_conversions, error_messages)
        """
        if not directory.exists() or not directory.is_dir():
            return 0, 0, [f"Directory not found: {directory}"]

        # Find all CBR files
        if recursive:
            cbr_files = list(directory.rglob("*.cbr"))
        else:
            cbr_files = list(directory.glob("*.cbr"))

        if not cbr_files:
            return 0, 0, [f"No CBR files found in: {directory}"]

        successful = 0
        failed = 0
        errors = []

        self.logger.info(f"Found {len(cbr_files)} CBR files to convert")

        for cbr_file in cbr_files:
            success, message = self.convert_file(cbr_file)
            if success:
                successful += 1
                self.logger.info(message)
            else:
                failed += 1
                errors.append(message)
                self.logger.error(message)

        return successful, failed, errors


def main() -> None:
    """Command-line interface for CBR to CBZ conversion."""
    parser = argparse.ArgumentParser(
        description="Convert CBR files to CBZ format. If a .cbr is actually a ZIP, it will be renamed to .cbz.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s file.cbr                    # Convert single file
  %(prog)s mislabeled.cbr              # If ZIP, will be renamed to mislabeled.cbz
  %(prog)s /path/to/comics/            # Convert all CBR files in directory
  %(prog)s /path/to/comics/ -r         # Convert recursively
  %(prog)s file.cbr --no-backup        # Convert without moving original to backups
  %(prog)s file.cbr --overwrite        # Overwrite existing CBZ files
        """
    )

    parser.add_argument(
        'input',
        help='CBR file or directory containing CBR files'
    )

    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Search for CBR files recursively in subdirectories'
    )

    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not move original CBR files to backups after conversion'
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing CBZ files'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize converter
    converter = CBRToCBZConverter(
        create_backups=not args.no_backup,
        overwrite=args.overwrite
    )

    input_path = Path(args.input)

    if input_path.is_file():
        # Convert single file
        success, message = converter.convert_file(input_path)
        if success:
            print(f"✓ {message}")
            sys.exit(0)
        else:
            print(f"✗ {message}")
            sys.exit(1)

    elif input_path.is_dir():
        # Convert directory
        successful, failed, errors = converter.convert_directory(input_path, args.recursive)

        print("\nConversion complete:")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")

        if errors:
            print("\nErrors:")
            for error in errors:
                print(f"  ✗ {error}")

        sys.exit(0 if failed == 0 else 1)

    else:
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()

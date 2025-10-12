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

# Try to import PyMuPDF (fitz)
HAS_FITZ = False
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except Exception:
    HAS_FITZ = False


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def _create_backup(path: Path, backup_dir: Optional[Path] = None) -> Optional[Path]:
    """Create a timestamped backup of `path` in `backup_dir`.

    If `backup_dir` is None, a `backups` folder next to the original file is used.
    Returns the Path to the backup file on success, or None on failure.
    """
    try:
        if backup_dir:
            backup_dir_path = Path(backup_dir)
        else:
            backup_dir_path = path.parent / "backups"
        backup_dir_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.stem}_backup_{timestamp}{path.suffix}"
        backup_path = backup_dir_path / backup_name
        shutil.copy2(path, backup_path)
        logging.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logging.warning(f"Failed to create backup for {path}: {e}")
        return None


def extract_images_with_fitz(pdf_path: Path, out_dir: Path) -> list:
    """Extract embedded images from PDF using PyMuPDF.
    Returns list of saved image Paths in extraction order.
    If no embedded images are found, this will return an empty list.
    """
    saved = []
    doc = fitz.open(str(pdf_path))
    img_index = 0
    for pageno in range(len(doc)):
        page = doc[pageno]
        images = page.get_images(full=True)
        if images:
            for img in images:
                xref = img[0]
                try:
                    # Try to extract the raw image bytes (preserve original format)
                    try:
                        img_dict = doc.extract_image(xref)
                        img_bytes = img_dict.get("image")
                        ext = img_dict.get("ext", "png")
                        out_path = out_dir / f"img_p{pageno+1:04d}_{img_index:04d}.{ext}"
                        with open(out_path, "wb") as fh:
                            fh.write(img_bytes)
                        saved.append(out_path)
                        img_index += 1
                        continue
                    except Exception:
                        # Fallback to Pixmap saving if extract_image isn't available
                        pass

                    pix = fitz.Pixmap(doc, xref)
                    # Ensure RGB for saving
                    if pix.n < 4:  # GRAY or RGB
                        ext = "png"
                        out_path = out_dir / f"img_p{pageno+1:04d}_{img_index:04d}.{ext}"
                        pix.save(str(out_path))
                    else:
                        # CMYK: convert to RGB first
                        pix2 = fitz.Pixmap(fitz.csRGB, pix)
                        ext = "png"
                        out_path = out_dir / f"img_p{pageno+1:04d}_{img_index:04d}.{ext}"
                        pix2.save(str(out_path))
                        pix2 = None
                    pix = None
                    saved.append(out_path)
                    img_index += 1
                except Exception as e:
                    logging.debug(f"Failed to extract image xref={xref} on page {pageno+1}: {e}")
    doc.close()
    return saved


def render_pages_with_fitz(pdf_path: Path, out_dir: Path, dpi: int = 150) -> list:
    """Render each PDF page to an image using PyMuPDF.
    Returns list of saved image Paths in page order.
    """
    saved = []
    doc = fitz.open(str(pdf_path))
    for pageno in range(len(doc)):
        page = doc[pageno]
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat)
        # Save rendered page as JPEG to reduce size compared to PNG
        out_path = out_dir / f"p{pageno+1:04d}.jpg"
        try:
            # Try to save directly as JPEG
            pix.save(str(out_path))
        except Exception:
            # Fallback: save as PNG then convert with Pillow if available
            png_path = out_dir / f"p{pageno+1:04d}.png"
            pix.save(str(png_path))
            try:
                from PIL import Image
                im = Image.open(png_path)
                im.convert('RGB').save(out_path, format='JPEG', quality=85)
                png_path.unlink()
            except Exception:
                # If Pillow not available, keep the PNG
                out_path = png_path
        saved.append(out_path)
        pix = None
    doc.close()
    return saved


def create_cbz_from_images(image_paths: list, cbz_path: Path, source_dir: Path) -> bool:
    try:
        # Ensure images are sorted naturally by name
        image_paths_sorted = sorted(image_paths, key=lambda p: p.name)
        with zipfile.ZipFile(cbz_path, 'w') as zf:
            for img in image_paths_sorted:
                arcname = img.relative_to(source_dir)
                # If the image is already in a compressed format, store it without extra compression
                if img.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
                    zf.write(img, arcname, compress_type=zipfile.ZIP_STORED)
                else:
                    # Use deflated compression for other formats
                    zf.write(img, arcname, compress_type=zipfile.ZIP_DEFLATED)
        logging.info(f"Created CBZ: {cbz_path} with {len(image_paths_sorted)} images")
        return True
    except Exception as e:
        logging.error(f"Failed to create CBZ {cbz_path}: {e}")
        return False


def convert_pdf_to_cbz(pdf_path: Path, overwrite: bool = False, create_backup: bool = True,
                       embedded_only: bool = False,
                       use_pdf_dpi: bool = False,
                       backup_dir: Optional[Path] = None) -> tuple:
    """Convert a single PDF to CBZ. Returns (success, message)."""
    if not pdf_path.exists():
        return False, f"File not found: {pdf_path}"
    if pdf_path.suffix.lower() != '.pdf':
        return False, f"Not a PDF file: {pdf_path}"

    cbz_path = pdf_path.with_suffix('.cbz')
    if cbz_path.exists() and not overwrite:
        return False, f"CBZ already exists (use --overwrite): {cbz_path}"

    if create_backup:
        _create_backup(pdf_path, backup_dir=backup_dir)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        # Render each PDF page to an image (one image per page)
        images = []
        if HAS_FITZ:
            render_dpi = 72 if use_pdf_dpi else 200
            images = render_pages_with_fitz(pdf_path, tmp, dpi=render_dpi)
        else:
            return False, ("PyMuPDF (fitz) is required to render PDF pages. "
                           "Install it with: pip install PyMuPDF")

        if not images:
            return False, f"No images produced for PDF: {pdf_path}"

        success = create_cbz_from_images(images, cbz_path, tmp)
        if not success:
            return False, f"Failed to create CBZ: {cbz_path}"

    return True, f"Converted PDF to CBZ: {pdf_path} -> {cbz_path}"


def convert_directory(directory: Path, recursive: bool = False, overwrite: bool = False,
                      create_backup: bool = True, embedded_only: bool = False,
                      use_pdf_dpi: bool = False, backup_dir: Optional[Path] = None) -> tuple:
    if not directory.exists() or not directory.is_dir():
        return 0, 0, [f"Directory not found: {directory}"]

    if recursive:
        pdf_files = list(directory.rglob('*.pdf'))
    else:
        pdf_files = list(directory.glob('*.pdf'))

    if not pdf_files:
        return 0, 0, [f"No PDF files found in: {directory}"]

    successful = 0
    failed = 0
    errors = []

    for pdf in pdf_files:
        ok, msg = convert_pdf_to_cbz(
            pdf,
            overwrite=overwrite,
            create_backup=create_backup,
            embedded_only=embedded_only,
            use_pdf_dpi=use_pdf_dpi,
            backup_dir=backup_dir,
        )
        if ok:
            successful += 1
            logging.info(msg)
        else:
            failed += 1
            errors.append(msg)
            logging.error(msg)

    return successful, failed, errors


def main() -> None:
    parser = argparse.ArgumentParser(description='Convert PDF files to CBZ archives')
    parser.add_argument('input', help='PDF file or directory containing PDFs')
    parser.add_argument('-r', '--recursive', action='store_true', help='Search directories recursively')
    parser.add_argument('--no-backup', action='store_true', help='Do not create backups')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing CBZ files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--embedded-only', action='store_true', help='Only accept PDFs that contain embedded images; skip rendering')
    parser.add_argument('--use-pdf-dpi', action='store_true', help='Render pages at the PDF nominal DPI (72) instead of a higher default')
    parser.add_argument('--backup-dir', help='Directory to place backups instead of default backups folder next to each file')

    args = parser.parse_args()
    _setup_logging(args.verbose)

    input_path = Path(args.input)
    if input_path.is_file():
        backup_dir_arg = Path(args.backup_dir) if args.backup_dir else None
        ok, msg = convert_pdf_to_cbz(
            input_path,
            overwrite=args.overwrite,
            create_backup=not args.no_backup,
            embedded_only=args.embedded_only,
            use_pdf_dpi=args.use_pdf_dpi,
            backup_dir=backup_dir_arg,
        )
        if ok:
            print(f"✓ {msg}")
            sys.exit(0)
        else:
            print(f"✗ {msg}")
            sys.exit(1)
    elif input_path.is_dir():
        backup_dir_arg = Path(args.backup_dir) if args.backup_dir else None
        successful, failed, errors = convert_directory(
            input_path,
            recursive=args.recursive,
            overwrite=args.overwrite,
            create_backup=not args.no_backup,
            embedded_only=args.embedded_only,
            use_pdf_dpi=args.use_pdf_dpi,
            backup_dir=backup_dir_arg,
        )

        print(f"\nConversion complete:\n  Successful: {successful}\n  Failed: {failed}")
        if errors:
            print("\nErrors:")
            for e in errors:
                print(f"  ✗ {e}")
        sys.exit(0 if failed == 0 else 1)
    else:
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)


if __name__ == '__main__':
    main()

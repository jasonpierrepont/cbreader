"""Clean up comic files.

Search through comics for missing metadatafiles
Find any cbr files and convert to cbz
Find any PDF files and convert to cbz.
"""
import argparse
import zipfile
from pathlib import Path
from typing import Optional

import patoolib
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from cbreader.db_models import Base, Comic

def load_comics_from_db(session: Session) -> list[Comic]:
    """Load all comics from the database."""
    query = select(Comic)
    return list(session.execute(query).scalars().all())


def find_missing_meta(session: Session, root:Path) -> None:
    """Find comic files missing metadata files."""
    total_checked = 0
    # load files from database that have metadata
    metadata_results = list(session.execute(select(Comic).where(Comic.has_metadata)).scalars().all())
    comics_with_metadata = {Path(str(comic.file_path)) for comic in metadata_results}

    # Placeholder for actual implementation
    print("Searching for comic files missing metadata...")
    for file in root.rglob('**/*'):
        if file in comics_with_metadata:
            # skip files already known to have metadata
            continue
        if file.suffix.lower() == '.cbz':
            # Look inside the cbz (zip) file for a ComicInfo.xml file
            with zipfile.ZipFile(file, 'r') as zip_ref:
                if 'ComicInfo.xml' not in zip_ref.namelist():
                    print(f"Missing ComicInfo.xml in: {file}")
                total_checked += 1
        if file.suffix.lower() == '.cbr':
            # patoolib.list_archive(str(file))
            print(f"RAR File: {file}")

    print(f"Total comic files checked: {total_checked}")


def load_library(session: Session, root_path: Path, skip_zip_scan_if_known: bool = False) -> Session:
    """Load or update the comic library using the provided session.

    Commits on success; rolls back on error and re-raises.
    Returns the same session for convenience.
    """
    try:
        # Optional: preload cache of known files with metadata to avoid per-file DB lookups and zip scans
        cache: set[str] = set()
        if skip_zip_scan_if_known:
            rows = list(session.execute(select(Comic).where(Comic.has_metadata)).scalars().all())
            prefix = str(root_path)
            cache = {str(comic.file_path) for comic in rows if str(comic.file_path).startswith(prefix)}
            print(f"Loaded {len(cache)} known comics with metadata from DB cache.")

        # Scan the directory for comic files and update the database
        for file in root_path.rglob('**/*'):
            if file.suffix.lower() in ['.cbz', '.cbr', '.pdf']:
                file_type = file.suffix.lstrip('.').lower()
                # If cached as known-good metadata, skip scanning and DB hit entirely
                if file_type == 'cbz' and skip_zip_scan_if_known and str(file) in cache:
                    continue

                # Fetch existing record if any (only for files we will touch)
                comic = session.execute(select(Comic).where(Comic.file_path == str(file))).scalars().first()

                has_metadata = False
                if file_type == 'cbz':
                    try:
                        with zipfile.ZipFile(file, 'r') as zip_ref:
                            has_metadata = 'ComicInfo.xml' in zip_ref.namelist()
                    except zipfile.BadZipFile:
                        print(f"Bad zip file: {file}")
                        has_metadata = False

                if not comic:
                    comic = Comic(file_path=str(file), has_metadata=has_metadata, file_type=file_type)
                    session.add(comic)
                else:
                    comic.has_metadata = has_metadata
                    comic.file_type = file_type
                    session.add(comic)
        session.commit()
        return session
    except Exception:
        session.rollback()
        raise

def remove_missing_comics(session: Session, root_path: Path) -> None:
    """Remove comics from the database if their files no longer exist.

    Commits on success; rolls back on error.
    """
    try:
        # Filter by path prefix using startswith in Python after fetching relevant rows.
        # For large datasets, consider normalizing path and indexing for DB-side filtering.
        comics = list(session.execute(select(Comic)).scalars().all())
        comics = [c for c in comics if str(c.file_path).startswith(str(root_path))]
        removed = 0
        for comic in comics:
            if not Path(str(comic.file_path)).exists():
                session.delete(comic)
                removed += 1
        session.commit()
        print(f"Removed {removed} comics that no longer exist.")
    except Exception:
        session.rollback()
        raise

def list_missing_metadata(session: Session, root_path: Optional[Path]=None) -> None:
    results = list(session.execute(select(Comic)).scalars().all())
    for comic in results:
        if (not comic.has_metadata) and (not root_path or str(comic.file_path).startswith(str(root_path))):
            print(comic.file_path)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find comic files missing metadata.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    load = subparsers.add_parser("load", help="Load or create the comic library database.")
    load.add_argument("root", type=Path, help="Root directory to scan for comics.")
    load.add_argument(
        "--skip-known",
        action="store_true",
        help=(
            "If a comic already exists in the database with has_metadata=True, "
            "skip scanning the CBZ contents and trust the DB value."
        ),
    )
    load.set_defaults(func=load_library)

    find_missing = subparsers.add_parser("find", help="Find comic files missing metadata.")
    find_missing.add_argument("root", type=Path, help="Root directory to scan for comics.")
    find_missing.set_defaults(func=find_missing_meta)

    list_parser = subparsers.add_parser("list", help="List all comics in the database with missing metadata.")
    list_parser.add_argument("root", type=Path, default=None, help="Root directory to scan for comics.")

    return parser.parse_args()


def main():
    args = parse_args()
    db_path = Path("comics_metadata.db")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        print(args)
        if args.command == "load":
            load_library(session, args.root, skip_zip_scan_if_known=getattr(args, "skip_known", False))
            remove_missing_comics(session, args.root)
        elif args.command == "find":
            find_missing_meta(session, args.root)
        elif args.command == "list":
            list_missing_metadata(session, args.root)
    finally:
        session.close()


if __name__ == "__main__":
    main()
    # find_missing_meta(Path(r"\\TOWER.local\Books\comics\Marvel\The Spectacular Spider-Man (1976)"))

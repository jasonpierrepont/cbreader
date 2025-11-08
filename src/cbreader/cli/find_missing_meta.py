"""Clean up comic files.

Search through comics for missing metadatafiles
Find any cbr files and convert to cbz
Find any PDF files and convert to cbz.
"""
from pathlib import Path
from typing import Optional
import zipfile
from sqlmodel import SQLModel, Field, create_engine, Session, select, func
import argparse
import patoolib
import datetime

class Comic(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    file_path: str = Field(index=True, unique=True)
    has_metadata: bool = Field(default=False)
    file_type: str = Field(index=True)  # e.g., 'cbz', 'cbr', 'pdf'
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(
            default_factory=datetime.datetime.now,
            sa_column_kwargs={"onupdate": func.now()} # Use func.now() for database-level update
        )
    def change_path(self, new_path: str|Path) -> None:
        old_ext = Path(self.file_path).suffix
        new_ext = Path(new_path).suffix
        self.file_path = str(new_path)
        if old_ext != new_ext:
            self.file_type = new_ext.lstrip('.').lower()


def load_comics_from_db(session: Session) -> list[Comic]:
    """Load all comics from the database."""
    query = select(Comic)
    return session.exec(query).all()


def find_missing_meta(session: Session, root:Path) -> None:
    """Find comic files missing metadata files."""
    total_checked = 0
    # load files from database that have metadata
    metadata_results = session.exec(select(Comic).where(Comic.has_metadata == True)).all()
    comics_with_metadata = {Path(comic.file_path) for comic in metadata_results}

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
            rows = session.exec(select(Comic.file_path).where(Comic.has_metadata)).all()
            prefix = str(root_path)
            cache = {str(fp) for fp in rows if isinstance(fp, (str,)) and str(fp).startswith(prefix)}
            print(f"Loaded {len(cache)} known comics with metadata from DB cache.")

        # Scan the directory for comic files and update the database
        for file in root_path.rglob('**/*'):
            if file.suffix.lower() in ['.cbz', '.cbr', '.pdf']:
                file_type = file.suffix.lstrip('.').lower()
                # If cached as known-good metadata, skip scanning and DB hit entirely
                if file_type == 'cbz' and skip_zip_scan_if_known and str(file) in cache:
                    continue

                # Fetch existing record if any (only for files we will touch)
                comic = session.exec(select(Comic).where(Comic.file_path == str(file))).first()

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
        comics = session.exec(select(Comic)).all()
        comics = [c for c in comics if c.file_path.startswith(str(root_path))]
        removed = 0
        for comic in comics:
            if not Path(comic.file_path).exists():
                session.delete(comic)
                removed += 1
        session.commit()
        print(f"Removed {removed} comics that no longer exist.")
    except Exception:
        session.rollback()
        raise

def list_missing_metadata(session: Session, root_path: Optional[Path]=None) -> None:
    results = session.exec(select(Comic)).all()
    for comic in results:
        if (not comic.has_metadata) and (not root_path or comic.file_path.startswith(str(root_path))):
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
    SQLModel.metadata.create_all(engine)
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

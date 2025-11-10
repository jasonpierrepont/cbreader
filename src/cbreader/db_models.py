import datetime
from pathlib import Path

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Comic(Base):
    __tablename__ = "comic"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, index=True, unique=True, nullable=False)
    has_metadata = Column(Boolean, default=False, nullable=False)
    file_type = Column(String, index=True, nullable=False)  # e.g., 'cbz', 'cbr', 'pdf'
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=func.now(), nullable=False)

    def change_path(self, new_path: str|Path) -> None:
        old_ext = Path(str(self.file_path)).suffix
        new_ext = Path(new_path).suffix
        self.file_path = str(new_path)
        if old_ext != new_ext:
            self.file_type = new_ext.lstrip('.').lower()

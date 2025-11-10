from __future__ import annotations
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread, QSettings
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QLineEdit, QCheckBox, QTextEdit, QMessageBox, QGroupBox
)

# Import app logic
from cbreader.cli.find_missing_meta import (
    load_library, find_missing_meta, remove_missing_comics, list_missing_metadata
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from cbreader.db_models import Base
from cbreader.cli.cbr2cbz import CBRToCBZConverter


class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(str)
    output = Signal(str)


class Worker(QThread):
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            # Capture stdout/stderr and forward to signals
            import sys as _sys
            class _Stream:
                def __init__(self, emit):
                    self._emit = emit
                def write(self, s):
                    s = str(s)
                    if s.strip():
                        self._emit(s.rstrip())
                def flush(self):
                    pass

            _orig_out, _orig_err = _sys.stdout, _sys.stderr
            _sys.stdout = _Stream(self.signals.output.emit)
            _sys.stderr = _Stream(lambda s: self.signals.error.emit(s))
            try:
                # Call the function
                self.func(*self.args, **self.kwargs)
            finally:
                _sys.stdout, _sys.stderr = _orig_out, _orig_err
            # If functions want to return info, we could emit it here
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))


class MetaGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Comics Metadata Tools")
        self.resize(800, 600)

        self.db_session: Session | None = None
        # Keep strong references to workers to prevent premature GC
        self._workers: list[Worker] = []
        # Settings to remember last chosen paths and options
        self.settings = QSettings("cbreader", "meta_tools")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Root path chooser
        path_group = QGroupBox("Library Root")
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._choose_root)
        path_layout.addWidget(QLabel("Root:"))
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(browse_btn)
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        # Load last remembered root path
        last_root_obj = self.settings.value("last_root_dir", "")
        last_root = str(last_root_obj) if last_root_obj is not None else ""
        if last_root:
            self.path_edit.setText(last_root)

        # Options
        opts_group = QGroupBox("Options")
        opts_layout = QHBoxLayout()
        self.skip_zip_scan_cb = QCheckBox("Skip CBZ scan if DB says has metadata")
        self.skip_zip_scan_cb.setChecked(True)
        opts_layout.addWidget(self.skip_zip_scan_cb)
        opts_group.setLayout(opts_layout)
        layout.addWidget(opts_group)

        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load / Update Library")
        self.load_btn.clicked.connect(self._on_load)
        self.remove_missing_btn = QPushButton("Remove Missing Files")
        self.remove_missing_btn.clicked.connect(self._on_remove_missing)
        self.find_btn = QPushButton("Find Missing Metadata (scan fs)")
        self.find_btn.clicked.connect(self._on_find)
        self.list_btn = QPushButton("List Missing Metadata (from DB)")
        self.list_btn.clicked.connect(self._on_list)
        actions_layout.addWidget(self.load_btn)
        actions_layout.addWidget(self.remove_missing_btn)
        actions_layout.addWidget(self.find_btn)
        actions_layout.addWidget(self.list_btn)
        # CBR->CBZ controls
        self.recursive_cb = QCheckBox("Recursive")
        self.convert_btn = QPushButton("Convert CBR → CBZ")
        self.convert_btn.clicked.connect(self._on_convert_cbr)
        actions_layout.addWidget(self.recursive_cb)
        actions_layout.addWidget(self.convert_btn)
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Output log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)

    def _append_log(self, text: str):
        self.log.append(text)

    def _choose_root(self):
        # Prefer current text as starting directory, else last remembered, else CWD
        current_text = self.path_edit.text().strip()
        last_saved = self.settings.value("last_root_dir", str(Path.cwd()))
        start_dir = current_text or str(last_saved) if last_saved is not None else str(Path.cwd())
        directory = QFileDialog.getExistingDirectory(self, "Choose Comics Root", str(start_dir))
        if directory:
            self.path_edit.setText(directory)
            # Remember selection
            self.settings.setValue("last_root_dir", directory)

    def _get_root(self) -> Path | None:
        p = self.path_edit.text().strip()
        if not p:
            QMessageBox.warning(self, "Missing Root", "Please choose a root directory.")
            return None
        return Path(p)

    def _run_worker(self, func, *args, **kwargs):
        worker = Worker(func, *args, **kwargs)
        self._workers.append(worker)
        worker.signals.output.connect(self._append_log)
        worker.signals.error.connect(lambda e: self._append_log(f"Error: {e}"))
        # Announce completion to the log when the task reports finished
        worker.signals.finished.connect(lambda: self._append_log("Done."))

        def _cleanup():
            # Remove reference and delete the thread safely AFTER the thread actually finished
            try:
                self._workers.remove(worker)
            except ValueError:
                pass
            worker.deleteLater()

        # Only perform cleanup when the QThread itself signals finished
        worker.finished.connect(_cleanup)
        worker.start()

    # Button handlers
    def _on_load(self):
        root = self._get_root()
        if not root:
            return
        skip = self.skip_zip_scan_cb.isChecked()
        # Initialize engine/session here to mirror CLI behavior
        self._append_log("Loading/updating library…")
        self._run_worker(self._load_wrapper, root, skip)

    def _load_wrapper(self, root: Path, skip: bool):
        db_path = Path("comics_metadata.db")
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        session = Session(engine)
        try:
            load_library(session, root, skip_zip_scan_if_known=skip)
        finally:
            session.close()

    def _on_remove_missing(self):
        root = self._get_root()
        if not root:
            return
        self._append_log("Removing missing files from DB…")
        self._run_worker(self._remove_missing_wrapper, root)

    def _remove_missing_wrapper(self, root: Path):
        db_path = Path("comics_metadata.db")
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        session = Session(engine)
        try:
            remove_missing_comics(session, root)
        finally:
            session.close()

    def _on_find(self):
        root = self._get_root()
        if not root:
            return
        self._append_log("Scanning filesystem for missing metadata…")
        self._run_worker(self._find_wrapper, root)

    def _find_wrapper(self, root: Path):
        db_path = Path("comics_metadata.db")
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        session = Session(engine)
        try:
            find_missing_meta(session, root)
        finally:
            session.close()

    def _on_list(self):
        root = self._get_root()
        # root can be None; we treat that as no filter
        self._append_log("Listing missing metadata from DB…")
        self._run_worker(self._list_wrapper, root)

    def _list_wrapper(self, root: Path | None):
        db_path = Path("comics_metadata.db")
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        session = Session(engine)
        try:
            list_missing_metadata(session, root)
        finally:
            session.close()

    def _on_convert_cbr(self):
        root = self._get_root()
        if not root:
            return
        recursive = self.recursive_cb.isChecked()
        self._append_log("Converting CBR files to CBZ…")
        self._run_worker(self._convert_cbr_wrapper, root, recursive)

    def _convert_cbr_wrapper(self, root: Path, recursive: bool):
        # Run conversion using the existing converter, reporting per-file
        import logging as _logging
        converter = CBRToCBZConverter(create_backups=True, overwrite=False)
        # Reduce chatter from internal logger; we'll print our own status lines
        try:
            converter.logger.setLevel(_logging.ERROR)
        except Exception:
            pass

        root = Path(root)
        files = list(root.rglob("*.cbr")) if recursive else list(root.glob("*.cbr"))
        total = len(files)
        ok = 0
        fail = 0
        for idx, fp in enumerate(files, start=1):
            success, message = converter.convert_file(fp)
            if success:
                ok += 1
                print(f"[{idx}/{total}] OK  - {message}")
            else:
                fail += 1
                print(f"[{idx}/{total}] FAIL - {message}")

        print(f"Summary: total={total}, successful={ok}, failed={fail}")

    def closeEvent(self, event):
        # Ensure all background workers have finished before closing
        if getattr(self, "_workers", None):
            self._append_log("Waiting for background tasks to finish…")
            for w in list(self._workers):
                try:
                    w.wait()
                except Exception:
                    pass
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MetaGUI()
    w.show()
    sys.exit(app.exec())

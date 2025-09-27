import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import patoolib
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QCloseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

class ImageExtractor(QThread):
    """Thread to extract images from comic book archives."""

    progress_updated = Signal(int, str)
    extraction_finished = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.file_path = file_path
        self.temp_dir: Optional[str] = None

    def run(self) -> None:
        try:
            self.temp_dir = tempfile.mkdtemp()
            self.progress_updated.emit(10, "Creating temporary directory...")

            # Determine file type and extract
            file_ext = Path(self.file_path).suffix.lower()

            if file_ext == '.cbz':
                self.extract_zip()
            elif file_ext == '.cbr':
                self.extract_rar()
            else:
                self.error_occurred.emit(f"Unsupported file format: {file_ext}")
                return

            # Find image files
            self.progress_updated.emit(80, "Scanning for images...")
            image_files = self.find_image_files()

            self.progress_updated.emit(100, "Extraction complete!")
            self.extraction_finished.emit(image_files)

        except Exception as e:
            self.error_occurred.emit(f"Error extracting archive: {str(e)}")

    def extract_zip(self) -> None:
        """Extract CBZ (ZIP) file."""
        self.progress_updated.emit(30, "Extracting CBZ file...")
        with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)

    def extract_rar(self) -> None:
        """Extract CBR (RAR) file using patool, with fallback to ZIP for ZIP-based CBR files."""
        self.progress_updated.emit(30, "Extracting CBR file...")
        try:
            # First try to extract as a RAR file
            patoolib.extract_archive(self.file_path, outdir=self.temp_dir)
        except Exception as rar_error:
            # If RAR extraction fails, try ZIP extraction (for ZIP-based CBR files)
            self.progress_updated.emit(40, "Trying ZIP extraction for CBR file...")
            try:
                with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
                    zip_ref.extractall(self.temp_dir)
            except Exception as zip_error:
                # If both fail, raise a combined error message
                raise Exception(
                    f"Failed to extract CBR file. RAR error: {str(rar_error)}, ZIP error: {str(zip_error)}"
                ) from rar_error

    def find_image_files(self) -> List[str]:
        """Find all image files in the extracted directory."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files: List[str] = []

        if self.temp_dir and os.path.exists(self.temp_dir):
            for root, _dirs, files in os.walk(self.temp_dir):
                for file in files:
                    if Path(file).suffix.lower() in image_extensions:
                        image_files.append(os.path.join(root, file))

        # Sort files naturally
        image_files.sort(key=lambda x: Path(x).name.lower())
        return image_files

class PageWidget(QFrame):
    """Widget to display a single comic page with selection checkbox."""

    def __init__(self, image_path: str, page_number: int) -> None:
        super().__init__()
        self.image_path = image_path
        self.page_number = page_number
        self.selected = True

        self.setFrameStyle(QFrame.Shape.Box)
        self.setMinimumSize(150, 200)
        self.setMaximumSize(200, 300)

        layout = QVBoxLayout()

        # Checkbox for selection
        self.checkbox = QCheckBox(f"Page {page_number}")
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self.on_selection_changed)
        layout.addWidget(self.checkbox)

        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)
        self.image_label.setMinimumSize(140, 180)

        # Load and display thumbnail
        self.load_thumbnail()

        layout.addWidget(self.image_label)
        self.setLayout(layout)

    def load_thumbnail(self) -> None:
        """Load and display a thumbnail of the image."""
        try:
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                # Scale to fit while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(140, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("Failed to load image")
        except Exception as e:
            self.image_label.setText(f"Error: {str(e)}")

    def on_selection_changed(self, state: int) -> None:
        """Handle checkbox state change."""
        self.selected = state == 2  # Qt.CheckState.Checked has value 2
        # Change appearance based on selection
        if self.selected:
            self.setStyleSheet("PageWidget { background-color: white; }")
        else:
            self.setStyleSheet("PageWidget { background-color: #ffcccc; }")

    def is_selected(self) -> bool:
        """Return whether this page is selected."""
        return self.selected

class ComicBookReader(QMainWindow):
    """Main comic book reader application."""

    def __init__(self) -> None:
        super().__init__()
        self.current_file: Optional[str] = None
        self.temp_dir: Optional[str] = None
        self.image_files: List[str] = []
        self.page_widgets: List[PageWidget] = []

        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Comic Book Reader - CBR/CBZ Editor")
        self.setGeometry(100, 100, 1200, 800)

        # Create menu bar
        self.create_menu_bar()

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)

        # Create toolbar
        toolbar_layout = QHBoxLayout()

        self.open_button = QPushButton("Open CBR/CBZ File")
        self.open_button.clicked.connect(self.open_file)
        toolbar_layout.addWidget(self.open_button)

        # Navigation buttons
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self.open_previous_file)
        self.prev_button.setEnabled(False)
        toolbar_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self.open_next_file)
        self.next_button.setEnabled(False)
        toolbar_layout.addWidget(self.next_button)

        # Add some spacing
        toolbar_layout.addSpacing(20)

        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all_pages)
        self.select_all_button.setEnabled(False)
        toolbar_layout.addWidget(self.select_all_button)

        self.select_none_button = QPushButton("Select None")
        self.select_none_button.clicked.connect(self.select_no_pages)
        self.select_none_button.setEnabled(False)
        toolbar_layout.addWidget(self.select_none_button)

        self.save_button = QPushButton("Save In Place")
        self.save_button.clicked.connect(self.save_modified_archive)
        self.save_button.setEnabled(False)
        toolbar_layout.addWidget(self.save_button)

        self.save_as_button = QPushButton("Save As...")
        self.save_as_button.clicked.connect(self.save_as_modified_archive)
        self.save_as_button.setEnabled(False)
        toolbar_layout.addWidget(self.save_as_button)

        self.revert_button = QPushButton("Revert from Backup")
        self.revert_button.clicked.connect(self.revert_from_backup)
        self.revert_button.setEnabled(False)
        self.revert_button.setVisible(False)
        toolbar_layout.addWidget(self.revert_button)

        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Open a CBR or CBZ file to get started.")
        main_layout.addWidget(self.status_label)

        # Scroll area for pages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Container widget for pages
        self.pages_container = QWidget()
        self.pages_layout = QGridLayout(self.pages_container)
        self.scroll_area.setWidget(self.pages_container)

        main_layout.addWidget(self.scroll_area)

        # Info panel
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(100)
        self.info_text.setReadOnly(True)
        main_layout.addWidget(self.info_text)

    def create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        open_action = QAction('Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        prev_action = QAction('Previous File', self)
        prev_action.setShortcut('Ctrl+Left')
        prev_action.triggered.connect(self.open_previous_file)
        file_menu.addAction(prev_action)

        next_action = QAction('Next File', self)
        next_action.setShortcut('Ctrl+Right')
        next_action.triggered.connect(self.open_next_file)
        file_menu.addAction(next_action)

        file_menu.addSeparator()

        save_action = QAction('Save In Place', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_modified_archive)
        file_menu.addAction(save_action)

        save_as_action = QAction('Save As...', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_as_modified_archive)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu('Help')

        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def open_file(self) -> None:
        """Open a CBR or CBZ file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Comic Book Archive",
            "",
            "Comic Book Files (*.cbr *.cbz);;All Files (*)"
        )

        if file_path:
            self.current_file = file_path
            self.extract_images(file_path)

    def extract_images(self, file_path: str) -> None:
        """Extract images from the comic book archive."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Show which file is being loaded
        filename = os.path.basename(file_path)
        self.status_label.setText(f"Loading {filename}...")

        # Clean up previous temp directory
        self.cleanup_temp_dir()

        # Create and start extraction thread
        self.extractor = ImageExtractor(file_path)
        self.extractor.progress_updated.connect(self.update_progress)
        self.extractor.extraction_finished.connect(self.on_extraction_finished)
        self.extractor.error_occurred.connect(self.on_extraction_error)
        self.extractor.start()

    def update_progress(self, value: int, message: str) -> None:
        """Update progress bar and status."""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def on_extraction_finished(self, image_files: List[str]) -> None:
        """Handle successful extraction."""
        self.progress_bar.setVisible(False)
        self.image_files = image_files
        self.temp_dir = self.extractor.temp_dir

        # Reset navigation button text
        self.prev_button.setText("◀ Previous")
        self.next_button.setText("Next ▶")

        if not image_files:
            QMessageBox.warning(self, "Warning", "No image files found in the archive.")
            # Still update navigation buttons even if no images found
            self.update_navigation_buttons()
            return

        self.load_pages()
        self.update_info_panel()
        self.update_revert_button()
        self.update_navigation_buttons()

        # Enable buttons
        self.select_all_button.setEnabled(True)
        self.select_none_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.save_as_button.setEnabled(True)

        self.status_label.setText(f"Loaded {len(image_files)} pages. Select pages to keep, then save.")

    def on_extraction_error(self, error_message: str) -> None:
        """Handle extraction error."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error occurred during extraction.")

        # Reset navigation button text and state
        self.prev_button.setText("◀ Previous")
        self.next_button.setText("Next ▶")
        self.update_navigation_buttons()

        # Re-enable other buttons
        self.select_all_button.setEnabled(bool(self.page_widgets))
        self.select_none_button.setEnabled(bool(self.page_widgets))
        self.save_button.setEnabled(bool(self.page_widgets))
        self.save_as_button.setEnabled(bool(self.page_widgets))

        QMessageBox.critical(self, "Extraction Error", error_message)

    def load_pages(self) -> None:
        """Load and display page thumbnails."""
        # Clear existing pages
        for widget in self.page_widgets:
            widget.deleteLater()
        self.page_widgets.clear()

        # Create page widgets
        columns = 5  # Number of columns in grid
        for i, image_path in enumerate(self.image_files):
            page_widget = PageWidget(image_path, i + 1)
            self.page_widgets.append(page_widget)

            row = i // columns
            col = i % columns
            self.pages_layout.addWidget(page_widget, row, col)

    def select_all_pages(self) -> None:
        """Select all pages."""
        for widget in self.page_widgets:
            widget.checkbox.setChecked(True)

    def select_no_pages(self) -> None:
        """Deselect all pages."""
        for widget in self.page_widgets:
            widget.checkbox.setChecked(False)

    def update_info_panel(self) -> None:
        """Update the information panel."""
        if not self.image_files or not self.current_file:
            return

        total_pages = len(self.image_files)
        selected_pages = sum(1 for widget in self.page_widgets if widget.is_selected())

        # Determine file format and archive capabilities
        original_ext = Path(self.current_file).suffix.lower()
        format_name = "CBR" if original_ext == '.cbr' else "CBZ"

        if original_ext == '.cbr':
            if self.is_rar_available():
                format_detail = f"{format_name} (RAR-based creation available)"
            else:
                format_detail = f"{format_name} (ZIP-based only - no RAR tool)"
        else:
            format_detail = f"{format_name} (ZIP-based)"

        info_text = f"""
Current File: {os.path.basename(self.current_file)}
Format: {format_detail}
Total Pages: {total_pages}
Selected Pages: {selected_pages}
Pages to Remove: {total_pages - selected_pages}

Instructions:
1. Uncheck pages you want to remove
2. Click 'Save In Place' to save in original format
3. Click 'Save As...' to save as CBZ in a new location
"""
        self.info_text.setText(info_text)

    def save_modified_archive(self) -> None:
        """Save a new archive in place of the current file with backup."""
        if not self.page_widgets:
            QMessageBox.warning(self, "Warning", "No pages loaded.")
            return

        selected_files = []
        for i, widget in enumerate(self.page_widgets):
            if widget.is_selected():
                selected_files.append(self.image_files[i])

        if not selected_files:
            QMessageBox.warning(self, "Warning", "No pages selected. Please select at least one page.")
            return

        if not self.current_file:
            return

        # Ask for confirmation
        total_pages = len(self.image_files)
        removed_count = total_pages - len(selected_files)
        original_ext = Path(self.current_file).suffix.lower()
        format_name = "CBR" if original_ext == '.cbr' else "CBZ"

        # Determine what type of archive will be created
        if original_ext == '.cbr':
            if self.is_rar_available():
                archive_info = f"Format: {format_name} (will attempt RAR-based, fallback to ZIP-based)"
            else:
                archive_info = f"Format: {format_name} (ZIP-based - no RAR tool found)"
        else:
            archive_info = f"Format: {format_name} (ZIP-based)"

        reply = QMessageBox.question(
            self,
            "Save In Place",
            f"This will replace the original file with {len(selected_files)} pages "
            f"(removing {removed_count} pages).\n\n"
            f"{archive_info}\n"
            f"A backup will be created in the 'backups' folder.\n\n"
            f"Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.create_new_archive_in_place(selected_files, self.current_file)

    def save_as_modified_archive(self) -> None:
        """Save a new archive with only selected pages to a new location."""
        if not self.page_widgets:
            QMessageBox.warning(self, "Warning", "No pages loaded.")
            return

        selected_files = []
        for i, widget in enumerate(self.page_widgets):
            if widget.is_selected():
                selected_files.append(self.image_files[i])

        if not selected_files:
            QMessageBox.warning(self, "Warning", "No pages selected. Please select at least one page.")
            return

        if not self.current_file:
            return

        original_name = Path(self.current_file).stem
        default_name = f"{original_name}_modified.cbz"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Modified Archive",
            default_name,
            "Comic Book Archive (*.cbz);;All Files (*)"
        )

        if save_path:
            self.create_new_archive(selected_files, save_path)

    def create_new_archive(self, selected_files: List[str], save_path: str) -> None:
        """Create a new CBZ archive with selected pages."""
        try:
            self.status_label.setText("Creating new archive...")

            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, file_path in enumerate(selected_files):
                    # Create a proper filename with page number
                    extension = Path(file_path).suffix
                    new_name = f"page_{i+1:03d}{extension}"

                    zip_file.write(file_path, new_name)

            removed_count = len(self.image_files) - len(selected_files)
            QMessageBox.information(
                self,
                "Success",
                f"Archive saved successfully!\n"
                f"Saved {len(selected_files)} pages.\n"
                f"Removed {removed_count} pages.\n"
                f"File: {save_path}"
            )

            self.status_label.setText(f"Archive saved: {os.path.basename(save_path)}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save archive: {str(e)}")
            self.status_label.setText("Error saving archive.")

    def is_rar_available(self) -> bool:
        """Check if RAR command-line tool is available."""
        try:
            # Try to run 'rar' command to see if it's available
            subprocess.run(['rar'], capture_output=True, text=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            try:
                # Try alternative RAR executable names
                subprocess.run(['winrar'], capture_output=True, text=True, timeout=5)
                return True
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                return False

    def create_rar_archive(self, selected_files: List[str], output_path: str) -> bool:
        """Create a RAR archive using command-line RAR tool. Returns True if successful."""
        try:
            # Create a temporary directory to organize files with proper names
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Copy files with proper page names
                for i, file_path in enumerate(selected_files):
                    extension = Path(file_path).suffix
                    new_name = f"page_{i+1:03d}{extension}"
                    temp_file = temp_path / new_name
                    shutil.copy2(file_path, temp_file)

                # Try to create RAR archive
                rar_commands = ['rar', 'winrar']
                for rar_cmd in rar_commands:
                    try:
                        # RAR command: a = add, -r = recurse subdirectories, -ep1 = exclude base folder from paths
                        cmd = [rar_cmd, 'a', '-r', '-ep1', str(output_path), str(temp_path / '*')]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                        if result.returncode == 0:
                            return True
                    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                        continue

                return False

        except Exception:
            return False

    def create_new_archive_in_place(self, selected_files: List[str], original_path: str) -> None:
        """Create a new archive in place of the original, with backup. Preserves original format (CBR/CBZ)."""
        try:
            self.status_label.setText("Creating backup...")

            # Create backup file in backups folder
            backup_path = self.get_backup_path(original_path)
            original_file = Path(original_path)
            original_ext = original_file.suffix.lower()

            # If backup already exists, ask user what to do
            if backup_path.exists():
                reply = QMessageBox.question(
                    self,
                    "Backup Exists",
                    f"A backup file already exists:\n{backup_path}\n\nOverwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    self.status_label.setText("Save cancelled.")
                    return

            # Create backup
            shutil.copy2(original_path, backup_path)
            self.status_label.setText("Creating new archive...")

            # Create temporary file for the new archive with same extension as original
            temp_archive = original_file.parent / f"{original_file.stem}_temp{original_ext}"

            if original_ext == '.cbr':
                # For CBR files, try to create a true RAR archive first
                if self.is_rar_available():
                    self.status_label.setText("Creating RAR archive...")
                    if self.create_rar_archive(selected_files, str(temp_archive)):
                        archive_type = "RAR-based CBR"
                    else:
                        # If RAR creation fails, fall back to ZIP-based CBR
                        self.status_label.setText("RAR failed, creating ZIP-based CBR...")
                        with zipfile.ZipFile(temp_archive, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for i, file_path in enumerate(selected_files):
                                extension = Path(file_path).suffix
                                new_name = f"page_{i+1:03d}{extension}"
                                zip_file.write(file_path, new_name)
                        archive_type = "ZIP-based CBR"
                else:
                    # No RAR tool available, create ZIP-based CBR
                    self.status_label.setText("Creating ZIP-based CBR (no RAR tool found)...")
                    with zipfile.ZipFile(temp_archive, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for i, file_path in enumerate(selected_files):
                            extension = Path(file_path).suffix
                            new_name = f"page_{i+1:03d}{extension}"
                            zip_file.write(file_path, new_name)
                    archive_type = "ZIP-based CBR"
            else:  # CBZ format
                # For CBZ files, always use ZIP format
                self.status_label.setText("Creating ZIP archive...")
                with zipfile.ZipFile(temp_archive, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for i, file_path in enumerate(selected_files):
                        # Create a proper filename with page number
                        extension = Path(file_path).suffix
                        new_name = f"page_{i+1:03d}{extension}"

                        zip_file.write(file_path, new_name)
                archive_type = "ZIP-based CBZ"

            # Replace original file with new archive
            if original_file.exists():
                original_file.unlink()  # Delete original
            temp_archive.rename(original_file)  # Rename temp to original

            removed_count = len(self.image_files) - len(selected_files)
            format_name = "CBR" if original_ext == '.cbr' else "CBZ"
            QMessageBox.information(
                self,
                "Success",
                f"Archive saved successfully!\n"
                f"Saved {len(selected_files)} pages.\n"
                f"Removed {removed_count} pages.\n"
                f"Format: {format_name} ({archive_type})\n"
                f"Original backed up to: backups/{backup_path.name}\n"
                f"File: {original_path}"
            )

            self.status_label.setText(f"Archive saved in place ({archive_type}). Backup: backups/{backup_path.name}")
            self.update_revert_button()  # Update revert button visibility

        except Exception as e:
            # Try to restore from backup if something went wrong
            try:
                if backup_path.exists() and not original_file.exists():
                    shutil.copy2(backup_path, original_path)
            except Exception:
                pass

            QMessageBox.critical(self, "Error", f"Failed to save archive: {str(e)}")
            self.status_label.setText("Error saving archive.")

    def revert_from_backup(self) -> None:
        """Revert the current file from its backup."""
        if not self.current_file:
            return

        original_file = Path(self.current_file)
        backup_path = self.get_latest_backup_path(self.current_file)

        if not backup_path or not backup_path.exists():
            QMessageBox.warning(self, "Warning", "No backup file found.")
            return

        reply = QMessageBox.question(
            self,
            "Revert from Backup",
            f"This will replace the current file with the backup version.\n\n"
            f"Current file: {original_file.name}\n"
            f"Backup file: backups/{backup_path.name}\n\n"
            f"Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Replace current file with backup
                if original_file.exists():
                    original_file.unlink()
                shutil.copy2(backup_path, original_file)

                QMessageBox.information(
                    self,
                    "Success",
                    f"File reverted successfully from backup.\n"
                    f"File: {original_file.name}"
                )

                # Reload the file
                self.extract_images(str(original_file))

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to revert from backup: {str(e)}")

    def get_backup_path(self, original_path: str) -> Path:
        """Get the backup file path in the backups folder."""
        original_file = Path(original_path)

        # Create backups directory in current working directory
        backup_dir = Path.cwd() / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Create backup filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{original_file.stem}_backup_{timestamp}{original_file.suffix}"

        return backup_dir / backup_filename

    def get_latest_backup_path(self, original_path: str) -> Optional[Path]:
        """Get the latest backup file path for the given original file."""
        original_file = Path(original_path)
        backup_dir = Path.cwd() / "backups"

        if not backup_dir.exists():
            return None

        # Find all backup files for this original file
        pattern = f"{original_file.stem}_backup_*{original_file.suffix}"
        backup_files = list(backup_dir.glob(pattern))

        if not backup_files:
            return None

        # Return the most recent backup (sorted by filename which includes timestamp)
        return sorted(backup_files)[-1]

    def check_backup_exists(self) -> bool:
        """Check if a backup exists for the current file."""
        if not self.current_file:
            return False

        latest_backup = self.get_latest_backup_path(self.current_file)
        return latest_backup is not None and latest_backup.exists()

    def update_revert_button(self) -> None:
        """Update the visibility and state of the revert button."""
        has_backup = self.check_backup_exists()
        self.revert_button.setVisible(has_backup)
        self.revert_button.setEnabled(has_backup)

    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Comic Book Reader",
            "Comic Book Reader v1.0\n\n"
            "A simple application to read CBR/CBZ files\n"
            "and remove unwanted pages.\n\n"
            "Supported formats: CBR, CBZ\n"
            "Built with PySide6 and Python"
        )

    def cleanup_temp_dir(self) -> None:
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temp directory: {e}")
        self.temp_dir = None

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle application close event."""
        self.cleanup_temp_dir()
        event.accept()

    def get_comic_files_in_directory(self, file_path: str) -> List[str]:
        """Get all comic book files in the same directory as the given file."""
        directory = Path(file_path).parent
        comic_extensions = {'.cbr', '.cbz'}
        comic_files = []

        try:
            for file in directory.iterdir():
                if file.is_file() and file.suffix.lower() in comic_extensions:
                    comic_files.append(str(file.resolve()))  # Use resolved absolute path
        except Exception:
            return []

        # Sort files naturally
        comic_files.sort(key=lambda x: Path(x).name.lower())
        return comic_files

    def get_current_file_index(self) -> int:
        """Get the index of the current file in the directory listing."""
        if not self.current_file:
            return -1

        comic_files = self.get_comic_files_in_directory(self.current_file)

        # Normalize current file path for comparison
        current_file_normalized = str(Path(self.current_file).resolve())

        try:
            return comic_files.index(current_file_normalized)
        except ValueError:
            return -1

    def update_navigation_buttons(self) -> None:
        """Update the enabled state of navigation buttons."""
        if not self.current_file:
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return

        comic_files = self.get_comic_files_in_directory(self.current_file)
        current_index = self.get_current_file_index()

        if current_index >= 0 and len(comic_files) > 1:
            prev_enabled = current_index > 0
            next_enabled = current_index < len(comic_files) - 1
            self.prev_button.setEnabled(prev_enabled)
            self.next_button.setEnabled(next_enabled)
        else:
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)

    def open_previous_file(self) -> None:
        """Open the previous comic file in the directory."""
        if not self.current_file:
            return

        comic_files = self.get_comic_files_in_directory(self.current_file)
        current_index = self.get_current_file_index()

        if current_index > 0:
            prev_file = comic_files[current_index - 1]

            # Show loading state
            self.prev_button.setText("Loading...")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)

            # Disable other buttons during navigation
            self.save_button.setEnabled(False)
            self.save_as_button.setEnabled(False)
            self.select_all_button.setEnabled(False)
            self.select_none_button.setEnabled(False)

            self.current_file = prev_file
            self.extract_images(prev_file)

    def open_next_file(self) -> None:
        """Open the next comic file in the directory."""
        if not self.current_file:
            return

        comic_files = self.get_comic_files_in_directory(self.current_file)
        current_index = self.get_current_file_index()

        if current_index >= 0 and current_index < len(comic_files) - 1:
            next_file = comic_files[current_index + 1]

            # Show loading state
            self.next_button.setText("Loading...")
            self.next_button.setEnabled(False)
            self.prev_button.setEnabled(False)

            # Disable other buttons during navigation
            self.save_button.setEnabled(False)
            self.save_as_button.setEnabled(False)
            self.select_all_button.setEnabled(False)
            self.select_none_button.setEnabled(False)

            self.current_file = next_file
            self.extract_images(next_file)

def main() -> None:
    """Main function to run the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Comic Book Reader")
    app.setApplicationVersion("1.0")

    # Set application style
    app.setStyle('Fusion')

    window = ComicBookReader()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

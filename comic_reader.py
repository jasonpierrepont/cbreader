import sys
import os
import tempfile
import shutil
import zipfile
import patoolib
from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox,
    QScrollArea, QGridLayout, QCheckBox, QFrame, QProgressBar,
    QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QAction


class ImageExtractor(QThread):
    """Thread to extract images from comic book archives."""
    
    progress_updated = Signal(int, str)
    extraction_finished = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.temp_dir = None
        
    def run(self):
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
    
    def extract_zip(self):
        """Extract CBZ (ZIP) file."""
        self.progress_updated.emit(30, "Extracting CBZ file...")
        with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)
    
    def extract_rar(self):
        """Extract CBR (RAR) file using patool."""
        self.progress_updated.emit(30, "Extracting CBR file...")
        patoolib.extract_archive(self.file_path, outdir=self.temp_dir)
    
    def find_image_files(self) -> List[str]:
        """Find all image files in the extracted directory."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files: List[str] = []
        
        if self.temp_dir and os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    if Path(file).suffix.lower() in image_extensions:
                        image_files.append(os.path.join(root, file))
        
        # Sort files naturally
        image_files.sort(key=lambda x: Path(x).name.lower())
        return image_files


class PageWidget(QFrame):
    """Widget to display a single comic page with selection checkbox."""
    
    def __init__(self, image_path: str, page_number: int):
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
    
    def load_thumbnail(self):
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
    
    def on_selection_changed(self, state):
        """Handle checkbox state change."""
        self.selected = state == Qt.CheckState.Checked
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
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.temp_dir = None
        self.image_files = []
        self.page_widgets = []
        
        self.init_ui()
        
    def init_ui(self):
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
        
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_action = QAction('Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
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
    
    def open_file(self):
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
    
    def extract_images(self, file_path: str):
        """Extract images from the comic book archive."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Extracting archive...")
        
        # Clean up previous temp directory
        self.cleanup_temp_dir()
        
        # Create and start extraction thread
        self.extractor = ImageExtractor(file_path)
        self.extractor.progress_updated.connect(self.update_progress)
        self.extractor.extraction_finished.connect(self.on_extraction_finished)
        self.extractor.error_occurred.connect(self.on_extraction_error)
        self.extractor.start()
    
    def update_progress(self, value: int, message: str):
        """Update progress bar and status."""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def on_extraction_finished(self, image_files: List[str]):
        """Handle successful extraction."""
        self.progress_bar.setVisible(False)
        self.image_files = image_files
        self.temp_dir = self.extractor.temp_dir
        
        if not image_files:
            QMessageBox.warning(self, "Warning", "No image files found in the archive.")
            return
        
        self.load_pages()
        self.update_info_panel()
        self.update_revert_button()
        
        # Enable buttons
        self.select_all_button.setEnabled(True)
        self.select_none_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.save_as_button.setEnabled(True)
        
        self.status_label.setText(f"Loaded {len(image_files)} pages. Select pages to keep, then save.")
    
    def on_extraction_error(self, error_message: str):
        """Handle extraction error."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error occurred during extraction.")
        QMessageBox.critical(self, "Extraction Error", error_message)
    
    def load_pages(self):
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
    
    def select_all_pages(self):
        """Select all pages."""
        for widget in self.page_widgets:
            widget.checkbox.setChecked(True)
    
    def select_no_pages(self):
        """Deselect all pages."""
        for widget in self.page_widgets:
            widget.checkbox.setChecked(False)
    
    def update_info_panel(self):
        """Update the information panel."""
        if not self.image_files or not self.current_file:
            return
            
        total_pages = len(self.image_files)
        selected_pages = sum(1 for widget in self.page_widgets if widget.is_selected())
        
        info_text = f"""
Current File: {os.path.basename(self.current_file)}
Total Pages: {total_pages}
Selected Pages: {selected_pages}
Pages to Remove: {total_pages - selected_pages}

Instructions:
1. Uncheck pages you want to remove
2. Click 'Save Modified Archive' to create a new file
"""
        self.info_text.setText(info_text)
    
    def save_modified_archive(self):
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
        
        reply = QMessageBox.question(
            self,
            "Save In Place",
            f"This will replace the original file with {len(selected_files)} pages "
            f"(removing {removed_count} pages).\n\n"
            f"A backup will be created as '{Path(self.current_file).stem}_backup{Path(self.current_file).suffix}'.\n\n"
            f"Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.create_new_archive_in_place(selected_files, self.current_file)
    
    def save_as_modified_archive(self):
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
    
    def create_new_archive(self, selected_files: List[str], save_path: str):
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
    
    def create_new_archive_in_place(self, selected_files: List[str], original_path: str):
        """Create a new CBZ archive in place of the original, with backup."""
        try:
            self.status_label.setText("Creating backup...")
            
            # Create backup file
            original_file = Path(original_path)
            backup_path = original_file.parent / f"{original_file.stem}_backup{original_file.suffix}"
            
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
            
            # Create temporary file for the new archive
            temp_archive = original_file.parent / f"{original_file.stem}_temp.cbz"
            
            with zipfile.ZipFile(temp_archive, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, file_path in enumerate(selected_files):
                    # Create a proper filename with page number
                    extension = Path(file_path).suffix
                    new_name = f"page_{i+1:03d}{extension}"
                    
                    zip_file.write(file_path, new_name)
            
            # Replace original file with new archive
            if original_file.exists():
                original_file.unlink()  # Delete original
            temp_archive.rename(original_file)  # Rename temp to original
            
            removed_count = len(self.image_files) - len(selected_files)
            QMessageBox.information(
                self, 
                "Success", 
                f"Archive saved successfully!\n"
                f"Saved {len(selected_files)} pages.\n"
                f"Removed {removed_count} pages.\n"
                f"Original backed up as: {backup_path.name}\n"
                f"File: {original_path}"
            )
            
            self.status_label.setText(f"Archive saved in place. Backup: {backup_path.name}")
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
    
    def revert_from_backup(self):
        """Revert the current file from its backup."""
        if not self.current_file:
            return
        
        original_file = Path(self.current_file)
        backup_path = original_file.parent / f"{original_file.stem}_backup{original_file.suffix}"
        
        if not backup_path.exists():
            QMessageBox.warning(self, "Warning", "No backup file found.")
            return
        
        reply = QMessageBox.question(
            self,
            "Revert from Backup",
            f"This will replace the current file with the backup version.\n\n"
            f"Current file: {original_file.name}\n"
            f"Backup file: {backup_path.name}\n\n"
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
    
    def check_backup_exists(self):
        """Check if a backup exists for the current file."""
        if not self.current_file:
            return False
        
        original_file = Path(self.current_file)
        backup_path = original_file.parent / f"{original_file.stem}_backup{original_file.suffix}"
        return backup_path.exists()
    
    def update_revert_button(self):
        """Update the visibility and state of the revert button."""
        has_backup = self.check_backup_exists()
        self.revert_button.setVisible(has_backup)
        self.revert_button.setEnabled(has_backup)
    
    def show_about(self):
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
    
    def cleanup_temp_dir(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temp directory: {e}")
        self.temp_dir = None
    
    def closeEvent(self, event):
        """Handle application close event."""
        self.cleanup_temp_dir()
        event.accept()


def main():
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

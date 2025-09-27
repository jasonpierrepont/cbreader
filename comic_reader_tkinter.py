import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import patoolib


class ImageExtractor:
    """Class to extract images from comic book archives using threading."""

    def __init__(self, file_path: str, progress_callback: Callable[[int, str], None],
                 finished_callback: Callable[[List[str]], None],
                 error_callback: Callable[[str], None]) -> None:
        self.file_path = file_path
        self.temp_dir: Optional[str] = None
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback
        self.error_callback = error_callback

    def extract_async(self) -> None:
        """Start extraction in a separate thread."""
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self) -> None:
        try:
            self.temp_dir = tempfile.mkdtemp()
            self.progress_callback(10, "Creating temporary directory...")

            # Determine file type and extract
            file_ext = Path(self.file_path).suffix.lower()

            if file_ext == '.cbz':
                self._extract_zip()
            elif file_ext == '.cbr':
                self._extract_rar()
            else:
                self.error_callback(f"Unsupported file format: {file_ext}")
                return

            # Find image files
            self.progress_callback(80, "Scanning for images...")
            image_files = self._find_image_files()

            self.progress_callback(100, "Extraction complete!")
            self.finished_callback(image_files)

        except Exception as e:
            self.error_callback(f"Error extracting archive: {str(e)}")

    def _extract_zip(self) -> None:
        """Extract CBZ (ZIP) file."""
        self.progress_callback(30, "Extracting CBZ file...")
        with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)

    def _extract_rar(self) -> None:
        """Extract CBR (RAR) file using patool, with fallback to ZIP for ZIP-based CBR files."""
        self.progress_callback(30, "Extracting CBR file...")
        try:
            # First try to extract as a RAR file
            patoolib.extract_archive(self.file_path, outdir=self.temp_dir)
        except Exception as rar_error:
            # If RAR extraction fails, try ZIP extraction (for ZIP-based CBR files)
            self.progress_callback(40, "Trying ZIP extraction for CBR file...")
            try:
                with zipfile.ZipFile(self.file_path, 'r') as zip_ref:
                    zip_ref.extractall(self.temp_dir)
            except Exception as zip_error:
                # If both fail, raise a combined error message
                raise Exception(
                    f"Failed to extract CBR file. RAR error: {str(rar_error)}, ZIP error: {str(zip_error)}"
                ) from rar_error

    def _find_image_files(self) -> List[str]:
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


class PageWidget:
    """Widget to display a single comic page with selection checkbox."""

    def __init__(self, parent: tk.Widget, image_path: str, page_number: int) -> None:
        self.image_path = image_path
        self.page_number = page_number
        self.selected = True

        # Create frame for this page
        self.frame = tk.Frame(parent, relief=tk.SOLID, borderwidth=1)
        self.frame.configure(width=150, height=200)

        # Checkbox for selection
        self.var = tk.BooleanVar(value=True)
        self.checkbox = tk.Checkbutton(
            self.frame,
            text=f"Page {page_number}",
            variable=self.var,
            command=self._on_selection_changed
        )
        self.checkbox.pack()

        # Image label
        self.image_label = tk.Label(self.frame)
        self.image_label.pack(expand=True, fill=tk.BOTH)

        # Load and display thumbnail
        self._load_thumbnail()

        # Update initial appearance
        self._on_selection_changed()

    def _load_thumbnail(self) -> None:
        """Load and display a thumbnail of the image."""
        try:
            # Open image with PIL
            pil_image = Image.open(self.image_path)
            
            # Resize to fit while maintaining aspect ratio
            pil_image.thumbnail((140, 180), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage for tkinter
            self.photo = ImageTk.PhotoImage(pil_image)
            self.image_label.configure(image=self.photo)
            
        except Exception as e:
            self.image_label.configure(text=f"Error: {str(e)}", image="")

    def _on_selection_changed(self) -> None:
        """Handle checkbox state change."""
        self.selected = self.var.get()
        # Change appearance based on selection
        if self.selected:
            self.frame.configure(bg="white")
            self.checkbox.configure(bg="white")
            self.image_label.configure(bg="white")
        else:
            self.frame.configure(bg="#ffcccc")
            self.checkbox.configure(bg="#ffcccc")
            self.image_label.configure(bg="#ffcccc")

    def is_selected(self) -> bool:
        """Return whether this page is selected."""
        return self.selected

    def set_selected(self, selected: bool) -> None:
        """Set the selection state."""
        self.var.set(selected)
        self._on_selection_changed()


class ComicBookReader:
    """Main comic book reader application."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.current_file: Optional[str] = None
        self.temp_dir: Optional[str] = None
        self.image_files: List[str] = []
        self.page_widgets: List[PageWidget] = []

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        self.root.title("Comic Book Reader - CBR/CBZ Editor (Tkinter)")
        self.root.geometry("1200x800")

        # Create menu bar
        self._create_menu_bar()

        # Create main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create toolbar
        toolbar_frame = tk.Frame(main_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))

        # Open button
        self.open_button = tk.Button(
            toolbar_frame,
            text="Open CBR/CBZ File",
            command=self._open_file
        )
        self.open_button.pack(side=tk.LEFT, padx=(0, 5))

        # Navigation buttons
        self.prev_button = tk.Button(
            toolbar_frame,
            text="◀ Previous",
            command=self._open_previous_file,
            state=tk.DISABLED
        )
        self.prev_button.pack(side=tk.LEFT, padx=(0, 5))

        self.next_button = tk.Button(
            toolbar_frame,
            text="Next ▶",
            command=self._open_next_file,
            state=tk.DISABLED
        )
        self.next_button.pack(side=tk.LEFT, padx=(0, 20))

        # Selection buttons
        self.select_all_button = tk.Button(
            toolbar_frame,
            text="Select All",
            command=self._select_all_pages,
            state=tk.DISABLED
        )
        self.select_all_button.pack(side=tk.LEFT, padx=(0, 5))

        self.select_none_button = tk.Button(
            toolbar_frame,
            text="Select None",
            command=self._select_no_pages,
            state=tk.DISABLED
        )
        self.select_none_button.pack(side=tk.LEFT, padx=(0, 20))

        # Save buttons
        self.save_button = tk.Button(
            toolbar_frame,
            text="Save In Place",
            command=self._save_modified_archive,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT, padx=(0, 5))

        self.save_as_button = tk.Button(
            toolbar_frame,
            text="Save As...",
            command=self._save_as_modified_archive,
            state=tk.DISABLED
        )
        self.save_as_button.pack(side=tk.LEFT, padx=(0, 5))

        self.revert_button = tk.Button(
            toolbar_frame,
            text="Revert from Backup",
            command=self._revert_from_backup,
            state=tk.DISABLED
        )
        self.revert_button.pack(side=tk.LEFT, padx=(0, 5))
        self.revert_button.pack_forget()  # Initially hidden

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100
        )
        # Initially hidden

        # Status label
        self.status_label = tk.Label(
            main_frame,
            text="Open a CBR or CBZ file to get started.",
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, pady=(0, 10))

        # Create scrollable frame for pages
        self.canvas = tk.Canvas(main_frame)
        self.scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Info panel
        info_frame = tk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))

        info_label = tk.Label(info_frame, text="Information:", anchor=tk.W)
        info_label.pack(fill=tk.X)

        self.info_text = scrolledtext.ScrolledText(
            info_frame,
            height=6,
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.info_text.pack(fill=tk.X)

        # Bind mouse wheel to canvas
        self._bind_mousewheel()

    def _bind_mousewheel(self) -> None:
        """Bind mouse wheel to canvas scrolling."""
        def on_mousewheel(event) -> None:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        self.canvas.bind("<MouseWheel>", on_mousewheel)

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)

        file_menu.add_command(label="Open", command=self._open_file, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Previous File", command=self._open_previous_file, accelerator="Ctrl+Left")
        file_menu.add_command(label="Next File", command=self._open_next_file, accelerator="Ctrl+Right")
        file_menu.add_separator()
        file_menu.add_command(label="Save In Place", command=self._save_modified_archive, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self._save_as_modified_archive, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self._open_file())
        self.root.bind('<Control-s>', lambda e: self._save_modified_archive())
        self.root.bind('<Control-Shift-S>', lambda e: self._save_as_modified_archive())
        self.root.bind('<Control-Left>', lambda e: self._open_previous_file())
        self.root.bind('<Control-Right>', lambda e: self._open_next_file())
        self.root.bind('<Control-q>', lambda e: self.root.quit())

    def _open_file(self) -> None:
        """Open a CBR or CBZ file."""
        file_path = filedialog.askopenfilename(
            title="Open Comic Book Archive",
            filetypes=[
                ("Comic Book Files", "*.cbr *.cbz"),
                ("All Files", "*.*")
            ]
        )

        if file_path:
            self.current_file = file_path
            self._extract_images(file_path)

    def _extract_images(self, file_path: str) -> None:
        """Extract images from the comic book archive."""
        # Show progress bar
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        self.progress_var.set(0)

        # Show which file is being loaded
        filename = os.path.basename(file_path)
        self.status_label.configure(text=f"Loading {filename}...")

        # Clean up previous temp directory
        self._cleanup_temp_dir()

        # Create and start extraction
        self.extractor = ImageExtractor(
            file_path,
            self._update_progress,
            self._on_extraction_finished,
            self._on_extraction_error
        )
        self.extractor.extract_async()

    def _update_progress(self, value: int, message: str) -> None:
        """Update progress bar and status."""
        # Use after() to ensure thread-safe GUI updates
        self.root.after(0, lambda: self._update_progress_gui(value, message))

    def _update_progress_gui(self, value: int, message: str) -> None:
        """Update progress bar and status (GUI thread)."""
        self.progress_var.set(value)
        self.status_label.configure(text=message)

    def _on_extraction_finished(self, image_files: List[str]) -> None:
        """Handle successful extraction."""
        # Use after() to ensure thread-safe GUI updates
        self.root.after(0, lambda: self._on_extraction_finished_gui(image_files))

    def _on_extraction_finished_gui(self, image_files: List[str]) -> None:
        """Handle successful extraction (GUI thread)."""
        self.progress_bar.pack_forget()
        self.image_files = image_files
        self.temp_dir = self.extractor.temp_dir

        # Reset navigation button text
        self.prev_button.configure(text="◀ Previous")
        self.next_button.configure(text="Next ▶")

        if not image_files:
            messagebox.showwarning("Warning", "No image files found in the archive.")
            # Still update navigation buttons even if no images found
            self._update_navigation_buttons()
            return

        self._load_pages()
        self._update_info_panel()
        self._update_revert_button()
        self._update_navigation_buttons()

        # Enable buttons
        self.select_all_button.configure(state=tk.NORMAL)
        self.select_none_button.configure(state=tk.NORMAL)
        self.save_button.configure(state=tk.NORMAL)
        self.save_as_button.configure(state=tk.NORMAL)

        self.status_label.configure(text=f"Loaded {len(image_files)} pages. Select pages to keep, then save.")

    def _on_extraction_error(self, error_message: str) -> None:
        """Handle extraction error."""
        # Use after() to ensure thread-safe GUI updates
        self.root.after(0, lambda: self._on_extraction_error_gui(error_message))

    def _on_extraction_error_gui(self, error_message: str) -> None:
        """Handle extraction error (GUI thread)."""
        self.progress_bar.pack_forget()
        self.status_label.configure(text="Error occurred during extraction.")

        # Reset navigation button text and state
        self.prev_button.configure(text="◀ Previous")
        self.next_button.configure(text="Next ▶")
        self._update_navigation_buttons()

        # Re-enable other buttons
        has_pages = bool(self.page_widgets)
        self.select_all_button.configure(state=tk.NORMAL if has_pages else tk.DISABLED)
        self.select_none_button.configure(state=tk.NORMAL if has_pages else tk.DISABLED)
        self.save_button.configure(state=tk.NORMAL if has_pages else tk.DISABLED)
        self.save_as_button.configure(state=tk.NORMAL if has_pages else tk.DISABLED)

        messagebox.showerror("Extraction Error", error_message)

    def _load_pages(self) -> None:
        """Load and display page thumbnails."""
        # Clear existing pages
        for widget in self.page_widgets:
            widget.frame.destroy()
        self.page_widgets.clear()

        # Create page widgets in a grid layout
        columns = 5  # Number of columns in grid
        for i, image_path in enumerate(self.image_files):
            page_widget = PageWidget(self.scrollable_frame, image_path, i + 1)
            self.page_widgets.append(page_widget)

            row = i // columns
            col = i % columns
            page_widget.frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # Configure grid weights for proper resizing
        for col in range(columns):
            self.scrollable_frame.grid_columnconfigure(col, weight=1)

    def _select_all_pages(self) -> None:
        """Select all pages."""
        for widget in self.page_widgets:
            widget.set_selected(True)

    def _select_no_pages(self) -> None:
        """Deselect all pages."""
        for widget in self.page_widgets:
            widget.set_selected(False)

    def _update_info_panel(self) -> None:
        """Update the information panel."""
        if not self.image_files or not self.current_file:
            return

        total_pages = len(self.image_files)
        selected_pages = sum(1 for widget in self.page_widgets if widget.is_selected())

        # Determine file format and archive capabilities
        original_ext = Path(self.current_file).suffix.lower()
        format_name = "CBR" if original_ext == '.cbr' else "CBZ"

        if original_ext == '.cbr':
            if self._is_rar_available():
                format_detail = f"{format_name} (RAR-based creation available)"
            else:
                format_detail = f"{format_name} (ZIP-based only - no RAR tool)"
        else:
            format_detail = f"{format_name} (ZIP-based)"

        info_text = f"""Current File: {os.path.basename(self.current_file)}
Format: {format_detail}
Total Pages: {total_pages}
Selected Pages: {selected_pages}
Pages to Remove: {total_pages - selected_pages}

Instructions:
1. Uncheck pages you want to remove
2. Click 'Save In Place' to save in original format
3. Click 'Save As...' to save as CBZ in a new location"""

        self.info_text.configure(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info_text)
        self.info_text.configure(state=tk.DISABLED)

    def _save_modified_archive(self) -> None:
        """Save a new archive in place of the current file with backup."""
        if not self.page_widgets:
            messagebox.showwarning("Warning", "No pages loaded.")
            return

        selected_files = []
        for i, widget in enumerate(self.page_widgets):
            if widget.is_selected():
                selected_files.append(self.image_files[i])

        if not selected_files:
            messagebox.showwarning("Warning", "No pages selected. Please select at least one page.")
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
            if self._is_rar_available():
                archive_info = f"Format: {format_name} (will attempt RAR-based, fallback to ZIP-based)"
            else:
                archive_info = f"Format: {format_name} (ZIP-based - no RAR tool found)"
        else:
            archive_info = f"Format: {format_name} (ZIP-based)"

        result = messagebox.askyesno(
            "Save In Place",
            f"This will replace the original file with {len(selected_files)} pages "
            f"(removing {removed_count} pages).\n\n"
            f"{archive_info}\n"
            f"A backup will be created in the 'backups' folder.\n\n"
            f"Do you want to continue?"
        )

        if result:
            self._create_new_archive_in_place(selected_files, self.current_file)

    def _save_as_modified_archive(self) -> None:
        """Save a new archive with only selected pages to a new location."""
        if not self.page_widgets:
            messagebox.showwarning("Warning", "No pages loaded.")
            return

        selected_files = []
        for i, widget in enumerate(self.page_widgets):
            if widget.is_selected():
                selected_files.append(self.image_files[i])

        if not selected_files:
            messagebox.showwarning("Warning", "No pages selected. Please select at least one page.")
            return

        if not self.current_file:
            return

        original_name = Path(self.current_file).stem
        default_name = f"{original_name}_modified.cbz"

        save_path = filedialog.asksaveasfilename(
            title="Save Modified Archive",
            defaultextension=".cbz",
            initialfile=default_name,
            filetypes=[
                ("Comic Book Archive", "*.cbz"),
                ("All Files", "*.*")
            ]
        )

        if save_path:
            self._create_new_archive(selected_files, save_path)

    def _create_new_archive(self, selected_files: List[str], save_path: str) -> None:
        """Create a new CBZ archive with selected pages."""
        try:
            self.status_label.configure(text="Creating new archive...")

            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, file_path in enumerate(selected_files):
                    # Create a proper filename with page number
                    extension = Path(file_path).suffix
                    new_name = f"page_{i+1:03d}{extension}"

                    zip_file.write(file_path, new_name)

            removed_count = len(self.image_files) - len(selected_files)
            messagebox.showinfo(
                "Success",
                f"Archive saved successfully!\n"
                f"Saved {len(selected_files)} pages.\n"
                f"Removed {removed_count} pages.\n"
                f"File: {save_path}"
            )

            self.status_label.configure(text=f"Archive saved: {os.path.basename(save_path)}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save archive: {str(e)}")
            self.status_label.configure(text="Error saving archive.")

    def _is_rar_available(self) -> bool:
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

    def _create_rar_archive(self, selected_files: List[str], output_path: str) -> bool:
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

    def _create_new_archive_in_place(self, selected_files: List[str], original_path: str) -> None:
        """Create a new archive in place of the original, with backup. Preserves original format (CBR/CBZ)."""
        try:
            self.status_label.configure(text="Creating backup...")

            # Create backup file in backups folder
            backup_path = self._get_backup_path(original_path)
            original_file = Path(original_path)
            original_ext = original_file.suffix.lower()

            # If backup already exists, ask user what to do
            if backup_path.exists():
                result = messagebox.askyesno(
                    "Backup Exists",
                    f"A backup file already exists:\n{backup_path}\n\nOverwrite it?"
                )
                if not result:
                    self.status_label.configure(text="Save cancelled.")
                    return

            # Create backup
            shutil.copy2(original_path, backup_path)
            self.status_label.configure(text="Creating new archive...")

            # Create temporary file for the new archive with same extension as original
            temp_archive = original_file.parent / f"{original_file.stem}_temp{original_ext}"

            if original_ext == '.cbr':
                # For CBR files, try to create a true RAR archive first
                if self._is_rar_available():
                    self.status_label.configure(text="Creating RAR archive...")
                    if self._create_rar_archive(selected_files, str(temp_archive)):
                        archive_type = "RAR-based CBR"
                    else:
                        # If RAR creation fails, fall back to ZIP-based CBR
                        self.status_label.configure(text="RAR failed, creating ZIP-based CBR...")
                        with zipfile.ZipFile(temp_archive, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for i, file_path in enumerate(selected_files):
                                extension = Path(file_path).suffix
                                new_name = f"page_{i+1:03d}{extension}"
                                zip_file.write(file_path, new_name)
                        archive_type = "ZIP-based CBR"
                else:
                    # No RAR tool available, create ZIP-based CBR
                    self.status_label.configure(text="Creating ZIP-based CBR (no RAR tool found)...")
                    with zipfile.ZipFile(temp_archive, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for i, file_path in enumerate(selected_files):
                            extension = Path(file_path).suffix
                            new_name = f"page_{i+1:03d}{extension}"
                            zip_file.write(file_path, new_name)
                    archive_type = "ZIP-based CBR"
            else:  # CBZ format
                # For CBZ files, always use ZIP format
                self.status_label.configure(text="Creating ZIP archive...")
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
            messagebox.showinfo(
                "Success",
                f"Archive saved successfully!\n"
                f"Saved {len(selected_files)} pages.\n"
                f"Removed {removed_count} pages.\n"
                f"Format: {format_name} ({archive_type})\n"
                f"Original backed up to: backups/{backup_path.name}\n"
                f"File: {original_path}"
            )

            self.status_label.configure(text=f"Archive saved in place ({archive_type}). Backup: backups/{backup_path.name}")
            self._update_revert_button()  # Update revert button visibility

        except Exception as e:
            # Try to restore from backup if something went wrong
            try:
                if backup_path.exists() and not original_file.exists():
                    shutil.copy2(backup_path, original_path)
            except Exception:
                pass

            messagebox.showerror("Error", f"Failed to save archive: {str(e)}")
            self.status_label.configure(text="Error saving archive.")

    def _revert_from_backup(self) -> None:
        """Revert the current file from its backup."""
        if not self.current_file:
            return

        original_file = Path(self.current_file)
        backup_path = self._get_latest_backup_path(self.current_file)

        if not backup_path or not backup_path.exists():
            messagebox.showwarning("Warning", "No backup file found.")
            return

        result = messagebox.askyesno(
            "Revert from Backup",
            f"This will replace the current file with the backup version.\n\n"
            f"Current file: {original_file.name}\n"
            f"Backup file: backups/{backup_path.name}\n\n"
            f"Do you want to continue?"
        )

        if result:
            try:
                # Replace current file with backup
                if original_file.exists():
                    original_file.unlink()
                shutil.copy2(backup_path, original_file)

                messagebox.showinfo(
                    "Success",
                    f"File reverted successfully from backup.\n"
                    f"File: {original_file.name}"
                )

                # Reload the file
                self._extract_images(str(original_file))

            except Exception as e:
                messagebox.showerror("Error", f"Failed to revert from backup: {str(e)}")

    def _get_backup_path(self, original_path: str) -> Path:
        """Get the backup file path in the backups folder."""
        original_file = Path(original_path)

        # Create backups directory in current working directory
        backup_dir = Path.cwd() / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Create backup filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{original_file.stem}_backup_{timestamp}{original_file.suffix}"

        return backup_dir / backup_filename

    def _get_latest_backup_path(self, original_path: str) -> Optional[Path]:
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

    def _check_backup_exists(self) -> bool:
        """Check if a backup exists for the current file."""
        if not self.current_file:
            return False

        latest_backup = self._get_latest_backup_path(self.current_file)
        return latest_backup is not None and latest_backup.exists()

    def _update_revert_button(self) -> None:
        """Update the visibility and state of the revert button."""
        has_backup = self._check_backup_exists()
        if has_backup:
            self.revert_button.pack(side=tk.LEFT, padx=(0, 5))
            self.revert_button.configure(state=tk.NORMAL)
        else:
            self.revert_button.pack_forget()

    def _show_about(self) -> None:
        """Show about dialog."""
        messagebox.showinfo(
            "About Comic Book Reader",
            "Comic Book Reader v1.0 (Tkinter)\n\n"
            "A simple application to read CBR/CBZ files\n"
            "and remove unwanted pages.\n\n"
            "Supported formats: CBR, CBZ\n"
            "Built with tkinter and Python"
        )

    def _cleanup_temp_dir(self) -> None:
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temp directory: {e}")
        self.temp_dir = None

    def _get_comic_files_in_directory(self, file_path: str) -> List[str]:
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

    def _get_current_file_index(self) -> int:
        """Get the index of the current file in the directory listing."""
        if not self.current_file:
            return -1

        comic_files = self._get_comic_files_in_directory(self.current_file)

        # Normalize current file path for comparison
        current_file_normalized = str(Path(self.current_file).resolve())

        try:
            return comic_files.index(current_file_normalized)
        except ValueError:
            return -1

    def _update_navigation_buttons(self) -> None:
        """Update the enabled state of navigation buttons."""
        if not self.current_file:
            self.prev_button.configure(state=tk.DISABLED)
            self.next_button.configure(state=tk.DISABLED)
            return

        comic_files = self._get_comic_files_in_directory(self.current_file)
        current_index = self._get_current_file_index()

        if current_index >= 0 and len(comic_files) > 1:
            prev_enabled = current_index > 0
            next_enabled = current_index < len(comic_files) - 1
            self.prev_button.configure(state=tk.NORMAL if prev_enabled else tk.DISABLED)
            self.next_button.configure(state=tk.NORMAL if next_enabled else tk.DISABLED)
        else:
            self.prev_button.configure(state=tk.DISABLED)
            self.next_button.configure(state=tk.DISABLED)

    def _open_previous_file(self) -> None:
        """Open the previous comic file in the directory."""
        if not self.current_file:
            return

        comic_files = self._get_comic_files_in_directory(self.current_file)
        current_index = self._get_current_file_index()

        if current_index > 0:
            prev_file = comic_files[current_index - 1]

            # Show loading state
            self.prev_button.configure(text="Loading...", state=tk.DISABLED)
            self.next_button.configure(state=tk.DISABLED)

            # Disable other buttons during navigation
            self.save_button.configure(state=tk.DISABLED)
            self.save_as_button.configure(state=tk.DISABLED)
            self.select_all_button.configure(state=tk.DISABLED)
            self.select_none_button.configure(state=tk.DISABLED)

            self.current_file = prev_file
            self._extract_images(prev_file)

    def _open_next_file(self) -> None:
        """Open the next comic file in the directory."""
        if not self.current_file:
            return

        comic_files = self._get_comic_files_in_directory(self.current_file)
        current_index = self._get_current_file_index()

        if current_index >= 0 and current_index < len(comic_files) - 1:
            next_file = comic_files[current_index + 1]

            # Show loading state
            self.next_button.configure(text="Loading...", state=tk.DISABLED)
            self.prev_button.configure(state=tk.DISABLED)

            # Disable other buttons during navigation
            self.save_button.configure(state=tk.DISABLED)
            self.save_as_button.configure(state=tk.DISABLED)
            self.select_all_button.configure(state=tk.DISABLED)
            self.select_none_button.configure(state=tk.DISABLED)

            self.current_file = next_file
            self._extract_images(next_file)

    def run(self) -> None:
        """Run the application."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()

    def _on_closing(self) -> None:
        """Handle application close event."""
        self._cleanup_temp_dir()
        self.root.destroy()


def main() -> None:
    """Main function to run the application."""
    try:
        # Check if required packages are available using importlib
        import importlib.util
        if importlib.util.find_spec("PIL") is None:
            raise ImportError("Pillow not found")
    except ImportError:
        print("Error: Pillow is required for image handling.")
        print("Install with: pip install Pillow")
        sys.exit(1)

    try:
        import importlib.util
        if importlib.util.find_spec("patoolib") is None:
            raise ImportError("patoolib not found")
    except ImportError:
        print("Warning: patoolib not found. CBR files may not work properly.")
        print("Install with: pip install patoolib")

    app = ComicBookReader()
    app.run()


if __name__ == "__main__":
    main()

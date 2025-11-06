# Comic Book Reader

A Python application built with PySide6 that allows you to read CBR (Comic Book RAR) and CBZ (Comic Book ZIP) files and remove unwanted pages.

## Features

- **Read CBR and CBZ files**: Supports both RAR and ZIP-based comic book archives
- **Page preview**: View thumbnails of all pages in a grid layout
- **Selective page removal**: Check/uncheck pages you want to keep or remove
- **Save in place with backup**: Replace the original file while keeping a backup copy
- **Save as new file**: Create a new CBZ file with only selected pages
- **Backup and restore**: Automatic backup creation and ability to revert changes
- **User-friendly interface**: Clean, modern GUI built with PySide6

## Requirements

- Python 3.7 or higher
- PySide6 (Qt for Python)
- Pillow (Python Imaging Library)
- patool (for RAR file extraction)

## Installation

### Option 1: Using UV (Recommended)

[UV](https://docs.astral.sh/uv/) is a fast Python package manager. If you have uv installed:

```bash
# Clone the repository
git clone <repository-url>
cd comic-book-reader

# Sync dependencies
uv sync

# Run the application
uv run comic-reader
```

### Option 2: Using pip

1. Clone or download this repository
2. Install the required dependencies:

```bash
````markdown
# Comic Book Reader - CBR/CBZ Editor

A Python application for reading and editing comic book archives (CBR/CBZ files). Available in both PySide6 (Qt) and tkinter versions.

## Features

- **Open and extract CBR/CBZ files** - Support for both RAR-based CBR and ZIP-based CBZ formats
- **Page management** - View thumbnail previews of all pages in a grid layout
- **Selective page removal** - Uncheck pages you want to remove from the archive
- **Save functionality**:
  - **Save In Place** - Replace the original file with automatic backup creation
  - **Save As** - Create a new archive with selected pages
- **Format preservation** - CBR files are saved as RAR when possible, with ZIP fallback
- **Backup system** - Automatic timestamped backups in a `backups` folder
- **Revert capability** - Restore from the most recent backup
- **Navigation** - Previous/Next buttons to browse through comic files in a directory
- **Loading indicators** - Visual feedback during file processing
- **Archive type detection** - Displays whether archives are RAR-based or ZIP-based

## Versions

### PySide6 Version (Recommended)
- **File**: `comic_reader.py`
- **Launch**: `launch.py` or `python comic_reader.py`
- **UI Framework**: PySide6 (Qt6)
- **Features**: Full-featured with modern Qt widgets

### Tkinter Version
- **File**: `comic_reader_tkinter.py`  
- **Launch**: `launch_tkinter.py` or `python comic_reader_tkinter.py`
- **UI Framework**: tkinter (built into Python)
- **Features**: Complete functionality using Python's standard GUI library

## Installation

### Prerequisites
- Python 3.8+
- Required packages (install via pip):

```bash
# For PySide6 version
pip install PySide6 Pillow patoolib

# For tkinter version (tkinter is built-in)
pip install Pillow patoolib
```

### Using uv (recommended)
```bash
uv sync
```

## Usage

### Running the Application

**PySide6 version:**
```bash
python comic_reader.py
# or
python launch.py
```

**Tkinter version:**
```bash
python comic_reader_tkinter.py
# or  
python launch_tkinter.py
```

### Using the Application

1. **Open a file**: Click "Open CBR/CBZ File" or use Ctrl+O
2. **Review pages**: All pages are displayed as thumbnails with checkboxes
3. **Select pages to keep**: Uncheck any pages you want to remove
4. **Save your changes**:
   - **Save In Place**: Replaces the original file (creates backup automatically)
   - **Save As**: Creates a new file with your changes
5. **Navigate**: Use Previous/Next buttons to browse other comics in the same folder

### Keyboard Shortcuts

- `Ctrl+O` - Open file
- `Ctrl+S` - Save in place  
- `Ctrl+Shift+S` - Save as
- `Ctrl+Left` - Previous file
- `Ctrl+Right` - Next file
- `Ctrl+Q` - Quit (PySide6 version)

## File Format Support

### CBR Files (Comic Book RAR)
- **RAR-based CBR**: Requires RAR command-line tool for creation
- **ZIP-based CBR**: Fallback when RAR tool is not available
- **Extraction**: Supports both RAR and ZIP-based CBR files

### CBZ Files (Comic Book ZIP)
- **Always ZIP-based**: Uses standard ZIP compression
- **Fully supported**: No external tools required

## Backup System

- Backups are automatically created in a `backups` folder
- Timestamped filenames prevent conflicts: `filename_backup_YYYYMMDD_HHMMSS.ext`
- Revert button appears when backups are available
- Each "Save In Place" operation creates a new backup

## Requirements

### Core Dependencies
- **Pillow**: Image processing and thumbnail generation
- **patoolib**: RAR/CBR archive extraction (optional but recommended)

### PDF Conversion (new)
- **PyMuPDF** (fitz): Used by `pdf2cbz.py` to extract embedded images or render pages to images. Install with `pip install PyMuPDF`.

### PySide6 Version Additional
- **PySide6**: Qt6 Python bindings for the GUI

### Optional
- **RAR command-line tool**: For creating true RAR-based CBR files
  - Windows: Install WinRAR or RAR for Windows
  - Linux: Install `rar` package
  - macOS: Install via Homebrew: `brew install rar`

## Project Structure

```
comic_reader/
├── comic_reader.py           # PySide6 version
├── comic_reader_tkinter.py   # tkinter version  
├── launch.py                 # PySide6 launcher
├── launch_tkinter.py         # tkinter launcher
├── requirements.txt          # Dependencies
├── pyproject.toml           # uv/pip configuration
├── README.md                # Original README
├── README_FULL.md           # This comprehensive guide
├── UV_SETUP.md              # uv setup instructions
├── backups/                 # Automatic backup folder (created when needed)
└── test_comics/             # Test files (if present)
```

## Technical Details

### Image Extraction
- Multi-threaded extraction for responsive UI
- Supports common image formats: JPG, PNG, GIF, BMP, WebP
- Natural sorting of page files
- Automatic cleanup of temporary files

### Archive Creation
- ZIP compression for CBZ files and ZIP-based CBR files
- RAR compression for true CBR files (when RAR tool is available)
- Proper page numbering: `page_001.jpg`, `page_002.jpg`, etc.
- Preserves original image formats

### Navigation
- Automatic detection of comic files in the current directory
- Path normalization for reliable file indexing
- Smart button enabling/disabling based on file position
- Loading states during navigation

## Differences Between Versions

| Feature | PySide6 Version | Tkinter Version |
|---------|----------------|-----------------|
| **Dependencies** | Requires PySide6 | Uses built-in tkinter |
| **Look & Feel** | Native Qt styling | Native OS styling |
| **Performance** | Excellent | Good |
| **Threading** | Qt signals/slots | Manual thread management |
| **Widgets** | Rich Qt widgets | Standard tkinter widgets |
| **Deployment** | Larger package size | Smaller package size |
| **Maintenance** | Qt ecosystem | Python standard library |

## Troubleshooting

### Common Issues

**"No image files found"**
- Archive may be corrupted or encrypted
- Unsupported archive format
- No actual image files in the archive

**"Failed to extract CBR file"**
- Install patoolib: `pip install patoolib`
- For RAR-based CBR files, install RAR command-line tool
- Some CBR files may be ZIP-based and will work without RAR

**Navigation buttons not working**
- Ensure there are multiple comic files in the same directory
- Check that files have .cbr or .cbz extensions

**Save operations failing**
- Check file permissions in the target directory
- Ensure sufficient disk space
- Verify the original file is not in use by another application

**Tkinter version image issues**
- Ensure Pillow is installed: `pip install Pillow`
- Check that image files are in supported formats

## Performance Tips

- **Large archives**: The application loads all page thumbnails into memory
- **Many pages**: Consider using the PySide6 version for better performance with 100+ page comics
- **Network drives**: Local storage provides better performance than network locations
- **SSD vs HDD**: Extraction and thumbnail generation are faster on SSDs

## Contributing

Contributions are welcome! Areas for improvement:
- Additional archive format support (7z, etc.)
- Better error handling and user feedback
- Performance optimizations for large files
- UI/UX enhancements
- Cross-platform testing and packaging
- Batch processing capabilities
- Metadata editing features

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Version History

- **v1.0**: Initial PySide6 version with core functionality
- **v1.1**: Added navigation buttons and loading indicators
- **v1.2**: Added tkinter version for broader compatibility
- **v1.3**: Enhanced backup system and error handling

````

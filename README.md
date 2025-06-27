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
pip install -r requirements.txt
```

## Usage

### Running the Application

You can run the application in several ways:

1. **Using UV (if available):**
```bash
uv run comic-reader
```

2. **Using the launcher script:**
```bash
python launch.py
```

3. **Running the main script directly:**
```bash
python comic_reader.py
```

### Using the Application

1. **Open a Comic Book File:**
   - Click "Open CBR/CBZ File" button or use Ctrl+O
   - Select a .cbr or .cbz file from your computer
   - Wait for the extraction and loading process to complete

2. **Preview and Select Pages:**
   - All pages will be displayed as thumbnails in a grid layout
   - Each page has a checkbox (checked by default)
   - Uncheck pages you want to remove from the final archive
   - Use "Select All" or "Select None" buttons for bulk operations

3. **Save Modified Archive:**
   - **Save In Place**: Click "Save In Place" to replace the original file
     - A backup will be automatically created (e.g., `comic_backup.cbz`)
     - The original file will be replaced with your edited version
   - **Save As**: Click "Save As..." to create a new file with your changes
     - Choose a location and filename for the new archive
     - The original file remains unchanged
   - **Revert from Backup**: If a backup exists, you can revert your changes
     - The "Revert from Backup" button appears when a backup is available
     - This will restore the original file from the backup

## File Formats Supported

- **CBZ (Comic Book ZIP)**: ZIP archives containing image files
- **CBR (Comic Book RAR)**: RAR archives containing image files

### Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- WebP (.webp)

## Technical Details

- The application extracts archives to a temporary directory for processing
- Images are automatically sorted by filename
- New archives are saved in CBZ format (ZIP)
- Pages are automatically renamed with sequential numbering (page_001.jpg, page_002.png, etc.)
- **Backup files** are created when using "Save In Place" with the suffix "_backup"
- Temporary files are cleaned up automatically when the application closes

## Troubleshooting

### RAR Files (CBR) Not Working
If you encounter issues with CBR files, make sure you have the appropriate RAR extraction tools installed:

- **Windows**: Install WinRAR or 7-Zip
- **macOS**: Install unrar via Homebrew: `brew install unrar`
- **Linux**: Install unrar package: `sudo apt-get install unrar` (Ubuntu/Debian)

### Memory Issues with Large Archives
For very large comic book archives:
- The application loads all images into memory for preview
- Consider closing other applications if you experience slowdowns
- Large archives may take some time to process

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

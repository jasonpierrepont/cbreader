# CBR to CBZ Converter

A Python script to convert Comic Book Archive files from RAR format (.cbr) to ZIP format (.cbz).

## Features

- **Single File Conversion**: Convert individual CBR files to CBZ format
- **Batch Conversion**: Convert all CBR files in a directory (with optional recursive search)
- **Automatic Backups**: Create timestamped backups of original CBR files
- **Smart File Handling**: Preserves original directory structure and sorts images naturally
- **Progress Tracking**: Detailed logging and progress information
- **Error Handling**: Robust error handling with detailed error messages
- **Flexible Options**: Customizable backup behavior and overwrite settings

## Requirements

- Python 3.6+
- `patool` (for RAR extraction)
- `Pillow` (for image handling)
- `PySide6` (for GUI interfaces, if using the main comic reader)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

### Command Line Usage

Convert a single CBR file:
```bash
python cbr2cbz.py "comic.cbr"
```

Convert all CBR files in a directory:
```bash
python cbr2cbz.py "comics_directory"
```

Convert recursively (including subdirectories):
```bash
python cbr2cbz.py "comics_directory" --recursive
```

### Advanced Options

```bash
# Convert without creating backups
python cbr2cbz.py "comic.cbr" --no-backup

# Overwrite existing CBZ files
python cbr2cbz.py "comic.cbr" --overwrite

# Enable verbose logging
python cbr2cbz.py "comics_directory" --verbose

# Combine multiple options
python cbr2cbz.py "comics_directory" --recursive --no-backup --overwrite --verbose
```

### Programmatic Usage

```python
from pathlib import Path
from cbr2cbz import CBRToCBZConverter

# Initialize converter
converter = CBRToCBZConverter(
    create_backups=True,  # Create backup copies
    overwrite=False       # Don't overwrite existing CBZ files
)

# Convert single file
success, message = converter.convert_file(Path("comic.cbr"))
if success:
    print(f"✓ {message}")
else:
    print(f"✗ {message}")

# Batch convert directory
successful, failed, errors = converter.convert_directory(
    Path("comics_directory"),
    recursive=True
)

print(f"Successful: {successful}, Failed: {failed}")
```

## How It Works

1. **Extraction**: Uses `patool` to extract CBR (RAR) files to a temporary directory
2. **Image Processing**: Identifies and sorts image files naturally (handling numeric sequences)
3. **Archive Creation**: Creates a new CBZ (ZIP) file containing all images
4. **Backup Management**: Optionally creates timestamped backups of original files
5. **Cleanup**: Automatically cleans up temporary files

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- WebP (.webp)
- TIFF (.tiff)

## Command Line Options

| Option | Description |
|--------|-------------|
| `input` | CBR file or directory containing CBR files |
| `-r, --recursive` | Search for CBR files recursively in subdirectories |
| `--no-backup` | Do not create backup copies of original CBR files |
| `--overwrite` | Overwrite existing CBZ files |
| `-v, --verbose` | Enable verbose logging |
| `-h, --help` | Show help message and exit |

## Examples

### Convert Single File with Backup
```bash
python cbr2cbz.py "Spawn #001.cbr"
```
Creates:
- `Spawn #001.cbz` (converted file)
- `backups/Spawn #001_backup_20250629_143022.cbr` (backup)

### Batch Convert Directory
```bash
python cbr2cbz.py "C:\Comics\Spawn" --recursive --verbose
```
Converts all CBR files in the Spawn directory and its subdirectories with detailed output.

### Convert Without Backups
```bash
python cbr2cbz.py "comics" --no-backup --overwrite
```
Converts all CBR files without creating backups and overwrites existing CBZ files.

## Error Handling

The converter handles various error conditions gracefully:

- **Missing Files**: Reports if CBR files don't exist
- **Corrupted Archives**: Skips files that can't be extracted
- **Permission Issues**: Reports access problems
- **Disk Space**: Handles insufficient disk space
- **Invalid Files**: Skips non-CBR files

## Backup System

When `create_backups=True` (default):
- Original CBR files are copied to a `backups` subdirectory
- Backup files include timestamps: `original_name_backup_YYYYMMDD_HHMMSS.cbr`
- Backups are created before conversion starts

## Dependencies

### Required
- **patool**: Handles RAR archive extraction (requires WinRAR, 7-Zip, or similar)
- **Pillow**: Image format support and validation

### System Requirements
- **Windows**: WinRAR or 7-Zip installed
- **Linux**: `unrar` or `rar` package
- **macOS**: `unrar` via Homebrew

## Troubleshooting

### "Could not find a 'file' executable"
This warning is normal on Windows and doesn't affect functionality.

### "Failed to extract CBR"
- Ensure WinRAR or 7-Zip is installed
- Check if the CBR file is corrupted
- Verify file permissions

### "No image files found"
- The CBR archive may not contain images
- Images may be in unsupported formats
- Check the archive structure

## Performance

- **Speed**: Processes archives efficiently using temporary directories
- **Memory**: Low memory usage, processes one archive at a time
- **Disk Space**: Requires temporary space equal to the largest uncompressed archive

## License

This project is part of the comic reader application. See the main project documentation for license information.

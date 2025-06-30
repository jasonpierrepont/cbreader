#!/usr/bin/env python3
"""
Example usage of the CBR to CBZ converter.

This file demonstrates how to use the CBRToCBZConverter class programmatically.
"""

from pathlib import Path

from cbr2cbz import CBRToCBZConverter


def example_single_file_conversion() -> None:
    """Example: Convert a single CBR file."""
    print("=== Single File Conversion ===")

    # Initialize converter with options
    converter = CBRToCBZConverter(
        create_backups=True,    # Create backup of original
        overwrite=False         # Don't overwrite existing CBZ files
    )

    # Convert a single file
    cbr_file = Path("example.cbr")  # Replace with actual file path
    if cbr_file.exists():
        success, message = converter.convert_file(cbr_file)
        if success:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")
    else:
        print(f"File not found: {cbr_file}")

def example_batch_conversion() -> None:
    """Example: Convert all CBR files in a directory."""
    print("\n=== Batch Conversion ===")

    # Initialize converter
    converter = CBRToCBZConverter(
        create_backups=False,   # Skip backups for batch operation
        overwrite=True          # Overwrite existing files
    )

    # Convert all CBR files in a directory
    directory = Path("comics")  # Replace with actual directory path
    if directory.exists():
        successful, failed, errors = converter.convert_directory(
            directory,
            recursive=True  # Search subdirectories too
        )

        print("Conversion complete:")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")

        if errors:
            print("Errors:")
            for error in errors:
                print(f"  ✗ {error}")
    else:
        print(f"Directory not found: {directory}")

def example_with_custom_settings() -> None:
    """Example: Use converter with custom settings."""
    print("\n=== Custom Settings ===")

    # Custom converter settings
    converter = CBRToCBZConverter(
        create_backups=True,
        overwrite=False
    )

    # You can also modify settings after initialization
    converter.backup_dir = "my_backups"  # Custom backup directory name

    # Example conversion
    print("Converter configured with custom backup directory: 'my_backups'")

if __name__ == "__main__":
    print("CBR to CBZ Converter - Usage Examples")
    print("=" * 50)

    example_single_file_conversion()
    example_batch_conversion()
    example_with_custom_settings()

    print("\n" + "=" * 50)
    print("Command Line Usage:")
    print("  python cbr2cbz.py file.cbr              # Convert single file")
    print("  python cbr2cbz.py directory/            # Convert all CBR in directory")
    print("  python cbr2cbz.py directory/ -r         # Convert recursively")
    print("  python cbr2cbz.py file.cbr --no-backup  # No backup")
    print("  python cbr2cbz.py file.cbr --overwrite  # Overwrite existing")
    print("  python cbr2cbz.py file.cbr --verbose    # Verbose output")

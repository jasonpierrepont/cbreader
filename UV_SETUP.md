# Comic Book Reader - UV Setup Guide

This project is now configured to work with [uv](https://docs.astral.sh/uv/), the fast Python package manager.

## Quick Start with UV

### 1. Install UV
```bash
# On Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Sync Dependencies
```bash
# Install all dependencies (including dev dependencies)
uv sync

# Install only production dependencies
uv sync --no-dev
```

### 3. Run the Application
```bash
# Run using the entry point script
uv run comic-reader

# Or run the Python module directly
uv run python comic_reader.py

# Or use the launch script
uv run python launch.py
```

### 4. Development Commands
```bash
# Run with development dependencies
uv sync
uv run python comic_reader.py

# Format code with black
uv run black comic_reader.py

# Check code with flake8
uv run flake8 comic_reader.py

# Type checking with mypy
uv run mypy comic_reader.py

# Sort imports with isort
uv run isort comic_reader.py
```

### 5. Building and Distribution
```bash
# Build the package
uv build

# Install in editable mode for development
uv pip install -e .
```

## Project Structure

```
comic-book-reader/
├── pyproject.toml          # Project configuration (uv compatible)
├── comic_reader.py         # Main application
├── launch.py              # Simple launcher
├── requirements.txt       # Legacy requirements file
├── README.md             # Project documentation
└── UV_SETUP.md           # This file
```

## Benefits of Using UV

- **Fast**: Much faster than pip for dependency resolution and installation
- **Modern**: Built with Rust, designed for modern Python workflows
- **Compatible**: Works with existing pip/poetry projects
- **Reliable**: Better dependency resolution and lock file support
- **Easy**: Simple commands for common tasks

## Migration from pip

If you were using pip before:
```bash
# Old way
pip install -r requirements.txt
python comic_reader.py

# New way with uv
uv sync
uv run comic-reader
```

## Configuration Details

The `pyproject.toml` includes:
- **Build system**: Uses hatchling for building
- **Dependencies**: PySide6, Pillow, patool
- **Dev dependencies**: black, flake8, mypy, pytest
- **Entry points**: Console and GUI scripts
- **Tool configurations**: For linting, formatting, and testing

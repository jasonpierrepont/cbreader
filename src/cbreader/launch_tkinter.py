#!/usr/bin/env python3
"""Launch script for the Tkinter version of Comic Book Reader."""

import sys
from pathlib import Path

# Add the current directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import and run the tkinter application
from cbreader.comic_reader_tkinter import main

if __name__ == "__main__":
    main()

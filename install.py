#!/usr/bin/env python3
import sys
import os

# Ensure the _config directory is in sys.path so 'bootstrap' package can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from bootstrap import main

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# src/pocket_build/__main__.py
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

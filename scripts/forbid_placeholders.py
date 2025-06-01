#!/usr/bin/env python3
"""
Script to check for forbidden placeholders in staged files.

Used in CI/CD pipeline to prevent accidental commits of temporary markers.
"""

import re
import sys
import subprocess
from pathlib import Path
from typing import List

# List of forbidden placeholders/markers
# Expand as needed
PATTERNS = [
    r"<updated>",
    r"<full content[^>]*>",
    r"current full file[^\n]*",
    r"TODO:.*PLACEHOLDER",
    r"FIXME:.*PLACEHOLDER",
]

regexes = [re.compile(p, re.IGNORECASE) for p in PATTERNS]


def get_staged_files() -> List[str]:
    """Get list of files staged for commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        # If not in git repo or no staged files, return empty list
        return []


def check_file_for_placeholders(file_path: Path) -> bool:
    """Check if file contains any forbidden placeholders."""
    # Skip binary files, deleted files, and this script itself
    if not file_path.is_file() or file_path.suffix == ".pyc":
        return False
    if file_path.name == "forbid_placeholders.py":
        # Allow placeholders inside the checking script itself
        return False

    try:
        text = file_path.read_text(errors="ignore")
    except Exception:
        # If unable to read - skip
        return False

    return any(r.search(text) for r in regexes)


def main() -> int:
    """Main function to check for placeholders in staged files."""
    staged_files = get_staged_files()

    # If no staged files (e.g., in CI), check all Python files
    if not staged_files:
        print("No staged files found, checking all Python files...")
        staged_files = [str(p) for p in Path(".").rglob("*.py") if p.is_file()]

    bad_files: List[str] = []

    for file_path_str in staged_files:
        path = Path(file_path_str)
        if check_file_for_placeholders(path):
            bad_files.append(file_path_str)

    if bad_files:
        print(f"❌ Found temporary placeholders in files: {', '.join(bad_files)}")
        print("Please remove these placeholders before committing.")
        return 1

    print("✅ No forbidden placeholders found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

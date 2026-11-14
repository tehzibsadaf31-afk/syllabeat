#!/usr/bin/env python3
"""Scan a folder for anything that looks like an API key before you publish or commit it.

    python scripts/check_secrets.py <folder>

Exit code 0 = nothing found, 1 = something suspicious was found (the files are listed,
the secret itself is NEVER printed). build_site.py runs this automatically on the finished site.
Standard library only.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

TEXT_EXT = {".html", ".htm", ".js", ".css", ".json", ".md", ".txt", ".py", ".ps1", ".sh", ".yml", ".yaml",
            ".toml", ".ini", ".cfg", ".env", ".csv", ".xml", ".svg", ".map", ""}
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
FORBIDDEN_NAMES = {".env"}  # a real .env must never be inside something you publish
ALLOWED_ENV_NAMES = {".env.example", ".env.sample"}


def scan(folder):
    root = Path(folder)
    if not root.is_dir():
        raise common.SyllaBeatError("Folder not found: %s" % root)
    live = common.load_api_key()  # also look for the user's REAL key value, if one is configured
    problems = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            rel = path.relative_to(root)
            low = name.lower()
            if low in FORBIDDEN_NAMES or (low.endswith(".env") and low not in ALLOWED_ENV_NAMES):
                problems.append((rel, "a .env file must never be published"))
                continue
            if path.suffix.lower() not in TEXT_EXT:
                continue
            try:
                if path.stat().st_size > 5_000_000:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if live and live in text:
                problems.append((rel, "contains your actual API key"))
                continue
            for pat in common.KEY_LIKE:
                if pat.search(text):
                    problems.append((rel, "contains text that looks like an API key"))
                    break
    return problems


def main():
    try:
        common.reject_key_arguments()
        if len(sys.argv) != 2:
            print(__doc__)
            sys.exit(2)
        problems = scan(sys.argv[1])
    except common.SyllaBeatError as e:
        common.fail(e)
    if problems:
        print("STOP - possible secrets found. Do NOT publish or commit until fixed:")
        for rel, why in problems:
            print("  %s  ->  %s" % (rel, why))
        sys.exit(1)
    print("OK - no keys or .env files found in %s" % sys.argv[1])


if __name__ == "__main__":
    main()

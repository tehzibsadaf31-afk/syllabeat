#!/usr/bin/env python3
"""Make a clean copy of SyllaBeat that is safe to publish (for example as a public GitHub repository).

    python scripts/export_clean_copy.py <destination-folder>             first time (folder must be new or empty)
    python scripts/export_clean_copy.py <destination-folder> --refresh   update an existing copy (keeps its .git history)

It copies only the shareable files and LEAVES OUT: your projects/ folder, any .env file (the .env.example template is kept),
the private sample/ folder, .git and caches. It then scans the copy for anything that looks like an API key and removes the
copy again if it finds one. Standard library only.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import check_secrets  # noqa: E402

ROOT = HERE.parent
SKIP_DIRS = {".git", "projects", "sample", "__pycache__", ".idea", ".vscode"}
SKIP_SUFFIX = {".pyc", ".log"}


def skip(path: Path) -> bool:
    name = path.name.lower()
    if name in {".env"} or (name.endswith(".env") and name != ".env.example"):
        return True
    if name == ".gitattributes":  # added by some Git apps; not part of SyllaBeat, and the new repository creates its own
        return True
    return path.suffix.lower() in SKIP_SUFFIX


def copy_clean(src: Path, dst: Path):
    count = 0
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel = Path(dirpath).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        for f in filenames:
            p = Path(dirpath) / f
            if skip(p):
                continue
            shutil.copy2(p, dst / rel / f)
            count += 1
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("destination")
    ap.add_argument("--refresh", action="store_true", help="replace the files of an existing copy but keep its .git folder")
    a = ap.parse_args()
    try:
        common.reject_key_arguments()
        dst = Path(a.destination).resolve()
        if ROOT in dst.parents or dst == ROOT:
            raise common.SyllaBeatError("Choose a destination OUTSIDE the SyllaBeat folder.")
        if dst.exists() and any(dst.iterdir()):
            if not a.refresh:
                raise common.SyllaBeatError("%s is not empty. Use --refresh to update an existing copy." % dst)
            for child in dst.iterdir():
                if child.name == ".git":
                    continue
                shutil.rmtree(child) if child.is_dir() else child.unlink()
        dst.mkdir(parents=True, exist_ok=True)
        n = copy_clean(ROOT, dst)
        problems = check_secrets.scan(dst)
        if problems:
            for child in dst.iterdir():
                if child.name != ".git":
                    shutil.rmtree(child) if child.is_dir() else child.unlink()
            lines = "\n".join("  %s -> %s" % (r, w) for r, w in problems)
            raise common.SyllaBeatError("The copy was removed because it looked like it contained a secret:\n" + lines)
    except common.SyllaBeatError as e:
        common.fail(e)
    print("Clean copy ready: %s  (%d files)" % (dst, n))
    print("Left out: projects/, sample/, any .env file, .git and caches. Security scan: no keys found.")
    print("Next: open that folder in GitHub Desktop (File > Add local repository) and publish it.")


if __name__ == "__main__":
    main()

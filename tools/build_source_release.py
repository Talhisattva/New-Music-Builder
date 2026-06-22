from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
}

INCLUDED_TOP_LEVEL_FILES = {
    ".gitignore",
    "Launch New Music Builder.bat",
    "main.py",
    "README.md",
    "requirements.txt",
    "requirements-packaging.txt",
    "NewMusicBuilder.spec",
}

INCLUDED_TOP_LEVEL_DIRS = {
    "assets",
    "docs",
    "src",
    "tests",
    "tools",
}


def iter_source_release_paths(repo_root: Path) -> list[Path]:
    paths: list[Path] = []

    for name in sorted(INCLUDED_TOP_LEVEL_FILES):
        candidate = repo_root / name
        if candidate.exists() and candidate.is_file():
            paths.append(candidate)

    for name in sorted(INCLUDED_TOP_LEVEL_DIRS):
        root = repo_root / name
        if not root.exists() or not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue
            if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            paths.append(path)

    return paths


def build_source_release(repo_root: Path, output_zip: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    with ZipFile(output_zip, "w", compression=ZIP_DEFLATED) as archive:
        for path in iter_source_release_paths(repo_root):
            archive.write(path, arcname=path.relative_to(repo_root))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_zip = Path(args.output).resolve()
    build_source_release(repo_root, output_zip)
    print(output_zip)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

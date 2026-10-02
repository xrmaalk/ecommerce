#!/usr/bin/env python3
"""Build and package the storefront and Organic Archives distributions."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class PackagingError(RuntimeError):
    pass


@dataclass(frozen=True)
class Distribution:
    source_name: str
    archive_name: str


DISTRIBUTIONS = (
    Distribution("dist", "dist.zip"),
    Distribution("dist-archives", "dist-archives.zip"),
)


def repository_root(script_path: Path) -> Path:
    root = script_path.resolve().parents[1]
    if not (root / ".git").exists() or not (root / "frontend" / "package.json").is_file():
        raise PackagingError(f"Could not identify the project root at {root}.")
    return root


def run_frontend_build(repository: Path) -> None:
    npm = shutil.which("npm")
    if npm is None:
        raise PackagingError("npm is required to build the frontend distributions.")
    result = subprocess.run(
        (npm, "--prefix", str(repository / "frontend"), "run", "build:all"),
        cwd=repository,
        check=False,
    )
    if result.returncode:
        raise PackagingError("The frontend build failed; existing ZIPs were not replaced.")


def distribution_files(source: Path) -> list[Path]:
    if not source.is_dir():
        raise PackagingError(f"Missing distribution directory: {source}")
    files = sorted(
        (path for path in source.rglob("*") if path.is_file()),
        key=lambda path: (
            path.relative_to(source).as_posix() == "index.html",
            path.relative_to(source).as_posix(),
        ),
    )
    if not files:
        raise PackagingError(f"No files found in {source}.")
    relative_names = {path.relative_to(source).as_posix() for path in files}
    for required_name in (".htaccess", "index.html"):
        if required_name not in relative_names:
            raise PackagingError(f"{source.name} is missing required file {required_name}.")
    for path in files:
        if path.is_symlink():
            raise PackagingError(f"Refusing to package symbolic link: {path}")
        try:
            path.resolve().relative_to(source.resolve())
        except ValueError as exc:
            raise PackagingError(
                f"Distribution file resolves outside {source}: {path}"
            ) from exc
    validate_index((source / "index.html").read_bytes(), relative_names, source.name)
    return files


class IndexResources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources: list[str] = []
        self.module_scripts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in ("script", "img", "source", "video", "audio"):
            url = attributes.get("src")
            if url:
                self.resources.append(url)
                if tag == "script" and attributes.get("type") == "module":
                    self.module_scripts.append(url)
        if tag == "link" and set((attributes.get("rel") or "").split()) & {
            "stylesheet", "modulepreload", "preload", "icon", "apple-touch-icon",
        }:
            if attributes.get("href"):
                self.resources.append(attributes["href"])


def local_resource_name(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path).removeprefix("/")
    if not path:
        return None
    if "\\" in path or any(part in (".", "..") for part in path.split("/")):
        raise PackagingError(f"Unsafe resource path in index.html: {url}")
    return path


def validate_index(content: bytes, available_files: set[str], label: str) -> None:
    """Validate Vite's generated document; never substitute a saved asset hash."""
    try:
        html = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PackagingError(f"{label}: index.html is not valid UTF-8.") from error
    parser = IndexResources()
    parser.feed(html)
    modules = [local_resource_name(url) for url in parser.module_scripts]
    if not any(name and name.startswith("assets/") and name.endswith(".js") for name in modules):
        raise PackagingError(f"{label}: index.html does not reference a built Vite entry script.")
    for url in parser.resources:
        name = local_resource_name(url)
        if name is not None and name not in available_files:
            raise PackagingError(f"{label}: index.html references missing file {url}.")


def prepare_archive(source: Path, output: Path, files: list[Path]) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{output.stem}-",
        suffix=".tmp",
        dir=output.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for file_path in files:
                relative_path = file_path.relative_to(source).as_posix()
                # Update-only ZIP extractors must see the rebuilt entry document
                # as new. A fixed 1980 timestamp can leave an old index deployed.
                timestamp = (
                    datetime.fromtimestamp(file_path.stat().st_mtime).timetuple()[:6]
                    if relative_path == "index.html" else FIXED_ZIP_TIME
                )
                info = zipfile.ZipInfo(relative_path, timestamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = stat.S_IMODE(file_path.stat().st_mode) << 16
                archive.writestr(info, file_path.read_bytes(), compresslevel=9)

        with zipfile.ZipFile(temporary_path) as archive:
            expected_names = [path.relative_to(source).as_posix() for path in files]
            if archive.namelist() != expected_names:
                raise PackagingError(
                    f"Archive validation failed for {output.name}: file listing changed."
                )
            bad_member = archive.testzip()
            if bad_member:
                raise PackagingError(
                    f"Archive validation failed for {output.name} at {bad_member}."
                )
            validate_index(archive.read("index.html"), set(archive.namelist()), output.name)
            for required_name in ("index.html", ".htaccess"):
                if archive.read(required_name) != (source / required_name).read_bytes():
                    raise PackagingError(f"{output.name}: {required_name} changed during packaging.")
        return temporary_path
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build and create dist.zip and dist-archives.zip with each site's "
            "deployable contents at the ZIP root."
        )
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Deprecated: accepted for compatibility, but a fresh build always runs.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    prepared: list[tuple[Distribution, Path, Path, list[Path]]] = []
    try:
        repository = repository_root(Path(__file__))
        if arguments.skip_build:
            print("warning: --skip-build is ignored; both frontends are always rebuilt.", file=sys.stderr)
        run_frontend_build(repository)

        frontend = repository / "frontend"
        for distribution in DISTRIBUTIONS:
            source = frontend / distribution.source_name
            output = repository / distribution.archive_name
            files = distribution_files(source)
            temporary_path = prepare_archive(source, output, files)
            prepared.append((distribution, temporary_path, output, files))

        # Import lazily: seo_shells also reuses this module's asset validation.
        if __package__:
            from .seo_shells import write_shells
        else:
            from seo_shells import write_shells
        write_shells(repository)

        for _, temporary_path, output, _ in prepared:
            os.replace(temporary_path, output)

        for distribution, _, output, files in prepared:
            size_kib = output.stat().st_size / 1024
            print(
                f"Created {distribution.archive_name} | Files: {len(files)} | "
                f"Size: {size_kib:.1f} KiB"
            )
            print(f"SHA-256: {sha256(output)}")
    except (OSError, ValueError, PackagingError) as error:
        for _, temporary_path, _, _ in prepared:
            temporary_path.unlink(missing_ok=True)
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

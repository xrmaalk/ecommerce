#!/usr/bin/env python3
"""Create a clean backend deployment ZIP using the repository's Git ignore rules."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
DEFAULT_OUTPUT = "backend.zip"


class PackagingError(RuntimeError):
    pass


def run_git(
    repository: Path,
    *arguments: str,
    input_text: str | None = None,
    accepted_codes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ("git", "-c", "core.quotepath=false", *arguments),
            cwd=repository,
            input=input_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            check=False,
        )
    except FileNotFoundError as exc:
        raise PackagingError("Git is required to apply .gitignore rules.") from exc
    if result.returncode not in accepted_codes:
        detail = result.stderr.strip() or result.stdout.strip() or "Git command failed."
        raise PackagingError(detail)
    return result


def repository_root(script_path: Path) -> Path:
    expected_root = script_path.resolve().parents[1]
    result = run_git(expected_root, "rev-parse", "--show-toplevel")
    discovered_root = Path(result.stdout.strip()).resolve()
    if discovered_root != expected_root:
        raise PackagingError(
            f"Expected repository root {expected_root}, but Git reported {discovered_root}."
        )
    return discovered_root


def backend_files(repository: Path) -> list[Path]:
    listed = run_git(
        repository,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
        "backend",
    )
    candidates = sorted(
        {
            Path(name)
            for name in listed.stdout.split("\0")
            if name and Path(name).parts[:1] == ("backend",)
        },
        key=lambda path: path.as_posix(),
    )
    if not candidates:
        raise PackagingError("No non-ignored backend files were found.")

    ignored_result = run_git(
        repository,
        "check-ignore",
        "--no-index",
        "-z",
        "--stdin",
        input_text="\0".join(path.as_posix() for path in candidates) + "\0",
        accepted_codes=(0, 1),
    )
    ignored = {
        Path(name)
        for name in ignored_result.stdout.split("\0")
        if name
    }

    backend_root = (repository / "backend").resolve()
    files: list[Path] = []
    for relative_path in candidates:
        if relative_path in ignored:
            continue
        source = repository / relative_path
        if not source.exists():
            continue
        if source.is_symlink():
            raise PackagingError(f"Refusing to package symbolic link: {relative_path}")
        if not source.is_file():
            continue
        try:
            source.resolve().relative_to(backend_root)
        except ValueError as exc:
            raise PackagingError(
                f"Backend file resolves outside the backend directory: {relative_path}"
            ) from exc
        files.append(relative_path)
    if not files:
        raise PackagingError("No packageable backend files were found.")
    return files


def resolve_output(repository: Path, value: str) -> Path:
    output = Path(value)
    if not output.is_absolute():
        output = repository / output
    output = output.resolve()
    try:
        output.relative_to(repository)
    except ValueError as exc:
        raise PackagingError("The output ZIP must be inside the repository.") from exc
    if output.suffix.lower() != ".zip":
        raise PackagingError("The output file must have a .zip extension.")
    return output


def write_archive(repository: Path, output: Path, files: list[Path]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.stem}-",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for relative_path in files:
                source = repository / relative_path
                info = zipfile.ZipInfo(relative_path.as_posix(), FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                permissions = stat.S_IMODE(source.stat().st_mode)
                info.external_attr = permissions << 16
                archive.writestr(info, source.read_bytes(), compresslevel=9)

        with zipfile.ZipFile(temporary_path) as archive:
            archived_names = archive.namelist()
            expected_names = [path.as_posix() for path in files]
            if archived_names != expected_names:
                raise PackagingError("Archive validation failed: file listing changed.")
            bad_member = archive.testzip()
            if bad_member:
                raise PackagingError(f"Archive validation failed at {bad_member}.")

        os.replace(temporary_path, output)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Package tracked and untracked non-ignored backend source files. "
            "Git applies the repository's .gitignore rules."
        )
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"ZIP path relative to the repository root (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace the output ZIP when it already exists.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        repository = repository_root(Path(__file__))
        output = resolve_output(repository, arguments.output)
        default_output = (repository / DEFAULT_OUTPUT).resolve()
        if output.exists() and output != default_output and not arguments.force:
            raise PackagingError(
                f"{output.name} already exists. Use --force to replace it."
            )
        files = backend_files(repository)
        write_archive(repository, output, files)
    except PackagingError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    size_kib = output.stat().st_size / 1024
    print(f"Created {output.relative_to(repository)}")
    print(f"Files: {len(files)} | Size: {size_kib:.1f} KiB")
    print(f"SHA-256: {sha256(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

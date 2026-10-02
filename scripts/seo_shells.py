"""Bundle validated Vite HTML shells with Django, never hard-code hashed assets."""
import os
from pathlib import Path

try:
    from .package_frontends import distribution_files
except ImportError:
    from package_frontends import distribution_files

SHELLS = {"storefront": "dist", "archives": "dist-archives"}


def built_shells(repository):
    result = {}
    for site, distribution in SHELLS.items():
        source = repository / "frontend" / distribution
        files = distribution_files(source)
        content = (source / "index.html").read_bytes()
        for marker in (b"<!-- page-metadata:start -->", b"<!-- page-metadata:end -->"):
            if content.count(marker) != 1:
                raise ValueError(f"{distribution}: missing/duplicate SEO metadata marker; rebuild both frontends")
        result[site] = content
    return result


def write_shells(repository):
    # Validate both before replacing either. This directory contains generated HTML only.
    shells = built_shells(repository)
    directory = repository / "backend" / "site_shells"
    directory.resolve().relative_to((repository / "backend").resolve())
    directory.mkdir(parents=True, exist_ok=True)
    for site, content in shells.items():
        temporary = directory / f".{site}.tmp"
        temporary.write_bytes(content)
        os.replace(temporary, directory / f"{site}.html")


def packaged_shells(repository):
    expected = built_shells(repository)
    files = []
    for site, content in expected.items():
        relative = Path("backend") / "site_shells" / f"{site}.html"
        source = repository / relative
        source.resolve().relative_to((repository / "backend").resolve())
        if source.is_symlink() or source.read_bytes() != content:
            raise ValueError("SEO shells do not match frontend builds; run scripts/package_frontends.py first")
        files.append(relative)
    return files

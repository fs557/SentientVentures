"""Cross-platform integrity helpers for deterministic fixture artifacts."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path


TEXT_FIXTURE_SUFFIXES = frozenset({
    ".csv",
    ".json",
    ".md",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
})


def fixture_integrity_bytes(path: Path) -> bytes:
    """Return canonical bytes while preserving byte-exact checks for binaries."""
    payload = path.read_bytes()
    if path.suffix.lower() not in TEXT_FIXTURE_SUFFIXES:
        return payload
    return payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def fixture_sha256(path: Path) -> str:
    """Hash text fixtures independently of LF/CRLF and binaries byte-for-byte."""
    return sha256(fixture_integrity_bytes(path)).hexdigest()

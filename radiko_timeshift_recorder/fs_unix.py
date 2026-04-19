"""Unix filesystem helpers."""

import os
from pathlib import Path

# Permission + setuid/setgid/sticky bits (12 bits), as accepted by chmod(2) on Unix.
_MAX_MODE = 0o7777


def parse_unix_mode_string(value: str) -> int:
    """
    Parse a non-empty string of octal digits (e.g. ``644``, ``0755``, ``2775``).

    Rejects values above ``0o7777`` (e.g. ``77777``) so only the usual chmod
    bit range is accepted.
    """
    v = value.strip()
    if not v:
        raise ValueError("Mode string is empty.")
    if not all(c in "01234567" for c in v):
        raise ValueError(
            f"Mode must be octal digits only (e.g. 644 or 0755), got {value!r}"
        )
    mode = int(v, 8)
    if mode > _MAX_MODE:
        raise ValueError(
            f"Mode must be at most {_MAX_MODE:o} (12 permission bits), got {value!r}"
        )
    return mode


def chown_group_under_ancestor(ancestor: Path, path: Path, gid: int) -> None:
    """
    Set group ``gid`` on ``path`` and on each directory strictly between ``ancestor`` and ``path``.

    ``ancestor`` itself is not modified. Directories from the first segment under ``ancestor``
    through ``path``'s parent are updated, then ``path``.

    ``path`` must resolve under ``ancestor``; otherwise raises ``ValueError``.
    """
    parent = path.parent
    try:
        rel = parent.resolve().relative_to(ancestor.resolve())
    except ValueError as e:
        raise ValueError(
            f"path must be under ancestor (path={path!r}, ancestor={ancestor!r})"
        ) from e
    current = ancestor
    for part in rel.parts:
        current = current / part
        os.chown(current, -1, gid)
    os.chown(path, -1, gid)

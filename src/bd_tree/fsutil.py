"""Filesystem safety: the per-store write lock and atomic node publication.

A store stays data-only: the lock file lives in the system temp directory,
keyed by the store's real path, so no lock or state file enters the store or
git.  The kernel releases the lock if a holder dies, so there is nothing to
clean up after a crash.  Node files are published with a temp file plus a
rename/link, so readers never observe a truncated document.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .errors import BreakdownError

try:  # POSIX
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]

try:  # Windows
    import msvcrt
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None  # type: ignore[assignment]


def lock_path(root: str | Path) -> Path:
    """The lock file for ``root``, outside the store."""
    resolved = os.path.realpath(root)
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:32]
    return Path(tempfile.gettempdir()) / f"bd_tree-{digest}.lock"


_held = threading.local()


def _held_paths() -> set[str]:
    paths = getattr(_held, "paths", None)
    if paths is None:
        paths = _held.paths = set()
    return paths


@contextmanager
def store_lock(root: str | Path) -> Iterator[None]:
    """Hold an exclusive inter-process lock on ``root`` for one write.

    Writers on the same store serialize; readers take no lock and still see
    either the old or the new file because writers publish atomically.  The
    lock is reentrant within a thread, so a writer may call another writer.
    """
    path = lock_path(root)
    held = _held_paths()
    if str(path) in held:
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        elif msvcrt is not None:  # pragma: no cover - Windows
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    continue
        held.add(str(path))
        try:
            yield
        finally:
            held.discard(str(path))
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
        elif msvcrt is not None:  # pragma: no cover - Windows
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    finally:
        os.close(fd)


def _default_mode() -> int:
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


_DEFAULT_FILE_MODE = _default_mode()


def _target_mode(path: Path) -> int:
    try:
        return path.stat().st_mode & 0o777
    except FileNotFoundError:
        return _DEFAULT_FILE_MODE


def atomic_write(path: Path, text: str) -> None:
    """Replace ``path`` atomically, keeping its mode; readers see old or new."""
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        os.fchmod(fd, _target_mode(path))
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def atomic_copy(source: Path, target: Path) -> None:
    """Copy ``source`` to ``target`` atomically, keeping the default mode."""
    fd, tmp_name = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        os.chmod(tmp, _DEFAULT_FILE_MODE)
        shutil.copyfile(source, tmp)
        os.replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def publish_new(path: Path, text: str) -> None:
    """Create ``path`` with ``text``; never overwrite an existing node."""
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        os.fchmod(fd, _DEFAULT_FILE_MODE)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise BreakdownError(f"node {path.stem} already exists at {path}") from None
        except OSError:
            # No hard links on this filesystem; the store lock already
            # serialized us, so an atomic replace cannot clobber a sibling.
            os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)

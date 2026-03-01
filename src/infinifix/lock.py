from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def execution_lock(name: str = "infinifix.lock") -> Iterator[None]:
    lock_path = _lock_path(name)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import fcntl  # type: ignore
    except ImportError:
        # Non-POSIX fallback (dev/test hosts). No strict lock available.
        yield
        return

    with lock_path.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f"Another InfiniFix session is already running: {lock_path}") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _lock_path(name: str) -> Path:
    preferred = Path("/var/lib/infinifix") / name
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        return preferred
    except PermissionError:
        fallback = Path(tempfile.gettempdir()) / "infinifix" / name
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback

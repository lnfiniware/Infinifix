from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    dry_run: bool = False


class CommandRunner:
    def __init__(self, dry_run: bool = False, log_path: Path | None = None) -> None:
        self.dry_run = dry_run
        self.log_path = log_path or self._default_log_path()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _default_log_path(self) -> Path:
        preferred = Path("/var/log/infinifix/infinifix.log")
        try:
            preferred.parent.mkdir(parents=True, exist_ok=True)
            if not preferred.exists():
                preferred.touch(exist_ok=True)
            return preferred
        except PermissionError:
            fallback = Path(tempfile.gettempdir()) / "infinifix" / "infinifix.log"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            return fallback

    def _log(self, result: CommandResult) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        chunk = [
            f"[{timestamp}] cmd={result.command}",
            f"rc={result.returncode} duration={result.duration_s:.3f}s dry_run={result.dry_run}",
            "--- stdout ---",
            result.stdout.strip(),
            "--- stderr ---",
            result.stderr.strip(),
            "",
        ]
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(chunk))

    def run(
        self,
        command: Sequence[str] | str,
        *,
        check: bool = False,
        as_user: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        rendered = command if isinstance(command, str) else shlex.join(command)
        exec_command: Sequence[str] | str = command
        shell = isinstance(command, str)

        if as_user and self._geteuid() == 0 and as_user != "root":
            exec_command = ["sudo", "-u", as_user, "bash", "-lc", rendered]
            shell = False

        start = time.monotonic()
        if self.dry_run:
            result = CommandResult(
                command=rendered,
                returncode=0,
                stdout="",
                stderr="[dry-run] skipped",
                duration_s=time.monotonic() - start,
                dry_run=True,
            )
            self._log(result)
            return result

        try:
            completed = subprocess.run(
                exec_command,
                shell=shell,
                text=True,
                capture_output=True,
                env=dict(os.environ, **(env or {})),
                check=False,
            )
            result = CommandResult(
                command=rendered,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_s=time.monotonic() - start,
                dry_run=False,
            )
        except FileNotFoundError as exc:
            result = CommandResult(
                command=rendered,
                returncode=127,
                stdout="",
                stderr=str(exc),
                duration_s=time.monotonic() - start,
                dry_run=False,
            )

        self._log(result)
        if check and result.returncode != 0:
            raise RuntimeError(f"Command failed ({result.returncode}): {rendered}\n{result.stderr.strip()}")
        return result

    def command_exists(self, command: str) -> bool:
        result = self.run(["bash", "-lc", f"command -v {shlex.quote(command)} >/dev/null 2>&1"])
        return result.returncode == 0

    @staticmethod
    def is_root() -> bool:
        return CommandRunner._geteuid() == 0

    @staticmethod
    def _geteuid() -> int:
        geteuid = getattr(os, "geteuid", None)
        if geteuid is None:
            return -1
        return int(geteuid())

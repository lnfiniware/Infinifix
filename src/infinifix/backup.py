from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class BackupManager:
    def __init__(self, root: Path | None = None, dry_run: bool = False) -> None:
        self.root = root or Path("/var/lib/infinifix/backups")
        self.dry_run = dry_run
        self.session_dir: Path | None = None
        self._manifest: List[Dict[str, Any]] = []

    def _resolve_root(self) -> Path:
        if self.root.exists() or self.dry_run:
            return self.root
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            return self.root
        except PermissionError:
            fallback = Path(tempfile.gettempdir()) / "infinifix" / "backups"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    def start_session(self) -> Path:
        resolved = self._resolve_root()
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.session_dir = resolved / timestamp
        if not self.dry_run:
            self.session_dir.mkdir(parents=True, exist_ok=True)
        self._manifest = []
        self._write_manifest()
        return self.session_dir

    def _require_session(self) -> Path:
        if self.session_dir is None:
            return self.start_session()
        return self.session_dir

    def _write_manifest(self) -> None:
        if self.dry_run:
            return
        session = self._require_session()
        manifest_path = session / "manifest.json"
        manifest_path.write_text(json.dumps(self._manifest, indent=2), encoding="utf-8")

    def backup_file(self, target: Path) -> None:
        session = self._require_session()
        target = Path(target)

        if target.exists():
            relative = target.as_posix().lstrip("/").replace("/", "__")
            backup_path = session / "files" / relative
            if not self.dry_run:
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup_path)
            self._manifest.append(
                {
                    "type": "file",
                    "original": str(target),
                    "backup": str(backup_path),
                }
            )
        else:
            self._manifest.append({"type": "created", "original": str(target)})
        self._write_manifest()

    def write_text(self, target: Path, content: str, mode: int = 0o644) -> None:
        target = Path(target)
        self.backup_file(target)
        if self.dry_run:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        target.chmod(mode)

    def write_executable(self, target: Path, content: str) -> None:
        self.write_text(target, content, mode=0o755)

    def latest_session(self) -> Path | None:
        root = self._resolve_root()
        if not root.exists():
            return None
        candidates = [item for item in root.iterdir() if item.is_dir()]
        if not candidates:
            return None
        return sorted(candidates)[-1]

    def restore_session(self, session: Path) -> List[str]:
        session = Path(session)
        manifest_path = session / "manifest.json"
        if not manifest_path.exists():
            return []

        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        restored: List[str] = []
        for entry in reversed(entries):
            original = Path(entry["original"])
            if entry["type"] == "file":
                backup = Path(entry["backup"])
                if backup.exists() and not self.dry_run:
                    original.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, original)
                restored.append(str(original))
            elif entry["type"] == "created":
                if original.exists() and not self.dry_run:
                    original.unlink(missing_ok=True)
                restored.append(str(original))
        return restored


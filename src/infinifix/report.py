from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .distro import DistroInfo
from .privacy import sanitize_obj
from .runner import CommandRunner


REPORT_ROOT = Path("/var/log/infinifix/reports")


def _resolve_report_root() -> Path:
    try:
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        return REPORT_ROOT
    except PermissionError:
        fallback = Path(tempfile.gettempdir()) / "infinifix" / "reports"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _write_command_output(runner: CommandRunner, target: Path, command: list[str] | str) -> None:
    result = runner.run(command)
    body = {
        "command": result.command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    target.write_text(json.dumps(sanitize_obj(body), indent=2), encoding="utf-8")


def generate_report(
    runner: CommandRunner,
    probe_data: Dict[str, Any],
    distro: DistroInfo,
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    staging = Path(tempfile.mkdtemp(prefix="infinifix-report-"))
    command_dir = staging / "commands"
    command_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "timestamp": timestamp,
        "distro": {
            "id": distro.distro_id,
            "family": distro.family,
            "pretty_name": distro.pretty_name,
            "package_manager": distro.package_manager,
        },
        "probe": probe_data,
    }
    (staging / "metadata.json").write_text(json.dumps(sanitize_obj(metadata), indent=2), encoding="utf-8")

    commands: dict[str, list[str] | str] = {
        "uname.json": ["uname", "-a"],
        "os_release.json": ["bash", "-lc", "cat /etc/os-release"],
        "lsmod.json": ["lsmod"],
        "lspci.json": ["bash", "-lc", "lspci -nn"],
        "lsusb.json": ["bash", "-lc", "lsusb"],
        "aplay.json": ["bash", "-lc", "aplay -l"],
        "pactl_info.json": ["bash", "-lc", "pactl info"],
        "pactl_sinks.json": ["bash", "-lc", "pactl list short sinks"],
        "fwupdmgr_devices.json": ["bash", "-lc", "fwupdmgr get-devices"],
        "journal_audio.json": ["bash", "-lc", "journalctl -b --no-pager | grep -Ei 'sof|pipewire|wireplumber|huawei-wmi'"],
    }
    for file_name, command in commands.items():
        _write_command_output(runner, command_dir / file_name, command)

    log_copy_targets = [
        Path("/var/log/infinifix/infinifix.log"),
        Path("/var/lib/infinifix/state.json"),
    ]
    copied_dir = staging / "copied"
    copied_dir.mkdir(parents=True, exist_ok=True)
    for target in log_copy_targets:
        if target.exists():
            shutil.copy2(target, copied_dir / target.name)

    report_root = _resolve_report_root()
    report_path = report_root / f"{timestamp}.tar.gz"
    with tarfile.open(report_path, "w:gz") as archive:
        archive.add(staging, arcname=f"infinifix-report-{timestamp}")
    shutil.rmtree(staging, ignore_errors=True)
    return report_path

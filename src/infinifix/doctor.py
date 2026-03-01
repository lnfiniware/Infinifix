from __future__ import annotations

import importlib
import json
import os
import platform
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from rich.console import Console

from .backup import BackupManager
from .distro import DistroInfo, detect_distro
from .paths import probe_candidates
from .report import generate_report
from .runner import CommandRunner
from .ui import actions_table, line, results_table, summary_table

MODULE_ORDER = [
    "sanity_checks",
    "firmware_fwupd",
    "audio_sof",
    "pipewire_wireplumber",
    "huawei_wmi",
    "grub_and_initramfs",
]


@dataclass
class DoctorContext:
    console: Console
    runner: CommandRunner
    backup: BackupManager
    distro: DistroInfo
    probe: Dict[str, Any]
    dry_run: bool
    include_advanced: bool
    target_user: str = field(default_factory=lambda: os.getenv("SUDO_USER") or os.getenv("USER") or "root")
    runtime: Dict[str, Any] = field(default_factory=dict)
    state_root: Path = Path("/var/lib/infinifix")


def _state_path() -> Path:
    preferred = Path("/var/lib/infinifix/state.json")
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        return preferred
    except PermissionError:
        fallback = Path(tempfile.gettempdir()) / "infinifix" / "state.json"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback


def load_probe(runner: CommandRunner) -> Dict[str, Any]:
    for candidate in probe_candidates():
        if candidate.exists() and candidate.is_file():
            result = runner.run([str(candidate)])
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    continue

    # Fallback when probe helper is not available.
    dmi_root = Path("/sys/class/dmi/id")
    return {
        "dmi_vendor": (dmi_root / "sys_vendor").read_text(encoding="utf-8").strip()
        if (dmi_root / "sys_vendor").exists()
        else "unknown",
        "dmi_product_name": (dmi_root / "product_name").read_text(encoding="utf-8").strip()
        if (dmi_root / "product_name").exists()
        else "unknown",
        "kernel": platform.release(),
        "lspci": runner.run(["bash", "-lc", "lspci"]).stdout.splitlines(),
        "lsusb": runner.run(["bash", "-lc", "lsusb"]).stdout.splitlines(),
    }


def build_context(console: Console, *, dry_run: bool = False, include_advanced: bool = False) -> DoctorContext:
    runner = CommandRunner(dry_run=dry_run)
    backup = BackupManager(dry_run=dry_run)
    distro = detect_distro()
    probe = load_probe(runner)
    return DoctorContext(
        console=console,
        runner=runner,
        backup=backup,
        distro=distro,
        probe=probe,
        dry_run=dry_run,
        include_advanced=include_advanced,
    )


def _load_module(module_name: str):
    return importlib.import_module(f"infinifix.modules.{module_name}")


def collect_plan(ctx: DoctorContext) -> Dict[str, Dict[str, Any]]:
    plans: Dict[str, Dict[str, Any]] = {}
    for module_name in MODULE_ORDER:
        module = _load_module(module_name)
        detected = module.detect(ctx)
        actions = module.plan(ctx, detected)
        for action in actions:
            action["module"] = module_name
            action.setdefault("safe", True)
            action.setdefault("advanced", False)
        plans[module_name] = {"module": module, "detect": detected, "actions": actions}
    return plans


def flatten_actions(plans: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_actions: List[Dict[str, Any]] = []
    for module_data in plans.values():
        all_actions.extend(module_data["actions"])
    return all_actions


def filter_actions(actions: List[Dict[str, Any]], include_advanced: bool) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    for action in actions:
        if action.get("advanced", False):
            if include_advanced:
                selected.append(action)
            continue
        if action.get("safe", True):
            selected.append(action)
    return selected


def build_summary(ctx: DoctorContext, plans: Dict[str, Dict[str, Any]], selected_actions: List[Dict[str, Any]]) -> Dict[str, str]:
    sanity = plans["sanity_checks"]["detect"]
    firmware = plans["firmware_fwupd"]["detect"]
    pipewire = plans["pipewire_wireplumber"]["detect"]
    wmi = plans["huawei_wmi"]["detect"]

    model = " ".join(
        [
            str(ctx.probe.get("dmi_vendor", "")).strip(),
            str(ctx.probe.get("dmi_product_name", "")).strip(),
        ]
    ).strip()
    model = model or "unknown"

    return {
        "Detected distro / pkg manager": f"{ctx.distro.family} / {ctx.distro.package_manager}",
        "Huawei model (DMI)": model,
        "Kernel version": str(ctx.probe.get("kernel", platform.release())),
        "Secure Boot": "enabled" if sanity.get("secure_boot_enabled") else "disabled-or-unknown",
        "Audio stack": "PipeWire+WirePlumber"
        if pipewire.get("pipewire_installed") and pipewire.get("wireplumber_installed")
        else "missing pieces",
        "WMI support status": "present" if wmi.get("wmi_present") else "missing",
        "Firmware updates": "available"
        if firmware.get("updates_available")
        else "none-or-unknown",
        "Actions planned": str(len(selected_actions)),
    }


def _save_state(payload: Dict[str, Any]) -> None:
    path = _state_path()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_state() -> Dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def apply_selected_actions(
    ctx: DoctorContext,
    plans: Dict[str, Dict[str, Any]],
    *,
    include_advanced: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Path | None]:
    if not ctx.runner.is_root() and not ctx.dry_run:
        raise PermissionError("Need root privileges for apply mode.")

    session: Path | None = None
    if not ctx.dry_run:
        session = ctx.backup.start_session()

    apply_results: List[Dict[str, Any]] = []
    verify_results: List[Dict[str, Any]] = []
    for module_name in MODULE_ORDER:
        module_data = plans[module_name]
        module = module_data["module"]
        actions = filter_actions(module_data["actions"], include_advanced=include_advanced)
        if not actions:
            continue
        for row in module.apply(ctx, actions):
            row["module"] = module_name
            apply_results.append(row)

    for module_name in MODULE_ORDER:
        module_data = plans[module_name]
        module = module_data["module"]
        verify = module.verify(ctx, module_data["detect"])
        verify_results.append(
            {
                "module": module_name,
                "id": "verify",
                "status": "ok" if verify.get("ok", False) else "warn",
                "message": verify.get("message", ""),
            }
        )

    state_payload = {
        "timestamp": datetime.now().isoformat(),
        "mode": "apply-all" if include_advanced else "apply-safe",
        "dry_run": ctx.dry_run,
        "backup_session": str(session) if session else None,
        "results": apply_results,
        "verify": verify_results,
    }
    _save_state(state_payload)
    return apply_results, verify_results, session


def revert_latest(ctx: DoctorContext) -> List[Dict[str, Any]]:
    if not ctx.runner.is_root() and not ctx.dry_run:
        raise PermissionError("Need root privileges for revert mode.")

    session = ctx.backup.latest_session()
    if session is None:
        return [{"module": "backup", "id": "restore", "status": "skip", "message": "No backup session found"}]

    restored_paths = ctx.backup.restore_session(session)
    rollback_rows: List[Dict[str, Any]] = [
        {"module": "backup", "id": "restore", "status": "ok", "message": f"Restored {len(restored_paths)} paths"}
    ]
    for module_name in MODULE_ORDER:
        module = _load_module(module_name)
        for row in module.rollback(ctx, session):
            row["module"] = module_name
            rollback_rows.append(row)

    _save_state(
        {
            "timestamp": datetime.now().isoformat(),
            "mode": "revert",
            "dry_run": ctx.dry_run,
            "backup_session": str(session),
            "results": rollback_rows,
        }
    )
    return rollback_rows


def show_status(ctx: DoctorContext) -> None:
    state = load_state()
    if not state:
        line(ctx.console, "No state found yet. Run doctor/apply first.", style="warn")
        return
    summary = {
        "Last run": state.get("timestamp", "unknown"),
        "Last mode": state.get("mode", "unknown"),
        "Dry-run": str(state.get("dry_run", False)),
        "Backup session": str(state.get("backup_session", "n/a")),
    }
    summary_table(ctx.console, summary)
    if state.get("results"):
        results_table(ctx.console, "Last Results", state["results"])


def run_report(ctx: DoctorContext) -> Path:
    return generate_report(ctx.runner, ctx.probe, ctx.distro)


def run_doctor_preview(ctx: DoctorContext) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]]:
    plans = collect_plan(ctx)
    selected = filter_actions(flatten_actions(plans), include_advanced=ctx.include_advanced)
    summary = build_summary(ctx, plans, selected)
    summary_table(ctx.console, summary)
    actions_table(ctx.console, selected)
    return plans, selected, summary

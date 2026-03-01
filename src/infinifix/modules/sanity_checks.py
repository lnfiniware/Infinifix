from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from infinifix.distro import install_packages_command, package_installed_command, resolve_package


def _secure_boot_enabled() -> bool:
    efivar_dir = Path("/sys/firmware/efi/efivars")
    if not efivar_dir.exists():
        return False
    candidates = list(efivar_dir.glob("SecureBoot-*"))
    if not candidates:
        return False
    try:
        raw = candidates[0].read_bytes()
    except OSError:
        return False
    # EFI var payload starts after 4-byte attributes.
    return len(raw) > 4 and raw[4] == 1


def detect(ctx) -> Dict[str, Any]:
    pkg = resolve_package("linux-firmware", ctx.distro.family)
    installed = False
    if pkg:
        installed = ctx.runner.run(package_installed_command(ctx.distro, pkg)).returncode == 0
    secure_boot = _secure_boot_enabled()
    ctx.runtime["secure_boot"] = secure_boot
    return {
        "linux_firmware_package": pkg,
        "linux_firmware_installed": installed,
        "secure_boot_enabled": secure_boot,
    }


def plan(ctx, detected: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    if detected.get("linux_firmware_package") and not detected.get("linux_firmware_installed"):
        actions.append(
            {
                "id": "install_linux_firmware",
                "description": f"install {detected['linux_firmware_package']}",
                "safe": True,
                "advanced": False,
            }
        )
    return actions


def apply(ctx, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for action in actions:
        if action["id"] == "install_linux_firmware":
            pkg = resolve_package("linux-firmware", ctx.distro.family)
            if not pkg:
                rows.append({"id": action["id"], "status": "skip", "message": "Unsupported distro package map"})
                continue
            ok = True
            for cmd in install_packages_command(ctx.distro, [pkg], refresh=True):
                result = ctx.runner.run(cmd)
                if result.returncode != 0:
                    ok = False
                    rows.append({"id": action["id"], "status": "fail", "message": result.stderr.strip()[:160]})
                    break
            if ok:
                rows.append({"id": action["id"], "status": "ok", "message": f"Installed {pkg}"})
    return rows


def verify(ctx, detected: Dict[str, Any]) -> Dict[str, Any]:
    pkg = detected.get("linux_firmware_package")
    if not pkg:
        return {"ok": True, "message": "No firmware package mapping for this distro"}
    result = ctx.runner.run(package_installed_command(ctx.distro, pkg))
    return {
        "ok": result.returncode == 0,
        "message": "linux-firmware present" if result.returncode == 0 else "linux-firmware still missing",
    }


def rollback(ctx, session) -> List[Dict[str, Any]]:
    return []


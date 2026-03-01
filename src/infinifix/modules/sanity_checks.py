from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from infinifix.distro import install_packages_command, package_installed_command, resolve_package

DIAG_TOOL_PACKAGES = ["pciutils", "usbutils", "alsa-utils"]


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
    diag_status: Dict[str, Dict[str, str | bool]] = {}
    for logical in DIAG_TOOL_PACKAGES:
        package_name = resolve_package(logical, ctx.distro.family)
        if not package_name:
            continue
        present = ctx.runner.run(package_installed_command(ctx.distro, package_name)).returncode == 0
        diag_status[logical] = {"package": package_name, "installed": present}
    secure_boot = _secure_boot_enabled()
    ctx.runtime["secure_boot"] = secure_boot
    return {
        "linux_firmware_package": pkg,
        "linux_firmware_installed": installed,
        "secure_boot_enabled": secure_boot,
        "diagnostic_tools": diag_status,
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
    missing_tools = []
    for logical, info in detected.get("diagnostic_tools", {}).items():
        if not info.get("installed"):
            missing_tools.append(str(info["package"]))
    if missing_tools:
        actions.append(
            {
                "id": "install_diag_tools",
                "description": f"install diagnostics packages: {', '.join(missing_tools)}",
                "safe": True,
                "advanced": False,
                "packages": missing_tools,
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
        elif action["id"] == "install_diag_tools":
            packages = [str(pkg) for pkg in action.get("packages", [])]
            ok = True
            for cmd in install_packages_command(ctx.distro, packages, refresh=True):
                result = ctx.runner.run(cmd)
                if result.returncode != 0:
                    ok = False
                    rows.append({"id": action["id"], "status": "fail", "message": result.stderr.strip()[:160]})
                    break
            if ok:
                rows.append({"id": action["id"], "status": "ok", "message": f"Installed: {', '.join(packages)}"})
    return rows


def verify(ctx, detected: Dict[str, Any]) -> Dict[str, Any]:
    pkg = detected.get("linux_firmware_package")
    firmware_ok = True
    if pkg:
        result = ctx.runner.run(package_installed_command(ctx.distro, pkg))
        firmware_ok = result.returncode == 0
    tools_ok = True
    for info in detected.get("diagnostic_tools", {}).values():
        package_name = str(info["package"])
        check = ctx.runner.run(package_installed_command(ctx.distro, package_name))
        if check.returncode != 0:
            tools_ok = False
            break

    if detected.get("secure_boot_enabled"):
        msg = "Secure Boot is enabled; DKMS actions may need enrolled keys"
    else:
        msg = "Sanity checks passed"
    ok = firmware_ok and tools_ok
    if not ok:
        msg = "Missing firmware or diagnostics tooling"
    return {"ok": ok, "message": msg}


def rollback(ctx, session) -> List[Dict[str, Any]]:
    return []

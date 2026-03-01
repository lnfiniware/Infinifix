from __future__ import annotations

from typing import Any, Dict, List

from infinifix.distro import install_packages_command, resolve_package


def detect(ctx) -> Dict[str, Any]:
    has_fwupd = ctx.runner.command_exists("fwupdmgr")
    updates_available = False
    output = ""
    if has_fwupd:
        refresh = ctx.runner.run(["fwupdmgr", "refresh"])
        updates = ctx.runner.run(["fwupdmgr", "get-updates"])
        output = (refresh.stdout + refresh.stderr + updates.stdout + updates.stderr).strip()
        lower = updates.stdout.lower() + updates.stderr.lower()
        if "no upgrades for" not in lower and "no updatable devices" not in lower and updates.returncode == 0:
            updates_available = True
    return {
        "fwupd_installed": has_fwupd,
        "updates_available": updates_available,
        "raw": output,
    }


def plan(ctx, detected: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    if not detected.get("fwupd_installed"):
        actions.append(
            {
                "id": "install_fwupd",
                "description": "install fwupd",
                "safe": True,
                "advanced": False,
            }
        )

    actions.append(
        {
            "id": "refresh_fwupd_metadata",
            "description": "run fwupdmgr refresh + get-updates",
            "safe": True,
            "advanced": False,
        }
    )

    if detected.get("updates_available"):
        actions.append(
            {
                "id": "apply_fwupd_updates",
                "description": "run fwupdmgr update",
                "safe": False,
                "advanced": True,
            }
        )
    return actions


def apply(ctx, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for action in actions:
        if action["id"] == "install_fwupd":
            pkg = resolve_package("fwupd", ctx.distro.family)
            if not pkg:
                rows.append({"id": action["id"], "status": "skip", "message": "No fwupd package mapping"})
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

        elif action["id"] == "refresh_fwupd_metadata":
            refresh = ctx.runner.run(["fwupdmgr", "refresh"])
            updates = ctx.runner.run(["fwupdmgr", "get-updates"])
            ok = refresh.returncode == 0 and updates.returncode in {0, 2}
            rows.append(
                {
                    "id": action["id"],
                    "status": "ok" if ok else "warn",
                    "message": "fwupd metadata refreshed" if ok else "fwupd check returned non-zero",
                }
            )

        elif action["id"] == "apply_fwupd_updates":
            result = ctx.runner.run(["fwupdmgr", "update", "-y"])
            rows.append(
                {
                    "id": action["id"],
                    "status": "ok" if result.returncode == 0 else "warn",
                    "message": "Firmware updates applied" if result.returncode == 0 else result.stderr.strip()[:160],
                }
            )
    return rows


def verify(ctx, detected: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.runner.command_exists("fwupdmgr"):
        return {"ok": False, "message": "fwupdmgr missing"}
    result = ctx.runner.run(["fwupdmgr", "get-devices"])
    return {
        "ok": result.returncode == 0,
        "message": "fwupdmgr get-devices ok" if result.returncode == 0 else "fwupdmgr get-devices failed",
    }


def rollback(ctx, session) -> List[Dict[str, Any]]:
    return []


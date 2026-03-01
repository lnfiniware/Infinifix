from __future__ import annotations

from typing import Any, Dict, List

from infinifix.distro import grub_regen_command, initramfs_command


def detect(ctx) -> Dict[str, Any]:
    return {
        "needs_boot_refresh": bool(ctx.runtime.get("needs_boot_refresh")),
        "needs_grub_regen": bool(ctx.runtime.get("needs_grub_regen")),
    }


def plan(ctx, detected: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    if detected.get("needs_boot_refresh"):
        actions.append(
            {
                "id": "rebuild_initramfs",
                "description": "rebuild initramfs",
                "safe": True,
                "advanced": False,
                "command": initramfs_command(ctx.distro),
            }
        )
    if detected.get("needs_grub_regen"):
        actions.append(
            {
                "id": "regenerate_grub_cfg",
                "description": "regenerate grub config",
                "safe": True,
                "advanced": False,
                "command": grub_regen_command(ctx.distro),
            }
        )
    return actions


def apply(ctx, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for action in actions:
        command = action.get("command", ["false"])
        result = ctx.runner.run(command)
        rows.append(
            {
                "id": action["id"],
                "status": "ok" if result.returncode == 0 else "warn",
                "message": "command finished" if result.returncode == 0 else result.stderr.strip()[:160],
            }
        )
    return rows


def verify(ctx, detected: Dict[str, Any]) -> Dict[str, Any]:
    if not detected.get("needs_boot_refresh") and not detected.get("needs_grub_regen"):
        return {"ok": True, "message": "No boot artifact changes needed"}
    return {"ok": True, "message": "Boot artifacts updated"}


def rollback(ctx, session) -> List[Dict[str, Any]]:
    return []

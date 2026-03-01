from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from infinifix.distro import install_packages_command, package_installed_command, resolve_package
from infinifix.paths import wireplumber_template_candidates


DROPIN_TARGET = Path("/etc/wireplumber/wireplumber.conf.d/51-infinifix.conf")


def _dropin_source() -> Path:
    for candidate in wireplumber_template_candidates():
        if candidate.exists():
            return candidate
    return wireplumber_template_candidates()[0]


def _pkg_installed(ctx, logical_name: str) -> bool:
    pkg = resolve_package(logical_name, ctx.distro.family)
    if not pkg:
        return False
    return ctx.runner.run(package_installed_command(ctx.distro, pkg)).returncode == 0


def _user_service_active(ctx, service: str) -> bool:
    result = ctx.runner.run(["systemctl", "--user", "is-active", service], as_user=ctx.target_user)
    return result.returncode == 0 and result.stdout.strip() == "active"


def detect(ctx) -> Dict[str, Any]:
    pipewire_installed = _pkg_installed(ctx, "pipewire")
    wireplumber_installed = _pkg_installed(ctx, "wireplumber")
    pulse_compat_installed = _pkg_installed(ctx, "pipewire-pulse")

    sinks = ctx.runner.run(["bash", "-lc", "pactl list short sinks"])
    sources = ctx.runner.run(["bash", "-lc", "pactl list short sources"])

    return {
        "pipewire_installed": pipewire_installed,
        "wireplumber_installed": wireplumber_installed,
        "pipewire_pulse_installed": pulse_compat_installed,
        "pipewire_active": _user_service_active(ctx, "pipewire"),
        "wireplumber_active": _user_service_active(ctx, "wireplumber"),
        "pipewire_pulse_active": _user_service_active(ctx, "pipewire-pulse"),
        "sinks_found": bool(sinks.stdout.strip()),
        "sources_found": bool(sources.stdout.strip()),
        "dropin_exists": DROPIN_TARGET.exists(),
    }


def plan(ctx, detected: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    missing = []
    if not detected.get("pipewire_installed"):
        missing.append(resolve_package("pipewire", ctx.distro.family))
    if not detected.get("wireplumber_installed"):
        missing.append(resolve_package("wireplumber", ctx.distro.family))
    if not detected.get("pipewire_pulse_installed"):
        missing.append(resolve_package("pipewire-pulse", ctx.distro.family))
    missing = [pkg for pkg in missing if pkg]

    if missing:
        actions.append(
            {
                "id": "install_pipewire_stack",
                "description": "install PipeWire + WirePlumber + pulse compatibility",
                "safe": True,
                "advanced": False,
                "packages": missing,
            }
        )

    if (not detected.get("sinks_found") or not detected.get("sources_found")) and not detected.get("dropin_exists"):
        actions.append(
            {
                "id": "add_wireplumber_dropin",
                "description": "add minimal WirePlumber drop-in",
                "safe": True,
                "advanced": False,
            }
        )

    if not all(
        [
            detected.get("pipewire_active"),
            detected.get("wireplumber_active"),
            detected.get("pipewire_pulse_active"),
        ]
    ):
        actions.append(
            {
                "id": "enable_user_audio_services",
                "description": "enable --user pipewire, pipewire-pulse, wireplumber",
                "safe": True,
                "advanced": False,
            }
        )
    return actions


def apply(ctx, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for action in actions:
        if action["id"] == "install_pipewire_stack":
            packages = [str(pkg) for pkg in action.get("packages", [])]
            ok = True
            for cmd in install_packages_command(ctx.distro, packages, refresh=True):
                result = ctx.runner.run(cmd)
                if result.returncode != 0:
                    ok = False
                    rows.append({"id": action["id"], "status": "fail", "message": result.stderr.strip()[:160]})
                    break
            if ok:
                rows.append({"id": action["id"], "status": "ok", "message": ", ".join(packages)})

        elif action["id"] == "add_wireplumber_dropin":
            source = _dropin_source()
            if not source.exists():
                rows.append({"id": action["id"], "status": "fail", "message": f"Missing template: {source}"})
                continue
            ctx.backup.write_text(DROPIN_TARGET, source.read_text(encoding="utf-8"))
            rows.append({"id": action["id"], "status": "ok", "message": f"Wrote {DROPIN_TARGET}"})

        elif action["id"] == "enable_user_audio_services":
            cmd = "systemctl --user enable --now pipewire pipewire-pulse wireplumber"
            result = ctx.runner.run(["bash", "-lc", cmd], as_user=ctx.target_user)
            rows.append(
                {
                    "id": action["id"],
                    "status": "ok" if result.returncode == 0 else "warn",
                    "message": "user services enabled" if result.returncode == 0 else result.stderr.strip()[:160],
                }
            )
    return rows


def verify(ctx, detected: Dict[str, Any]) -> Dict[str, Any]:
    pactl = ctx.runner.run(["bash", "-lc", "pactl info"])
    sinks = ctx.runner.run(["bash", "-lc", "pactl list short sinks"])
    services_ok = all(
        [
            _user_service_active(ctx, "pipewire"),
            _user_service_active(ctx, "wireplumber"),
            _user_service_active(ctx, "pipewire-pulse"),
        ]
    )
    ok = pactl.returncode == 0 and bool(sinks.stdout.strip()) and services_ok
    return {"ok": ok, "message": "PipeWire stack healthy" if ok else "PipeWire stack still incomplete"}


def rollback(ctx, session) -> List[Dict[str, Any]]:
    return []

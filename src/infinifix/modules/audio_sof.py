from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from infinifix.distro import install_packages_command, package_installed_command, resolve_package

DSP_CONF_PATH = Path("/etc/modprobe.d/snd-intel-dspcfg.conf")
GRUB_DEFAULT_PATH = Path("/etc/default/grub")
DSP_LINE = "options snd-intel-dspcfg dsp_driver=3\n"
DSP_PARAM = "snd_intel_dspcfg.dsp_driver=3"


def _kernel_param_present() -> bool:
    if not GRUB_DEFAULT_PATH.exists():
        return False
    text = GRUB_DEFAULT_PATH.read_text(encoding="utf-8", errors="ignore")
    return DSP_PARAM in text


def detect(ctx) -> Dict[str, Any]:
    lspci_lines = [str(line) for line in ctx.probe.get("lspci", [])]
    intel_audio = any("intel" in line.lower() and "audio" in line.lower() for line in lspci_lines)

    lsmod = ctx.runner.run(["lsmod"]).stdout.lower()
    sof_loaded = "snd_sof" in lsmod or "sof_audio_pci" in lsmod or "sof-audio-pci" in lsmod
    dspcfg_loaded = "snd_intel_dspcfg" in lsmod
    dspcfg_in_sysfs = Path("/sys/module/snd_intel_dspcfg").exists()

    aplay = ctx.runner.run(["bash", "-lc", "aplay -l"])
    pactl_info = ctx.runner.run(["bash", "-lc", "pactl info"])
    sinks = ctx.runner.run(["bash", "-lc", "pactl list short sinks"])

    sof_pkg = resolve_package("sof-firmware", ctx.distro.family)
    sof_installed = True
    if sof_pkg:
        sof_installed = ctx.runner.run(package_installed_command(ctx.distro, sof_pkg)).returncode == 0

    dsp_conf_present = False
    if DSP_CONF_PATH.exists():
        try:
            dsp_conf_present = "dsp_driver=3" in DSP_CONF_PATH.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            dsp_conf_present = False

    return {
        "intel_audio": intel_audio,
        "sof_loaded": sof_loaded,
        "dspcfg_loaded": dspcfg_loaded,
        "dspcfg_in_sysfs": dspcfg_in_sysfs,
        "aplay_has_devices": "card " in aplay.stdout.lower(),
        "pactl_ok": pactl_info.returncode == 0,
        "dummy_output": "dummy" in sinks.stdout.lower(),
        "sof_firmware_package": sof_pkg,
        "sof_firmware_installed": sof_installed,
        "dsp_conf_present": dsp_conf_present,
        "grub_param_present": _kernel_param_present(),
    }


def plan(ctx, detected: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    intel_audio = detected.get("intel_audio", False)
    audio_broken = detected.get("dummy_output", False) or not detected.get("aplay_has_devices", True)

    if intel_audio and detected.get("sof_firmware_package") and not detected.get("sof_firmware_installed"):
        actions.append(
            {
                "id": "install_sof_firmware",
                "description": f"install {detected['sof_firmware_package']}",
                "safe": True,
                "advanced": False,
            }
        )

    if intel_audio and audio_broken and not detected.get("dsp_conf_present", False):
        actions.append(
            {
                "id": "set_dsp_driver_3",
                "description": "set snd-intel-dspcfg dsp_driver=3",
                "safe": True,
                "advanced": False,
            }
        )
        ctx.runtime["needs_boot_refresh"] = True

    # Bootloader edits are advanced-only.
    # We only recommend this when modprobe option already exists but audio is still broken,
    # or when the module appears built-in (sysfs visible, not in lsmod).
    needs_advanced_grub = (
        intel_audio
        and audio_broken
        and not detected.get("grub_param_present")
        and (
            detected.get("dsp_conf_present", False)
            or (detected.get("dspcfg_in_sysfs", False) and not detected.get("dspcfg_loaded", False))
        )
    )
    if needs_advanced_grub:
        actions.append(
            {
                "id": "add_grub_dsp_param",
                "description": "advanced: append kernel param snd_intel_dspcfg.dsp_driver=3 in /etc/default/grub",
                "safe": False,
                "advanced": True,
            }
        )
        if ctx.include_advanced:
            ctx.runtime["needs_grub_regen"] = True

    return actions


def _inject_kernel_param(grub_text: str, param: str) -> str:
    keys = ["GRUB_CMDLINE_LINUX_DEFAULT", "GRUB_CMDLINE_LINUX"]
    lines = grub_text.splitlines()
    touched = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        for key in keys:
            if stripped.startswith(f"{key}="):
                prefix, value = line.split("=", 1)
                quote = '"' if '"' in value else "'"
                payload = value.strip().strip('"').strip("'").strip()
                if param not in payload.split():
                    payload = f"{payload} {param}".strip()
                lines[idx] = f"{prefix}={quote}{payload}{quote}"
                touched = True
                break
    if not touched:
        lines.append(f'GRUB_CMDLINE_LINUX_DEFAULT="{param}"')
    return "\n".join(lines) + "\n"


def apply(ctx, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for action in actions:
        if action["id"] == "install_sof_firmware":
            pkg = resolve_package("sof-firmware", ctx.distro.family)
            if not pkg:
                rows.append({"id": action["id"], "status": "skip", "message": "No SOF package mapping"})
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

        elif action["id"] == "set_dsp_driver_3":
            ctx.backup.write_text(DSP_CONF_PATH, DSP_LINE)
            rows.append({"id": action["id"], "status": "ok", "message": f"Wrote {DSP_CONF_PATH}"})

        elif action["id"] == "add_grub_dsp_param":
            current = ""
            if GRUB_DEFAULT_PATH.exists():
                current = GRUB_DEFAULT_PATH.read_text(encoding="utf-8", errors="ignore")
            updated = _inject_kernel_param(current, DSP_PARAM)
            ctx.backup.write_text(GRUB_DEFAULT_PATH, updated)
            rows.append({"id": action["id"], "status": "ok", "message": f"Updated {GRUB_DEFAULT_PATH}"})
    return rows


def verify(ctx, detected: Dict[str, Any]) -> Dict[str, Any]:
    aplay = ctx.runner.run(["bash", "-lc", "aplay -l"])
    pactl = ctx.runner.run(["bash", "-lc", "pactl info"])
    sinks = ctx.runner.run(["bash", "-lc", "pactl list short sinks"])
    sources = ctx.runner.run(["bash", "-lc", "pactl list short sources"])

    sink_count = len([line for line in sinks.stdout.splitlines() if line.strip()])
    source_count = len([line for line in sources.stdout.splitlines() if line.strip()])
    ok = "card " in aplay.stdout.lower() and pactl.returncode == 0 and sink_count > 0
    return {
        "ok": ok,
        "message": (
            f"Audio stack looks healthy (sinks={sink_count}, sources={source_count})"
            if ok
            else f"Audio still broken (sinks={sink_count}, sources={source_count}). "
            "Run `infinifix report` and attach the tarball."
        ),
    }


def rollback(ctx, session) -> List[Dict[str, Any]]:
    return []

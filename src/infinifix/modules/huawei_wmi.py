from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from infinifix.distro import install_packages_command, resolve_package


UDEV_RULES = Path("/etc/udev/rules.d/99-infinifix-huawei.rules")
THRESHOLD_CONF = Path("/etc/infinifix/thresholds.conf")
THRESHOLD_SERVICE = Path("/etc/systemd/system/infinifix-thresholds.service")
THRESHOLD_SCRIPT = Path("/usr/libexec/infinifix/restore-thresholds.sh")
SLEEP_HOOK = Path("/usr/lib/systemd/system-sleep/infinifix-thresholds")


def _is_huawei_like(vendor: str, product: str) -> bool:
    value = f"{vendor} {product}".lower()
    return "huawei" in value or "honor" in value


def _threshold_paths() -> List[Path]:
    candidates = [
        Path("/sys/class/power_supply/BAT0/charge_control_start_threshold"),
        Path("/sys/class/power_supply/BAT0/charge_control_end_threshold"),
        Path("/sys/devices/platform/huawei-wmi/charge_control_thresholds"),
    ]
    return [path for path in candidates if path.exists()]


def detect(ctx) -> Dict[str, Any]:
    vendor = str(ctx.probe.get("dmi_vendor", "")).strip()
    product = str(ctx.probe.get("dmi_product_name", "")).strip()
    thresholds = _threshold_paths()
    fn_lock = Path("/sys/devices/platform/huawei-wmi/fn_lock_state")
    fn_lock_path = str(fn_lock) if fn_lock.exists() else ""
    fn_lock_readable = False
    if fn_lock.exists():
        try:
            fn_lock.read_text(encoding="utf-8")
            fn_lock_readable = True
        except OSError:
            fn_lock_readable = False

    mic_led = []
    leds_root = Path("/sys/class/leds")
    if leds_root.exists():
        mic_led = [str(item) for item in leds_root.iterdir() if "micmute" in item.name.lower()]

    return {
        "vendor": vendor,
        "product": product,
        "is_huawei": _is_huawei_like(vendor, product),
        "wmi_present": Path("/sys/devices/platform/huawei-wmi").exists(),
        "threshold_paths": [str(path) for path in thresholds],
        "fn_lock_path": fn_lock_path,
        "fn_lock_readable": fn_lock_readable,
        "micmute_led_paths": mic_led,
    }


def plan(ctx, detected: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not detected.get("is_huawei"):
        return []

    actions: List[Dict[str, Any]] = [
        {
            "id": "setup_infinifix_group_udev",
            "description": "create infinifix group + udev threshold permissions",
            "safe": True,
            "advanced": False,
        }
    ]

    if detected.get("threshold_paths"):
        actions.append(
            {
                "id": "install_threshold_reinstate",
                "description": "install threshold restore service + suspend hook",
                "safe": True,
                "advanced": False,
            }
        )

    if not detected.get("wmi_present"):
        msg = "install Huawei-WMI DKMS module from GitHub"
        if ctx.runtime.get("secure_boot"):
            msg += " (may fail with Secure Boot enabled)"
        actions.append(
            {
                "id": "install_huawei_wmi_dkms",
                "description": msg,
                "safe": False,
                "advanced": True,
            }
        )
    return actions


def _udev_content() -> str:
    return """# InfiniFix Huawei controls
SUBSYSTEM=="power_supply", KERNEL=="BAT*", ATTR{charge_control_start_threshold}=="*", GROUP="infinifix", MODE="0664"
SUBSYSTEM=="power_supply", KERNEL=="BAT*", ATTR{charge_control_end_threshold}=="*", GROUP="infinifix", MODE="0664"
KERNEL=="huawei-wmi", GROUP="infinifix", MODE="0664"
"""


def _threshold_conf_content() -> str:
    return """# InfiniFix threshold defaults
START=40
END=80
"""


def _threshold_script_content() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail
[ -f /etc/infinifix/thresholds.conf ] && source /etc/infinifix/thresholds.conf
START="${START:-40}"
END="${END:-80}"

if [ -w /sys/class/power_supply/BAT0/charge_control_start_threshold ]; then
  echo "$START" > /sys/class/power_supply/BAT0/charge_control_start_threshold || true
fi
if [ -w /sys/class/power_supply/BAT0/charge_control_end_threshold ]; then
  echo "$END" > /sys/class/power_supply/BAT0/charge_control_end_threshold || true
fi
if [ -w /sys/devices/platform/huawei-wmi/charge_control_thresholds ]; then
  echo "${START} ${END}" > /sys/devices/platform/huawei-wmi/charge_control_thresholds || true
fi
"""


def _threshold_service_content() -> str:
    return """[Unit]
Description=InfiniFix restore Huawei battery thresholds
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/libexec/infinifix/restore-thresholds.sh

[Install]
WantedBy=multi-user.target
"""


def _sleep_hook_content() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "post" ]; then
  /usr/libexec/infinifix/restore-thresholds.sh || true
fi
"""


def apply(ctx, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for action in actions:
        if action["id"] == "setup_infinifix_group_udev":
            ctx.runner.run(["groupadd", "-f", "infinifix"])
            ctx.backup.write_text(UDEV_RULES, _udev_content())
            ctx.runner.run(["udevadm", "control", "--reload-rules"])
            rows.append({"id": action["id"], "status": "ok", "message": f"Configured {UDEV_RULES}"})

        elif action["id"] == "install_threshold_reinstate":
            ctx.backup.write_text(THRESHOLD_CONF, _threshold_conf_content())
            ctx.backup.write_executable(THRESHOLD_SCRIPT, _threshold_script_content())
            ctx.backup.write_text(THRESHOLD_SERVICE, _threshold_service_content())
            ctx.backup.write_executable(SLEEP_HOOK, _sleep_hook_content())
            ctx.runner.run(["systemctl", "daemon-reload"])
            ctx.runner.run(["systemctl", "enable", "--now", "infinifix-thresholds.service"])
            rows.append({"id": action["id"], "status": "ok", "message": "Threshold service installed"})

        elif action["id"] == "install_huawei_wmi_dkms":
            deps = []
            for logical in ["dkms", "git", "make", "gcc", "kernel-headers"]:
                package = resolve_package(logical, ctx.distro.family)
                if package:
                    deps.append(package)
            for cmd in install_packages_command(ctx.distro, deps, refresh=True):
                ctx.runner.run(cmd)
            install_cmd = (
                "set -euo pipefail; "
                "tmp=$(mktemp -d); "
                "git clone --depth=1 https://github.com/qu1x/huawei-wmi.git \"$tmp\"; "
                "cd \"$tmp\"; "
                "if [ -x ./install.sh ]; then ./install.sh; "
                "elif [ -f dkms.conf ]; then "
                "name=$(grep -E '^PACKAGE_NAME=' dkms.conf | cut -d= -f2 | tr -d '\"'); "
                "ver=$(grep -E '^PACKAGE_VERSION=' dkms.conf | cut -d= -f2 | tr -d '\"'); "
                "dkms add . || true; "
                "dkms build \"$name/$ver\"; "
                "dkms install \"$name/$ver\"; "
                "else make && make install; fi"
            )
            result = ctx.runner.run(["bash", "-lc", install_cmd])
            rows.append(
                {
                    "id": action["id"],
                    "status": "ok" if result.returncode == 0 else "warn",
                    "message": "DKMS install attempted" if result.returncode == 0 else result.stderr.strip()[:160],
                }
            )
    return rows


def verify(ctx, detected: Dict[str, Any]) -> Dict[str, Any]:
    threshold_paths = _threshold_paths()
    threshold_ok = all(path.exists() for path in threshold_paths) if threshold_paths else True
    wmi_ok = Path("/sys/devices/platform/huawei-wmi").exists() or not detected.get("is_huawei")
    fn_ok = bool(detected.get("fn_lock_readable", True)) or not bool(detected.get("fn_lock_path", ""))
    ok = threshold_ok and wmi_ok and fn_ok
    detail = []
    if detected.get("fn_lock_path"):
        detail.append("fn-lock readable" if fn_ok else "fn-lock path unreadable")
    if detected.get("micmute_led_paths"):
        detail.append("micmute LED path present")
    return {
        "ok": ok,
        "message": "Huawei WMI paths look sane"
        if ok
        else "Huawei WMI features partially unavailable"
        + (f" ({'; '.join(detail)})" if detail else ""),
    }


def rollback(ctx, session) -> List[Dict[str, Any]]:
    return []

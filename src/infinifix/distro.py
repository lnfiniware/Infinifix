from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class DistroInfo:
    distro_id: str
    id_like: List[str]
    pretty_name: str
    family: str
    package_manager: str


FAMILY_MAP = {
    "debian": {"debian", "ubuntu", "linuxmint", "pop", "zorin", "elementary"},
    "fedora": {"fedora", "rhel", "centos", "rocky", "almalinux"},
    "arch": {"arch", "manjaro", "endeavouros", "cachyos"},
    "suse": {"opensuse", "opensuse-tumbleweed", "opensuse-leap", "suse", "sled", "sles"},
}

PACKAGE_MANAGER_MAP = {
    "debian": "apt",
    "fedora": "dnf",
    "arch": "pacman",
    "suse": "zypper",
    "unknown": "unknown",
}

LOGICAL_PACKAGES = {
    "fwupd": {
        "debian": "fwupd",
        "fedora": "fwupd",
        "arch": "fwupd",
        "suse": "fwupd",
    },
    "sof-firmware": {
        "debian": "sof-firmware",
        "fedora": "alsa-sof-firmware",
        "arch": "sof-firmware",
        "suse": "sof-firmware",
    },
    "linux-firmware": {
        "debian": "firmware-linux",
        "fedora": "linux-firmware",
        "arch": "linux-firmware",
        "suse": "kernel-firmware",
    },
    "pipewire": {
        "debian": "pipewire",
        "fedora": "pipewire",
        "arch": "pipewire",
        "suse": "pipewire",
    },
    "wireplumber": {
        "debian": "wireplumber",
        "fedora": "wireplumber",
        "arch": "wireplumber",
        "suse": "wireplumber",
    },
    "pipewire-pulse": {
        "debian": "pipewire-pulse",
        "fedora": "pipewire-pulseaudio",
        "arch": "pipewire-pulse",
        "suse": "pipewire-pulseaudio",
    },
    "dkms": {
        "debian": "dkms",
        "fedora": "dkms",
        "arch": "dkms",
        "suse": "dkms",
    },
    "git": {
        "debian": "git",
        "fedora": "git",
        "arch": "git",
        "suse": "git",
    },
    "make": {
        "debian": "make",
        "fedora": "make",
        "arch": "make",
        "suse": "make",
    },
    "gcc": {
        "debian": "gcc",
        "fedora": "gcc",
        "arch": "gcc",
        "suse": "gcc",
    },
    "kernel-headers": {
        "debian": "linux-headers-amd64",
        "fedora": "kernel-devel",
        "arch": "linux-headers",
        "suse": "kernel-default-devel",
    },
    "pciutils": {
        "debian": "pciutils",
        "fedora": "pciutils",
        "arch": "pciutils",
        "suse": "pciutils",
    },
    "usbutils": {
        "debian": "usbutils",
        "fedora": "usbutils",
        "arch": "usbutils",
        "suse": "usbutils",
    },
    "alsa-utils": {
        "debian": "alsa-utils",
        "fedora": "alsa-utils",
        "arch": "alsa-utils",
        "suse": "alsa-utils",
    },
    "mokutil": {
        "debian": "mokutil",
        "fedora": "mokutil",
        "arch": "mokutil",
        "suse": "mokutil",
    },
}


def parse_os_release(os_release_text: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for raw_line in os_release_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        data[key] = value
    return data


def _detect_family(distro_id: str, id_like: List[str]) -> str:
    values = {distro_id.lower(), *[item.lower() for item in id_like]}
    for family, needles in FAMILY_MAP.items():
        if values & needles:
            return family
    return "unknown"


def detect_distro(os_release_text: str | None = None) -> DistroInfo:
    if os_release_text is None:
        os_release_path = Path("/etc/os-release")
        if os_release_path.exists():
            os_release_text = os_release_path.read_text(encoding="utf-8")
        else:
            return DistroInfo(
                distro_id="unknown",
                id_like=[],
                pretty_name="unknown",
                family="unknown",
                package_manager="unknown",
            )
    parsed = parse_os_release(os_release_text)
    distro_id = parsed.get("ID", "unknown").lower()
    id_like = [item for item in parsed.get("ID_LIKE", "").split() if item]
    pretty_name = parsed.get("PRETTY_NAME", distro_id)
    family = _detect_family(distro_id, id_like)
    package_manager = PACKAGE_MANAGER_MAP.get(family, "unknown")
    return DistroInfo(
        distro_id=distro_id,
        id_like=id_like,
        pretty_name=pretty_name,
        family=family,
        package_manager=package_manager,
    )


def resolve_package(logical_name: str, family: str) -> str | None:
    return LOGICAL_PACKAGES.get(logical_name, {}).get(family)


def package_installed_command(distro: DistroInfo, package_name: str) -> List[str]:
    if distro.family == "debian":
        return ["dpkg", "-s", package_name]
    if distro.family in {"fedora", "suse"}:
        return ["rpm", "-q", package_name]
    if distro.family == "arch":
        return ["pacman", "-Qi", package_name]
    return ["false"]


def install_packages_command(distro: DistroInfo, packages: List[str], refresh: bool = False) -> List[List[str]]:
    if not packages:
        return []
    if distro.family == "debian":
        commands: List[List[str]] = []
        if refresh:
            commands.append(["apt-get", "update"])
        commands.append(["apt-get", "install", "-y", *packages])
        return commands
    if distro.family == "fedora":
        return [["dnf", "install", "-y", *packages]]
    if distro.family == "arch":
        return [["pacman", "-Sy", "--noconfirm", *packages]]
    if distro.family == "suse":
        return [["zypper", "--non-interactive", "install", *packages]]
    return [["false"]]


def initramfs_command(distro: DistroInfo) -> List[str]:
    if distro.family == "debian":
        return ["update-initramfs", "-u"]
    if distro.family in {"fedora", "suse"}:
        return ["dracut", "--force"]
    if distro.family == "arch":
        return ["mkinitcpio", "-P"]
    return ["false"]


def grub_regen_command(distro: DistroInfo) -> List[str]:
    if distro.family == "debian":
        return ["update-grub"]
    if distro.family == "fedora":
        return ["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"]
    if distro.family == "arch":
        return ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"]
    if distro.family == "suse":
        return ["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"]
    return ["false"]

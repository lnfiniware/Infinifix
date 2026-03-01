from infinifix.distro import (
    detect_distro,
    grub_regen_command,
    initramfs_command,
    resolve_package,
)


def test_detect_ubuntu_family() -> None:
    text = """
NAME="Ubuntu"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 24.04 LTS"
"""
    distro = detect_distro(text)
    assert distro.family == "debian"
    assert distro.package_manager == "apt"


def test_detect_fedora_family() -> None:
    text = """
NAME=Fedora
ID=fedora
ID_LIKE="fedora rhel"
PRETTY_NAME="Fedora Linux"
"""
    distro = detect_distro(text)
    assert distro.family == "fedora"
    assert distro.package_manager == "dnf"


def test_package_resolution() -> None:
    assert resolve_package("fwupd", "debian") == "fwupd"
    assert resolve_package("sof-firmware", "fedora") == "alsa-sof-firmware"


def test_initramfs_and_grub_commands() -> None:
    distro = detect_distro(
        """
ID=arch
PRETTY_NAME="Arch Linux"
"""
    )
    assert initramfs_command(distro) == ["mkinitcpio", "-P"]
    assert grub_regen_command(distro) == ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"]

#!/usr/bin/env bash
set -euo pipefail

action="${1:-base}"

if [[ "${action}" == "base" ]]; then
  pacman -Sy --noconfirm \
    python python-pip python-rich \
    cmake gcc make pkgconf \
    pciutils usbutils alsa-utils fwupd rsync
  exit 0
fi

echo "Usage: $0 base"
exit 1

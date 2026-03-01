#!/usr/bin/env bash
set -euo pipefail

action="${1:-base}"

if [[ "${action}" == "base" ]]; then
  dnf install -y \
    python3 python3-pip python3-rich python3-setuptools \
    cmake gcc-c++ gcc make pkgconf-pkg-config \
    pciutils usbutils alsa-utils fwupd rsync
  exit 0
fi

echo "Usage: $0 base"
exit 1

#!/usr/bin/env bash
set -euo pipefail

action="${1:-base}"

if [[ "${action}" == "base" ]]; then
  apt-get update
  apt-get install -y \
    python3 python3-venv python3-pip python3-rich python3-setuptools \
    cmake g++ gcc make pkg-config \
    pciutils usbutils alsa-utils fwupd rsync
  exit 0
fi

echo "Usage: $0 base"
exit 1

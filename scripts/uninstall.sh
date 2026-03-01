#!/usr/bin/env bash
set -euo pipefail

PREFIX="/usr"
APP_ROOT="/opt/infinifix"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      PREFIX="${2:-}"
      shift 2
      ;;
    --app-root)
      APP_ROOT="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat <<EOF
Usage: sudo ./scripts/uninstall.sh [options]

Options:
  --prefix <path>      Prefix used during install (default: /usr)
  --app-root <path>    App runtime root (default: /opt/infinifix)
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root: sudo ./scripts/uninstall.sh"
  exit 1
fi

systemctl disable --now infinifix-thresholds.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/infinifix-thresholds.service
rm -f /usr/lib/systemd/system-sleep/infinifix-thresholds
rm -f /etc/udev/rules.d/99-infinifix-huawei.rules
rm -f "${PREFIX}/libexec/infinifix/restore-thresholds.sh"
rm -f /usr/local/lib/infinifix/restore-thresholds.sh

rm -f "${PREFIX}/bin/infinifix"
rm -rf "${PREFIX}/libexec/infinifix"
rm -rf "${PREFIX}/share/infinifix"
rm -f "${PREFIX}/share/applications/infinifix.desktop"
rm -f "${PREFIX}/share/icons/hicolor/scalable/apps/infinifix.svg"
rm -f "${PREFIX}/share/metainfo/infinifix.appdata.xml"
rm -f "${PREFIX}/share/man/man1/infinifix.1"
rm -f "${PREFIX}/share/man/man1/infinifix.1.gz"
rm -rf "${APP_ROOT}"

systemctl daemon-reload >/dev/null 2>&1 || true
udevadm control --reload-rules >/dev/null 2>&1 || true

echo "InfiniFix uninstalled."
echo "Backups and reports kept in /var/lib/infinifix and /var/log/infinifix."

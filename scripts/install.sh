#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="/usr"
APP_ROOT="/opt/infinifix"
DESKTOP_ENTRY=1

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
    --no-desktop)
      DESKTOP_ENTRY=0
      shift
      ;;
    -h|--help)
      cat <<EOF
Usage: sudo ./scripts/install.sh [options]

Options:
  --prefix <path>      Install prefix for runtime wrappers/assets (default: /usr)
  --app-root <path>    Python runtime venv root (default: /opt/infinifix)
  --no-desktop         Skip .desktop/appstream/icon install
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "InfiniFix installer supports Linux only."
  exit 1
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root: sudo ./scripts/install.sh"
  exit 1
fi

if [[ ! -f /etc/os-release ]]; then
  echo "Cannot detect distro: /etc/os-release missing."
  exit 1
fi
source /etc/os-release

family="unknown"
case "${ID,,} ${ID_LIKE,,}" in
  *debian*|*ubuntu*)
    family="debian"
    ;;
  *fedora*|*rhel*|*centos*|*rocky*|*almalinux*)
    family="fedora"
    ;;
  *arch*|*manjaro*|*endeavouros*|*cachyos*)
    family="arch"
    ;;
  *opensuse*|*suse*)
    family="suse"
    ;;
esac

if [[ "${family}" == "unknown" ]]; then
  echo "Unsupported distro family for auto-install."
  exit 1
fi

echo "Detected distro family: ${family}"
case "${family}" in
  debian) distro_script="${ROOT_DIR}/scripts/distros/debian_apt.sh" ;;
  fedora) distro_script="${ROOT_DIR}/scripts/distros/fedora_dnf.sh" ;;
  arch) distro_script="${ROOT_DIR}/scripts/distros/arch_pacman.sh" ;;
  suse) distro_script="${ROOT_DIR}/scripts/distros/suse_zypper.sh" ;;
esac
"${distro_script}" base

echo "Building hardware probe..."
cmake -S "${ROOT_DIR}/src/cpp" -B "${ROOT_DIR}/build/cpp"
cmake --build "${ROOT_DIR}/build/cpp" --config Release

echo "Installing Python runtime..."
VENV_DIR="${APP_ROOT}/venv"
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip wheel setuptools
"${VENV_DIR}/bin/pip" install --upgrade "${ROOT_DIR}"

BIN_DIR="${PREFIX}/bin"
SHARE_DIR="${PREFIX}/share/infinifix"
LIBEXEC_DIR="${PREFIX}/libexec/infinifix"
APP_DIR="${PREFIX}/share/applications"
ICON_DIR="${PREFIX}/share/icons/hicolor/scalable/apps"
METAINFO_DIR="${PREFIX}/share/metainfo"
MAN_DIR="${PREFIX}/share/man/man1"

install -d "${BIN_DIR}" "${SHARE_DIR}/data/rules/wireplumber" "${SHARE_DIR}/data/rules/ucm2_overrides" "${LIBEXEC_DIR}" "${MAN_DIR}"
install -Dm755 "${ROOT_DIR}/build/cpp/probe" "${LIBEXEC_DIR}/probe"
install -Dm644 "${ROOT_DIR}/src/infinifix/data/rules/wireplumber/51-infinifix.conf" "${SHARE_DIR}/data/rules/wireplumber/51-infinifix.conf"

cat >"${BIN_DIR}/infinifix" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export INFINIFIX_PROBE_PATH="${LIBEXEC_DIR}/probe"
exec "${VENV_DIR}/bin/infinifix" "\$@"
EOF
chmod +x "${BIN_DIR}/infinifix"

if [[ "${DESKTOP_ENTRY}" -eq 1 ]]; then
  install -d "${APP_DIR}" "${ICON_DIR}" "${METAINFO_DIR}"
  install -Dm644 "${ROOT_DIR}/packaging/desktop/infinifix.desktop" "${APP_DIR}/infinifix.desktop"
  install -Dm644 "${ROOT_DIR}/packaging/desktop/infinifix.appdata.xml" "${METAINFO_DIR}/infinifix.appdata.xml"
  install -Dm644 "${ROOT_DIR}/assets/icon-h.svg" "${ICON_DIR}/infinifix.svg"
fi

install -Dm644 "${ROOT_DIR}/packaging/man/infinifix.1" "${MAN_DIR}/infinifix.1"
install -d /var/lib/infinifix/backups /var/log/infinifix/reports

echo "InfiniFix installed."
echo "CLI: infinifix doctor"
if [[ "${DESKTOP_ENTRY}" -eq 1 ]]; then
  echo "App launcher: InfiniFix (terminal)"
fi

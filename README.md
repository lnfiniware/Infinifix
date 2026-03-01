# InfiniFix

**Huawei Linux Doctor**

Repository: `https://github.com/lnfiniware/Infinifix`
Release: `v0.2 (beta)`

InfiniFix is a terminal-first doctor for Huawei and Honor laptops on Linux.
It detects common breakages, builds a safe fix plan, and applies fixes with backups and verification.

The default flow is safe:

- dry-run preview first
- timestamped backups before any config write
- command logs
- post-apply verification
- rollback path

Final message after apply:
`All done. One step left: reboot now or later.`

## What It Fixes

- Firmware update flow with `fwupd`
- Intel SOF audio issues (`Dummy Output`, missing cards, DSP mode toggles)
- PipeWire + WirePlumber service sanity
- Huawei WMI basics (threshold permissions, reinstate service)
- Kernel module and firmware sanity checks

## Supported Distros

- Debian / Ubuntu / derivatives (`apt`)
- Fedora / RHEL-like (`dnf`)
- Arch (`pacman`)
- openSUSE (`zypper`)

## Quick Start

```bash
git clone https://github.com/lnfiniware/Infinifix.git
cd infinifix
sudo ./scripts/install.sh
```

Install options:

```bash
sudo ./scripts/install.sh --prefix /usr --app-root /opt/infinifix
sudo ./scripts/install.sh --no-desktop
```

Run commands:

```bash
infinifix doctor
infinifix doctor --all --yes
infinifix report
sudo infinifix apply
sudo infinifix apply --all --yes
sudo infinifix revert
infinifix status
```

Dry-run works globally:

```bash
infinifix --dry-run apply
```

v0.2 beta highlights:

- `doctor --all --yes` automation path
- `apply --all --yes` non-interactive advanced mode
- execution lock to prevent overlapping runs
- report sanitization for safer sharing

Desktop launcher (optional, terminal app):

- App name: `InfiniFix`
- Action: launches `infinifix doctor` in terminal

## Safety and Rollback

- Backups: `/var/lib/infinifix/backups/<timestamp>/`
- Reports: `/var/log/infinifix/reports/<timestamp>.tar.gz`
- State file: `/var/lib/infinifix/state.json`
- Probe helper: `/usr/libexec/infinifix/probe` (or `/usr/lib/infinifix/probe` on some layouts)

Rollback:

```bash
sudo infinifix revert
```

## Repo Layout

```text
infinifix/
  src/infinifix/       # Python orchestrator + modules
  src/cpp/             # Hardware probe helper
  scripts/             # Installer and distro shell helpers
  packaging/           # Debian/RPM/Arch/openSUSE packaging skeletons
  docs/                # Design + support docs
  assets/              # Brand and README-only media
```

## Trademark and Firmware Notes

- Huawei and Honor are trademarks of their respective owners.
- This project does not ship Huawei logos by default.
- Firmware updates may change hardware behavior; read device notes before applying `--all`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT, see [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

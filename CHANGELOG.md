# Changelog

## v0.2.0-beta (2026-02-27)

- Added `doctor --all --yes` and `apply --all --yes` non-interactive flow.
- Added execution lock to prevent overlapping runs.
- Added report sanitization for safer sharing.
- Expanded sanity checks to include diagnostics tooling packages.
- Improved Huawei WMI verification details (fn-lock readability, micmute path signal).

## v0.1.0-beta (2026-02-11)

- Initial beta release.
- Core modules: firmware, audio/SOF, PipeWire/WirePlumber, Huawei-WMI, grub/initramfs.
- Backup/rollback flow and diagnostic reporting.
- Packaging skeletons for Debian/RPM/Arch/openSUSE.


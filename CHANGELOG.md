# Changelog

## v0.3.0-beta (2026-03-02)

- Fixed plan-collection safety so modules with empty plans are still tracked.
- Added tests for empty-plan modules and CLI parser/version smoke.
- Hardened safe mode:
  - moved GRUB DSP kernel parameter to advanced-only path (`--all`)
  - only proposes GRUB DSP parameter when modprobe path is likely insufficient
- Tuned WirePlumber drop-in policy to advanced mode with power-usage warning.
- Pinned Huawei-WMI DKMS source to a specific upstream tag+commit and log the pinned ref.
- Improved post-apply verification messages:
  - reports sinks/sources counts
  - reports user service status
  - gives explicit report-bundle hint when audio is still broken
- Added Ruff lint/format checks in CI and configured Ruff in `pyproject.toml`.

## v0.2.0-beta (2026-02-24)

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

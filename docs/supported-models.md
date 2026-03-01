# Supported Models

Repository: `https://github.com/lnfiniware/Infinifix`

InfiniFix is model-aware but not model-locked. It uses DMI + runtime probes and applies safe fixes only when signals match.

## Known Good Coverage

- MateBook D14 / D15 series (Intel variants)
- MateBook 13 / 14 / X Pro (selected Intel generations)
- Honor MagicBook devices that expose Huawei/Honor DMI strings

## Community Validation

If your model works, open a PR with:

- `infinifix report` bundle details (sanitize personal info first)
- model name from DMI
- kernel + distro
- what worked / what failed

## Notes

- AMD models may skip Intel SOF-specific actions.
- WMI features vary by firmware and kernel.
- Some features need reboot to validate fully.

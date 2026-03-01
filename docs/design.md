# Design Notes

Repository: `https://github.com/lnfiniware/Infinifix`
Release line: `v0.2 (beta)`

## CLI Direction

- Terminal-first
- Boxed minimal layout
- Red accents, white text, black background-friendly
- No long prose in command output
- Optional desktop entry opens terminal and starts `infinifix doctor`

## Voice

- Short and technical
- No marketing copy in runtime UI
- Clear plan, clear risk boundary

Examples:

- `Found: Huawei MateBook D15 (2021)`
- `Audio: SOF detected`
- `Plan: install sof-firmware, set dsp_driver=3, rebuild initramfs`

## UX Rules

- Always preview plan before writing.
- Separate `safe` and `advanced` actions.
- Use plain status words: `ok`, `warn`, `skip`, `fail`.
- Support automation with `--yes` flags.
- Prevent concurrent runs with execution locking.
- Sanitize report payloads before writing archive files.

## Why Rich

Rich gives:

- readable tables/panels
- fast startup
- no heavy GUI dependency

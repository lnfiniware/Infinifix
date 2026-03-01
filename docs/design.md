# Design Notes

Repository: `https://github.com/lnfiniware/Infinifix`
Release line: `v0.1 (beta)`

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

## Why Rich

Rich gives:

- readable tables/panels
- fast startup
- no heavy GUI dependency

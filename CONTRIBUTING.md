# Contributing to InfiniFix

Repository: `https://github.com/lnfiniware/Infinifix`

## Ground Rules

- Keep fixes upstream-friendly and distro-aware.
- Prefer small, reviewable changes.
- No silent config edits: backup first.
- Keep CLI copy short and technical.

## Local Dev

```bash
git clone https://github.com/lnfiniware/Infinifix.git
cd Infinifix
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip rich pytest
PYTHONPATH=src pytest -q
```

Build C++ probe:

```bash
cmake -S src/cpp -B build/cpp
cmake --build build/cpp
```

## Commit Style

- `feat:`
- `fix:`
- `docs:`
- `packaging:`
- `test:`

## Pull Requests

- Add/update tests for logic changes.
- Include sample output for CLI changes.
- Mention distro impact in PR description.
- Update `CHANGELOG.md` for user-facing changes.

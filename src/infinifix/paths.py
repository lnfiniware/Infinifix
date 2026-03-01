from __future__ import annotations

import os
from pathlib import Path


def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(path)
    return ordered


def probe_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_probe = os.getenv("INFINIFIX_PROBE_PATH")
    if env_probe:
        candidates.append(Path(env_probe))

    candidates.extend(
        [
            Path("/usr/libexec/infinifix/probe"),
            Path("/usr/lib/infinifix/probe"),
            Path(__file__).resolve().parents[2] / "build" / "cpp" / "probe",
            Path(__file__).resolve().parents[1] / "cpp" / "build" / "probe",
        ]
    )
    return _dedupe(candidates)


def wireplumber_template_candidates() -> list[Path]:
    candidates = [
        Path(__file__).resolve().parent / "data" / "rules" / "wireplumber" / "51-infinifix.conf",
        Path("/usr/share/infinifix/data/rules/wireplumber/51-infinifix.conf"),
    ]
    return _dedupe(candidates)

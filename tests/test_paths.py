from __future__ import annotations

import os
from pathlib import Path

from infinifix.paths import probe_candidates, wireplumber_template_candidates


def test_probe_candidates_honor_env_override() -> None:
    os.environ["INFINIFIX_PROBE_PATH"] = "/tmp/custom-probe"
    candidates = probe_candidates()
    assert candidates[0] == Path("/tmp/custom-probe")
    del os.environ["INFINIFIX_PROBE_PATH"]


def test_probe_candidates_include_system_paths() -> None:
    candidates = probe_candidates()
    paths = {str(path).replace("\\", "/") for path in candidates}
    assert "/usr/libexec/infinifix/probe" in paths
    assert "/usr/lib/infinifix/probe" in paths


def test_wireplumber_template_candidates_include_shared_path() -> None:
    paths = {str(path).replace("\\", "/") for path in wireplumber_template_candidates()}
    assert "/usr/share/infinifix/data/rules/wireplumber/51-infinifix.conf" in paths

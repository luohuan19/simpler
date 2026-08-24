# Copyright (c) PyPTO Contributors.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.
# -----------------------------------------------------------------------------------------------------------

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[3]
ACTION = REPO_ROOT / ".github/actions/setup-npu-devices/action.yml"
NPU_WORKFLOWS = tuple(
    REPO_ROOT / ".github/workflows" / name
    for name in (
        "_ut-npu-a2a3.yml",
        "_ut-npu-a5.yml",
        "_st-npu-a2a3.yml",
        "_st-npu-a5.yml",
        "_st-deepseek-a2a3.yml",
    )
)


def _load_yaml(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text())
    assert isinstance(document, dict)
    return document


def _run_action(tmp_path: Path, **device_env: str) -> subprocess.CompletedProcess[str]:
    action = _load_yaml(ACTION)
    script = action["runs"]["steps"][0]["run"]
    github_env = tmp_path / "github-env"
    env = os.environ.copy()
    env.pop("DEVICE_RANGE", None)
    env.pop("DEVICE_NUM", None)
    env.update(device_env)
    env["GITHUB_ENV"] = str(github_env)
    return subprocess.run(["bash", "-c", script], env=env, text=True, capture_output=True, check=False)


def _exported_devices(tmp_path: Path) -> dict[str, str]:
    return dict(line.split("=", 1) for line in (tmp_path / "github-env").read_text().splitlines())


@pytest.mark.parametrize(
    ("device_env", "expected"),
    [
        ({}, {"DEVICE_RANGE": "0-3", "DEVICE_NUM": "4"}),
        ({"DEVICE_RANGE": "4-7"}, {"DEVICE_RANGE": "4-7", "DEVICE_NUM": "4"}),
        ({"DEVICE_RANGE": "6"}, {"DEVICE_RANGE": "6-6", "DEVICE_NUM": "1"}),
        ({"DEVICE_NUM": "2"}, {"DEVICE_RANGE": "0-1", "DEVICE_NUM": "2"}),
    ],
)
def test_action_resolves_npu_device_environment(
    tmp_path: Path, device_env: dict[str, str], expected: dict[str, str]
) -> None:
    result = _run_action(tmp_path, **device_env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _exported_devices(tmp_path) == expected


def test_action_rejects_invalid_device_range(tmp_path: Path) -> None:
    result = _run_action(tmp_path, DEVICE_RANGE="0,2")
    assert result.returncode != 0
    assert "DEVICE_RANGE" in result.stdout + result.stderr


@pytest.mark.parametrize("workflow", NPU_WORKFLOWS, ids=lambda path: path.name)
def test_standard_npu_workflows_select_devices(workflow: Path) -> None:
    document = _load_yaml(workflow)
    steps = next(iter(document["jobs"].values()))["steps"]
    setup_indexes = [
        index for index, step in enumerate(steps) if step.get("uses") == "./.github/actions/setup-npu-devices"
    ]
    assert len(setup_indexes) == 1
    first_hardware_step = next(
        index
        for index, step in enumerate(steps)
        if "pytest" in step.get("run", "") or step.get("uses") == "./.github/actions/run-onboard-dfx-smokes"
    )
    assert setup_indexes[0] < first_hardware_step

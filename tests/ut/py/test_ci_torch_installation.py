# Copyright (c) PyPTO Contributors.
# This program is free software, you can redistribute it and/or modify it under the terms and conditions of
# CANN Open Software License Agreement Version 2.0 (the "License").
# Please refer to the License for details. You may not use this file except in compliance with the License.
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
# See LICENSE in the root of the software repository for the full text of the License.
# -----------------------------------------------------------------------------------------------------------

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[3]
SETUP_VENV_ACTION = REPO_ROOT / ".github/actions/setup-venv/action.yml"
NETWORK1_STAGE_ACTION = REPO_ROOT / ".github/actions/network1-stage/action.yml"
CPU_TORCH_INSTALL = "pip install 'torch>=2.3' --index-url https://download.pytorch.org/whl/cpu"
NPU_WORKFLOWS = tuple(
    REPO_ROOT / ".github/workflows" / name
    for name in (
        "_ut-npu-a2a3.yml",
        "_ut-npu-a5.yml",
        "_st-npu-a2a3.yml",
        "_st-npu-a5.yml",
        "_st-deepseek-a2a3.yml",
        "_st-network1.yml",
    )
)


def _load_yaml(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text())
    assert isinstance(document, dict)
    return document


def _setup_venv_step(path: Path) -> dict[str, Any]:
    workflow = _load_yaml(path)
    matches = [
        step
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if step.get("uses") == "./.github/actions/setup-venv"
    ]
    assert len(matches) == 1
    return matches[0]


def test_setup_venv_installs_cpu_torch_before_packages() -> None:
    action = _load_yaml(SETUP_VENV_ACTION)
    assert action["inputs"]["install-torch"]["default"] == "true"
    script = action["runs"]["steps"][0]["run"]
    assert script.index(CPU_TORCH_INSTALL) < script.index("pip install $PACKAGES")


@pytest.mark.parametrize("workflow", NPU_WORKFLOWS, ids=lambda path: path.name)
def test_npu_workflow_does_not_disable_cpu_torch(workflow: Path) -> None:
    step = _setup_venv_step(workflow)
    assert step.get("with", {}).get("install-torch", "true") == "true"
    assert ".[test]" in step["with"]["packages"]


def test_network1_peer_installs_cpu_torch_before_test_dependencies() -> None:
    action = _load_yaml(NETWORK1_STAGE_ACTION)
    script = action["runs"]["steps"][0]["run"]
    test_install = "pip install --config-settings=build.targets=build_package_$NETWORK1_PLATFORM '.[test]'"
    assert script.index(CPU_TORCH_INSTALL) < script.index(test_install)

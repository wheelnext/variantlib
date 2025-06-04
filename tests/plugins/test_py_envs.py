from __future__ import annotations

import os
import sys
import sysconfig
import venv
from pathlib import Path

import pytest

from variantlib.plugins.py_envs import python_env


def test_system_env() -> None:
    with python_env(isolated=False) as env:
        assert env.venv_path is None
        assert env.python_executable == Path(sys.executable)


@pytest.mark.parametrize("custom", [False, True])
def test_isolated_env(
    custom: bool, tmp_path: Path, test_plugin_package_req: str
) -> None:
    if custom:
        venv.create(tmp_path, with_pip=True)
    with python_env(isolated=True, venv_path=tmp_path if custom else None) as env:
        assert env.venv_path is not None
        if custom:
            assert env.venv_path == tmp_path
        script_dir = Path(
            sysconfig.get_path("scripts", vars={"base": str(env.venv_path)})
        )
        assert env.python_executable == script_dir / (
            "python.exe" if os.name == "nt" else "python"
        )

        env.install([test_plugin_package_req])

        purelib = Path(sysconfig.get_path("purelib", vars={"base": str(env.venv_path)}))
        assert (purelib / "test_plugin_package.py").exists()

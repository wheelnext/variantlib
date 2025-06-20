from __future__ import annotations

import os
import sys
import sysconfig
import venv
from pathlib import Path

from variantlib.plugins.py_envs import python_env


def test_system_env() -> None:
    with python_env() as env:
        assert env.venv_path is None
        assert env.python_executable == Path(sys.executable)


def test_isolated_env(tmp_path: Path, test_plugin_package_req: str) -> None:
    venv.create(tmp_path, with_pip=True)
    with python_env(venv_path=tmp_path) as env:
        assert env.venv_path == tmp_path
        script_dir = Path(
            sysconfig.get_path("scripts", vars={"base": str(env.venv_path)})
        )
        assert env.python_executable == script_dir / (
            "python.exe" if os.name == "nt" else "python"
        )

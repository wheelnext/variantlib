from __future__ import annotations

import logging
import os
import pathlib
import sys
import sysconfig
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator


logger = logging.getLogger(__name__)


def _find_executable(path: pathlib.Path) -> pathlib.Path:
    """
    Detect the Python executable of a virtual environment.

    :param path: The location of the virtual environment
    :return: The Python executable
    """
    config_vars = (
        sysconfig.get_config_vars().copy()
    )  # globally cached, copy before altering it
    config_vars["base"] = str(path)
    scheme_names = sysconfig.get_scheme_names()

    if "venv" in scheme_names:
        # Python distributors with custom default installation scheme can set a
        # scheme that can't be used to expand the paths in a venv.
        # This can happen if `variantlib` itself is not installed in a venv.
        # The distributors are encouraged to set a "venv" scheme to be used for this.
        # See https://bugs.python.org/issue45413
        # and https://github.com/pypa/virtualenv/issues/2208
        paths = sysconfig.get_paths(scheme="venv", vars=config_vars)

    elif "posix_local" in scheme_names:
        # The Python that ships on Debian/Ubuntu varies the default scheme to
        # install to /usr/local
        # But it does not (yet) set the "venv" scheme.
        # If we're the Debian "posix_local" scheme is available, but "venv"
        # is not, we use "posix_prefix" instead which is venv-compatible there.
        paths = sysconfig.get_paths(scheme="posix_prefix", vars=config_vars)

    elif "osx_framework_library" in scheme_names:
        # The Python that ships with the macOS developer tools varies the
        # default scheme depending on whether the ``sys.prefix`` is part of a framework.
        # But it does not (yet) set the "venv" scheme.
        # If the Apple-custom "osx_framework_library" scheme is available but "venv"
        # is not, we use "posix_prefix" instead which is venv-compatible there.
        paths = sysconfig.get_paths(scheme="posix_prefix", vars=config_vars)

    else:
        paths = sysconfig.get_paths(vars=config_vars)

    executable = pathlib.Path(paths["scripts"]) / (
        "python.exe" if os.name == "nt" else "python"
    )
    if not executable.exists():
        msg = f"Virtual environment creation failed, executable {executable} missing"
        raise RuntimeError(msg)

    return executable


class PythonEnv:
    def __init__(self, venv_path: pathlib.Path | None = None):
        self.venv_path = venv_path

    @property
    def python_executable(self) -> pathlib.Path:
        if self.venv_path is not None:
            if not self.venv_path.exists():
                raise FileNotFoundError
            return pathlib.Path(_find_executable(self.venv_path))
        return pathlib.Path(sys.executable)


@contextmanager
def python_env(venv_path: pathlib.Path | None = None) -> Generator[PythonEnv]:
    yield PythonEnv(venv_path)

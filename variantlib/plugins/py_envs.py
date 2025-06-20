from __future__ import annotations

import functools
import logging
import os
import pathlib
import sys
import sysconfig
import tempfile
import typing
from contextlib import contextmanager
from typing import TYPE_CHECKING

from variantlib.plugins.py_backends import AutoInstallBackend
from variantlib.plugins.py_backends import PipBackend
from variantlib.plugins.py_backends import UvBackend

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Generator


logger = logging.getLogger(__name__)

Installer = typing.Literal["pip", "uv"]

INSTALLERS = typing.get_args(Installer)


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


@functools.cache
def _fs_supports_symlink() -> bool:
    """Return True if symlinks are supported"""
    # Using definition used by venv.main()
    if os.name != "nt":
        return True

    # Windows may support symlinks (setting in Windows 10)
    with tempfile.NamedTemporaryFile(prefix="variant-symlink-") as tmp_file:
        dest = f"{tmp_file}-b"
        try:
            os.symlink(tmp_file.name, dest)
            os.unlink(dest)  # noqa: PTH108
        except (OSError, NotImplementedError, AttributeError):
            return False
        return True


class PythonEnv:
    _env_backend: UvBackend | PipBackend = AutoInstallBackend()

    def __init__(self, venv_path: pathlib.Path | None = None):
        self.venv_path = venv_path

    def install(self, requirements: Collection[str]) -> None:
        """
        Install packages from PEP 508 requirements in the isolated variant plugin
        environment.

        :param requirements: PEP 508 requirement specification to install

        :note: Passing non-PEP 508 strings will result in undefined behavior, you
               *should not* rely on it. It is merely an implementation detail, it may
               change any time without warning.
        """
        if not requirements:
            return

        logger.info(
            "Installing packages in current environment:\n%(reqs)s",
            {"reqs": "\n".join(f"- {r}" for r in sorted(requirements))},
        )
        self._env_backend.install_requirements(
            requirements, py_exec=self.python_executable
        )

    @property
    def python_executable(self) -> pathlib.Path:
        if self.venv_path is not None:
            if not self.venv_path.exists():
                raise FileNotFoundError
            return pathlib.Path(_find_executable(self.venv_path))
        return pathlib.Path(sys.executable)


@contextmanager
def python_env(
    isolated: bool = False, venv_path: pathlib.Path | None = None
) -> Generator[PythonEnv]:
    if venv_path is None and isolated:
        import venv

        with tempfile.TemporaryDirectory(prefix="variantlib-venv") as temp_dir:
            logger.info(
                "Creating virtual environment in %(path)s ...",
                {"path": str(temp_dir)},
            )
            venv.EnvBuilder(
                symlinks=_fs_supports_symlink(),
                with_pip=True,
                system_site_packages=False,
                clear=True,
            ).create(temp_dir)
            yield PythonEnv(pathlib.Path(temp_dir))
    else:
        yield PythonEnv(venv_path)

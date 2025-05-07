# SPDX-License-Identifier: MIT

"""
This file is imported from https://github.com/pypa/build/blob/35d86b8/src/build/env.py
Some modifications have been made to make the code standalone.

If possible, this code should stay as close to the original as possible.
"""

from __future__ import annotations

import abc
import contextlib
import functools
import logging
import os
import pathlib
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import typing
from itertools import chain
from typing import TYPE_CHECKING

import pip._internal.configuration

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Mapping

if sys.version_info >= (3, 11):
    from typing import Self

else:
    from typing_extensions import Self

logger = logging.getLogger(__name__)

Installer = typing.Literal["pip", "uv"]

INSTALLERS = typing.get_args(Installer)


def _get_pip_index_urls():
    # Load pip configuration
    configuration = pip._internal.configuration.Configuration(  # noqa: SLF001
        isolated=False, load_only=None
    )
    configuration.load()

    def unpack_pip_index_config_value(val: str | list[str] | tuple[str]) -> list[str]:
        val: list[str] | tuple[str]
        return [v.strip() for v in val.split("\n") if v.strip()]

    # Retrieve index-url and extra-index-url values
    # index_url = configuration.get_value("global.index-url")
    # extra_index_urls = configuration.get_value("global.extra-index-url")
    index_url = []
    extra_index_urls = []
    for key, val in configuration.items():
        if key in ["global.index-url", "install.index-url"]:
            index_url.extend(unpack_pip_index_config_value(val))
        if key in ["global.extra-index-url", "install.extra-index-url"]:
            extra_index_urls.extend(unpack_pip_index_config_value(val))

    return list(set(index_url)), list(set(extra_index_urls))


def _run_subprocess(cmd: list[str], env: Mapping[str, str] | None = None) -> bool:
    try:
        subprocess.run(cmd, capture_output=True, check=True, env=env)  # noqa: S603
    except subprocess.CalledProcessError as exc:
        logger.exception(exc.stdout.decode("utf-8"), exc_info=False)
        logger.exception(exc.stderr.decode("utf-8"), exc_info=False)
        return False

    return True


def _find_executable_and_scripts(path: str) -> tuple[str, str, str]:
    """
    Detect the Python executable and script folder of a virtual environment.

    :param path: The location of the virtual environment
    :return: The Python executable, script folder, and purelib folder
    """
    config_vars = (
        sysconfig.get_config_vars().copy()
    )  # globally cached, copy before altering it
    config_vars["base"] = path
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

    executable = os.path.join(  # noqa: PTH118
        paths["scripts"], "python.exe" if os.name == "nt" else "python"
    )
    if not os.path.exists(executable):  # noqa: PTH110
        msg = f"Virtual environment creation failed, executable {executable} missing"
        raise RuntimeError(msg)

    return executable, paths["scripts"], paths["purelib"]


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


class _EnvBackend(abc.ABC):  # pragma: no cover
    @contextlib.contextmanager
    def prepare_requirements(
        self,
        requirements: Collection[str],
    ) -> typing.Generator[pathlib.Path, None, None]:
        """
        Prepare requirements for installation.

        :param requirements: PEP 508 requirement specification to install
        :return: A list of requirements to install
        """
        # pip does not honour environment markers in command line arguments
        # but it does from requirement files.
        with tempfile.NamedTemporaryFile(
            "w",
            prefix="variants-plugins-reqs-",
            suffix=".txt",
            encoding="utf-8",
        ) as _req_file:
            req_file = pathlib.Path(_req_file.name)

            with req_file.open("w", encoding="utf-8") as rf:
                rf.write(os.linesep.join(requirements))

            yield req_file

    @abc.abstractmethod
    def install_requirements(
        self, requirements: Collection[str], py_exec: str | None = None
    ) -> None: ...

    @property
    @abc.abstractmethod
    def display_name(self) -> str: ...


class _UvBackend(_EnvBackend):
    display_name = "uv"

    def install_requirements(
        self, requirements: Collection[str], py_exec: str | None = None
    ) -> None:
        index_urls, extra_index_urls = _get_pip_index_urls()

        with self.prepare_requirements(requirements) as req_file:
            cmd = [
                shutil.which("uv"),
                "pip",
                "install",
                "--python",
                sys.executable if py_exec is None else py_exec,
                "--no-config",
                "--no-managed-python",
                "--no-progress",
                "--no-python-downloads",
                *chain.from_iterable([["--default-index", idx] for idx in index_urls]),
                *chain.from_iterable([["--index", idx] for idx in extra_index_urls]),
                "-r",
                req_file.resolve(),
            ]
            _run_subprocess(cmd)


class _PipBackend(_EnvBackend):
    display_name = "pip"

    def install_requirements(
        self, requirements: Collection[str], py_exec: str | None = None
    ) -> None:
        index_urls, extra_index_urls = _get_pip_index_urls()

        with self.prepare_requirements(requirements) as req_file:
            cmd = [
                sys.executable if py_exec is None else py_exec,
                "-m",
                "pip",
                "install",
                "--use-pep517",
                "--no-warn-script-location",
                "--no-compile",
                *chain.from_iterable(
                    [["--index-url", idx] for idx in index_urls]
                    if py_exec is not None
                    else []
                ),
                *chain.from_iterable(
                    [["--extra-index-url", idx] for idx in extra_index_urls]
                    if py_exec is not None
                    else []
                ),
                "-r",
                req_file.resolve(),
            ]
            _run_subprocess(cmd)


class BasePythonEnv(abc.ABC):
    """Base Installation Environment."""

    python_executable: str | None = None
    scripts_dir: str | None = None
    _env_backend: _EnvBackend

    def __init__(self) -> None:
        if shutil.which("uv") is not None:
            self._env_backend = _UvBackend()
        else:
            self._env_backend = _PipBackend()

    @abc.abstractmethod
    def __enter__(self) -> Self:
        """
        Enter the environment.
        """

    @abc.abstractmethod
    def __exit__(self, *args: object) -> None:
        """
        Exit the environment.
        """

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


class NonIsolatedPythonEnv(BasePythonEnv):
    """
    Non-Isolated environment which supports several different underlying
    implementations.
    """

    def __enter__(self) -> Self:
        logger.info(
            "Using environment: %(env)s ...",
            {"env": self._env_backend.display_name},
        )

        return self

    def __exit__(self, *args: object) -> None:
        pass


class IsolatedPythonEnv(BasePythonEnv):
    """
    Isolated environment which supports several different underlying
    implementations.
    """

    def __enter__(self) -> Self:
        try:
            self._path = pathlib.Path(tempfile.mkdtemp(prefix="variant-env-"))

            logger.info(
                "Creating isolated environment: %(env)s ...",
                {"env": self._env_backend.display_name},
            )
            self.python_executable, self.scripts_dir = self._create_venv(self._path)

        except Exception:  # cleanup folder if creation fails
            self.__exit__(*sys.exc_info())
            raise

        return self

    def __exit__(self, *args: object) -> None:
        # in case the user already deleted skip remove
        if os.path.exists(self._path):  # noqa: PTH110
            shutil.rmtree(self._path)
        self.python_executable, self.scripts_dir = None, None

    def _create_venv(self, path: pathlib.Path) -> tuple[str, str]:
        try:
            import virtualenv

            result = virtualenv.cli_run(
                [
                    str(path.resolve()),
                    "--no-setuptools",
                    "--no-wheel",
                    "--no-pip",
                    # below is necessary until `variantlib` is vendored into PIP
                    "--system-site-packages",
                ],
                setup_logging=False,
            )

            # The creator attributes are `pathlib.Path`s.
            python_executable = str(result.creator.exe)
            scripts_dir = str(result.creator.script_dir)

        except (ImportError, ModuleNotFoundError):
            import venv

            try:
                venv.EnvBuilder(
                    symlinks=_fs_supports_symlink(),
                    with_pip=True,
                    system_site_packages=True,
                    clear=True,
                ).create(path)
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    exc, "Failed to create venv. Maybe try installing virtualenv."
                ) from None

            python_executable, scripts_dir, _ = _find_executable_and_scripts(path)

        return python_executable, scripts_dir

    def install(self, requirements: Collection[str]) -> None:
        if self.python_executable is None:
            raise RuntimeError("The virtual environment is not created yet.")
        super().install(requirements)

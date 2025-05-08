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
from typing import TYPE_CHECKING

from variantlib.plugins.py_backends import AutoInstallBackend
from variantlib.plugins.py_backends import PipBackend
from variantlib.plugins.py_backends import UvBackend

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Generator

if sys.version_info >= (3, 11):
    from typing import Self

else:
    from typing_extensions import Self

logger = logging.getLogger(__name__)

Installer = typing.Literal["pip", "uv"]

INSTALLERS = typing.get_args(Installer)


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


class BasePythonEnv(abc.ABC):
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


class IsolatedPythonEnvMixin:
    _venv_path: pathlib.Path | None = None

    def __init__(self) -> None:
        raise NotImplementedError("This path is not yet supported")

    @property
    def python_executable(self) -> pathlib.Path:
        return self._get_venv_path(0)

    @property
    def script_dir(self) -> pathlib.Path:
        return self._get_venv_path(1)

    @property
    def package_dir(self) -> pathlib.Path:
        return self._get_venv_path(2)

    def _get_venv_path(self, idx: int) -> pathlib.Path:
        if self._venv_path is None or not self._venv_path.exists():
            raise FileNotFoundError
        assert 0 <= idx <= 2
        return pathlib.Path(_find_executable_and_scripts(str(self._venv_path))[idx])


class BasePythonInstallerEnv(BasePythonEnv):
    """Base Installation Environment."""

    _env_backend: UvBackend | PipBackend = AutoInstallBackend()

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
    @abc.abstractmethod
    def python_executable(self) -> pathlib.Path | None: ...


class NonIsolatedPythonInstallerEnv(BasePythonInstallerEnv):
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

    @property
    def python_executable(self) -> None:
        return None


class IsolatedPythonInstallerEnv(IsolatedPythonEnvMixin, BasePythonInstallerEnv):
    """
    Isolated environment which supports several different underlying
    implementations.
    """

    def __init__(self) -> None:
        raise NotImplementedError("This path is not yet supported")
        super().__init__()

    def __enter__(self) -> Self:
        try:
            self._venv_path = pathlib.Path(tempfile.mkdtemp(prefix="variant-env-"))

            logger.info(
                "Creating isolated environment: %(env)s ...",
                {"env": self._env_backend.display_name},
            )
            self._create_venv(self._venv_path)

        except Exception:  # cleanup folder if creation fails
            self.__exit__(*sys.exc_info())
            raise

        return self

    def __exit__(self, *args: object) -> None:
        # in case the user already deleted skip remove
        if self._venv_path is None or not self._venv_path.exists():
            return
        shutil.rmtree(self._venv_path)

    def _create_venv(self, path: pathlib.Path) -> None:
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

    def install(self, requirements: Collection[str]) -> None:
        if self._venv_path is None:
            raise RuntimeError("The virtual environment is not created yet.")
        super().install(requirements)


@contextlib.contextmanager
def PythonInstallerEnv(  # noqa: N802
    isolated: bool,
) -> Generator[IsolatedPythonInstallerEnv | NonIsolatedPythonInstallerEnv]:
    try:
        if isolated:
            # original_sys_path = sys.path.copy()
            # with IsolatedPythonInstallerEnv() as ctx:
            #     sys.path.insert(0, str(ctx.package_dir))
            #     yield ctx
            #     sys.path = original_sys_path
            raise NotImplementedError("This path is not yet supported")  # noqa: TRY301
        else:
            with NonIsolatedPythonInstallerEnv() as ctx:
                yield ctx

    except Exception:
        logger.exception("An error occured during plugin installation.")


class ExternalNonIsolatedPythonEnv(BasePythonEnv):
    """
    Externally managed non-isolated python environment.
    """

    def __enter__(self) -> Self:
        logger.info("Using externally managed python environment")
        return self

    def __exit__(self, *args: object) -> None:
        pass


class ExternalIsolatedPythonEnv(IsolatedPythonEnvMixin, BasePythonEnv):
    """
    Externally managed isolated python environment.
    """

    def __init__(self, venv_path: pathlib.Path | None) -> None:
        raise NotImplementedError("This path is not yet supported")
        if venv_path is None or not (venv_path := pathlib.Path(venv_path)).exists():
            raise FileNotFoundError
        self._venv_path = venv_path

    def __enter__(self) -> Self:
        logger.info(
            "Using externally managed python environment isolated at `%s`",
            self._venv_path,
        )
        return self

    def __exit__(self, *args: object) -> None:
        pass


@contextlib.contextmanager
def ExternalPythonEnv(  # noqa: N802
    venv_path: pathlib.Path | None,
) -> Generator[ExternalIsolatedPythonEnv | ExternalNonIsolatedPythonEnv]:
    try:
        if venv_path is not None:
            # original_sys_path = sys.path.copy()
            # with ExternalIsolatedPythonEnv(venv_path=venv_path) as ctx:
            #     sys.path.insert(0, str(ctx.package_dir))
            #     yield ctx
            #     sys.path = original_sys_path
            raise NotImplementedError("This path is not yet supported")  # noqa: TRY301
        else:
            with ExternalNonIsolatedPythonEnv() as ctx:
                yield ctx

    except Exception:
        logger.exception("An error occured during plugin installation.")


@contextlib.contextmanager
def AutoPythonEnv(  # noqa: N802
    use_auto_install: bool, isolated: bool = True, venv_path: pathlib.Path | None = None
) -> Generator[
    IsolatedPythonInstallerEnv
    | NonIsolatedPythonInstallerEnv
    | ExternalIsolatedPythonEnv
    | ExternalNonIsolatedPythonEnv
]:
    if use_auto_install:
        if venv_path is not None:
            raise ValueError("`venv_path` must be None if `use_auto_install` is True.")
        with PythonInstallerEnv(isolated=isolated) as ctx:
            yield ctx
    else:
        with ExternalPythonEnv(venv_path=venv_path) as ctx:
            yield ctx


# Helper Tuples
ISOLATED_PYTHON_ENVS = (IsolatedPythonInstallerEnv, ExternalIsolatedPythonEnv)
NON_ISOLATED_PYTHON_ENVS = (NonIsolatedPythonInstallerEnv, ExternalNonIsolatedPythonEnv)
INSTALLER_PYTHON_ENVS = (IsolatedPythonInstallerEnv, NonIsolatedPythonInstallerEnv)
EXTERNAL_PYTHON_ENVS = (ExternalIsolatedPythonEnv, ExternalNonIsolatedPythonEnv)

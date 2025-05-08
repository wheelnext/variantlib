from __future__ import annotations

import abc
import contextlib
import logging
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import typing
from itertools import chain
from typing import TYPE_CHECKING

import pip._internal.configuration

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Generator
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

Installer = typing.Literal["pip", "uv"]

INSTALLERS = typing.get_args(Installer)


def _get_pip_index_urls() -> tuple[list[str], list[str]]:
    # Load pip configuration
    configuration = pip._internal.configuration.Configuration(  # noqa: SLF001
        isolated=False, load_only=None
    )
    configuration.load()

    def unpack_pip_index_config_value(val: str) -> list[str]:
        # val: list[str] | tuple[str]
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


class _BaseBackend(abc.ABC):
    @contextlib.contextmanager
    def prepare_requirements(
        self,
        requirements: Collection[str],
    ) -> Generator[pathlib.Path, None, None]:
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
        self, requirements: Collection[str], py_exec: pathlib.Path | None = None
    ) -> None: ...

    @property
    @abc.abstractmethod
    def display_name(self) -> str: ...


class UvBackend(_BaseBackend):
    display_name: str = "uv"
    _uv_exec_path: str | None = shutil.which("uv")

    def install_requirements(
        self, requirements: Collection[str], py_exec: pathlib.Path | None = None
    ) -> None:
        if self._uv_exec_path is None or not pathlib.Path(self._uv_exec_path).exists():
            raise FileNotFoundError("Can not find `uv` executable")

        index_urls, extra_index_urls = _get_pip_index_urls()

        with self.prepare_requirements(requirements) as req_file:
            cmd: list[str] = [
                self._uv_exec_path,
                "pip",
                "install",
                "--python",
                sys.executable if py_exec is None else str(py_exec),
                "--no-config",
                "--no-managed-python",
                "--no-progress",
                "--no-python-downloads",
                *chain.from_iterable([["--default-index", idx] for idx in index_urls]),
                *chain.from_iterable([["--index", idx] for idx in extra_index_urls]),
                "-r",
                str(req_file.resolve()),
            ]
            _run_subprocess(cmd)


class PipBackend(_BaseBackend):
    display_name = "pip"

    def install_requirements(
        self, requirements: Collection[str], py_exec: pathlib.Path | None = None
    ) -> None:
        index_urls, extra_index_urls = _get_pip_index_urls()

        with self.prepare_requirements(requirements) as req_file:
            cmd: list[str] = [
                sys.executable if py_exec is None else str(py_exec),
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
                str(req_file.resolve()),
            ]
            _run_subprocess(cmd)


def AutoInstallBackend() -> UvBackend | PipBackend:  # noqa: N802
    if shutil.which("uv") is not None:
        return UvBackend()

    return PipBackend()

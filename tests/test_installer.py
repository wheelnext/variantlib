# SPDX-License-Identifier: MIT

"""
This file is imported from https://github.com/pypa/build/blob/35d86b8/tests/test_util.py
Some modifications have been made to make the code standalone.

If possible, this code should stay as close to the original as possible.
"""

from __future__ import annotations

import importlib.util
import logging
import shutil
import subprocess
import sys
import sysconfig
import typing
from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.version import Version

import variantlib.installer as vinstall

if typing.TYPE_CHECKING:
    import pytest_mock

IS_PYPY = sys.implementation.name == "pypy"
IS_WINDOWS = sys.platform.startswith("win")

MISSING_UV = importlib.util.find_spec("uv") is None and not shutil.which("uv")


@pytest.fixture
def local_pip(monkeypatch):
    monkeypatch.setattr(vinstall._PipBackend, "_has_valid_outer_pip", None)  # noqa: SLF001


@pytest.fixture(autouse=True, params=[False])
def has_virtualenv(request, monkeypatch):
    if request.param is not None:
        monkeypatch.setattr(vinstall._PipBackend, "_has_virtualenv", request.param)  # noqa: SLF001


@pytest.mark.isolated
def test_isolation():
    subprocess.check_call([sys.executable, "-c", "import variantlib.installer"])  # noqa: S603
    with vinstall.DefaultIsolatedEnv() as env:  # noqa: SIM117
        with pytest.raises(subprocess.CalledProcessError):  # noqa: PT012
            debug = "import sys; import os; print(os.linesep.join(sys.path));"
            subprocess.check_call(  # noqa: S603
                [env.python_executable, "-c", f"{debug} import variantlib.installer"]
            )


@pytest.mark.skipif(IS_PYPY, reason="PyPy3 uses get path to create and provision venv")
@pytest.mark.skipif(sys.platform != "darwin", reason="workaround for Apple Python")
def test_can_get_venv_paths_with_conflicting_default_scheme(
    mocker: pytest_mock.MockerFixture,
):
    get_scheme_names = mocker.patch(
        "sysconfig.get_scheme_names", return_value=("osx_framework_library",)
    )
    with vinstall.DefaultIsolatedEnv():
        pass
    assert get_scheme_names.call_count == 1


SCHEME_NAMES = sysconfig.get_scheme_names()


@pytest.mark.skipif(
    "posix_local" not in SCHEME_NAMES, reason="workaround for Debian/Ubuntu Python"
)
@pytest.mark.skipif(
    "venv" in SCHEME_NAMES, reason="different call if venv is in scheme names"
)
def test_can_get_venv_paths_with_posix_local_default_scheme(
    mocker: pytest_mock.MockerFixture,
):
    get_paths = mocker.spy(sysconfig, "get_paths")
    # We should never call this, but we patch it to ensure failure if we do
    get_default_scheme = mocker.patch(
        "sysconfig.get_default_scheme", return_value="posix_local"
    )
    with vinstall.DefaultIsolatedEnv():
        pass
    get_paths.assert_called_once_with(scheme="posix_prefix", vars=mocker.ANY)
    assert get_default_scheme.call_count == 0


def test_venv_executable_missing_post_creation(
    mocker: pytest_mock.MockerFixture,
):
    venv_create = mocker.patch("venv.EnvBuilder.create")
    with pytest.raises(  # noqa: SIM117
        RuntimeError, match="Virtual environment creation failed, executable .* missing"
    ):
        with vinstall.DefaultIsolatedEnv():
            pass
    assert venv_create.call_count == 1


@typing.no_type_check
def test_isolated_env_abstract():
    with pytest.raises(TypeError):
        vinstall.IsolatedEnv()

    class PartialEnvA(vinstall.IsolatedEnv):
        @property
        def executable(self):
            raise NotImplementedError

    with pytest.raises(TypeError):
        PartialEnvA()

    class PartialEnvB(vinstall.IsolatedEnv):
        def make_extra_environ(self):
            raise NotImplementedError

    with pytest.raises(TypeError):
        PartialEnvB()


@pytest.mark.pypy3323bug
def test_isolated_env_log(
    caplog: pytest.LogCaptureFixture,
    mocker: pytest_mock.MockerFixture,
):
    caplog.set_level(logging.DEBUG)
    mocker.patch("variantlib.installer.run_subprocess")

    with vinstall.DefaultIsolatedEnv() as env:
        env.install(["something"])

    assert [(record.levelname, record.message) for record in caplog.records] == [
        ("INFO", "Creating isolated environment: venv+pip ..."),
        ("INFO", "Installing packages in isolated environment:\n- something"),
    ]


@pytest.mark.isolated
@pytest.mark.usefixtures("local_pip")
def test_default_pip_is_never_too_old():
    with vinstall.DefaultIsolatedEnv() as env:
        version = subprocess.check_output(  # noqa: S603
            [env.python_executable, "-c", 'import pip; print(pip.__version__, end="")'],
            encoding="utf-8",
        )
        assert Version(version) >= Version("19.1")


@pytest.mark.isolated
@pytest.mark.parametrize("pip_version", ["20.2.0", "20.3.0", "21.0.0", "21.0.1"])
@pytest.mark.parametrize("arch", ["x86_64", "arm64"])
@pytest.mark.usefixtures("local_pip")
def test_pip_needs_upgrade_mac_os_11(
    mocker: pytest_mock.MockerFixture,
    pip_version: str,
    arch: str,
):
    run_subprocess = mocker.patch("variantlib.installer.run_subprocess")
    mocker.patch("platform.system", return_value="Darwin")
    mocker.patch("platform.mac_ver", return_value=("11.0", ("", "", ""), arch))
    mocker.patch(
        "variantlib.installer.distributions",
        return_value=(SimpleNamespace(version=pip_version),),
    )

    min_pip_version = "20.3.0" if arch == "x86_64" else "21.0.1"

    with vinstall.DefaultIsolatedEnv() as env:
        if Version(pip_version) < Version(min_pip_version):
            assert run_subprocess.call_args_list == [
                mocker.call(
                    [
                        env.python_executable,
                        "-Im",
                        "pip",
                        "install",
                        f"pip>={min_pip_version}",
                    ]
                ),
                mocker.call(
                    [
                        env.python_executable,
                        "-Im",
                        "pip",
                        "uninstall",
                        "-y",
                        "setuptools",
                    ]
                ),
            ]
        else:
            run_subprocess.assert_called_once_with(
                [env.python_executable, "-Im", "pip", "uninstall", "-y", "setuptools"],
            )


@pytest.mark.parametrize(
    "has_symlink", [True, False] if sys.platform.startswith("win") else [True]
)
def test_venv_symlink(
    mocker: pytest_mock.MockerFixture,
    has_symlink: bool,
):
    if has_symlink:
        mocker.patch("os.symlink")
        mocker.patch("os.unlink")
    else:
        mocker.patch("os.symlink", side_effect=OSError())

    # Cache must be cleared to rerun
    vinstall._fs_supports_symlink.cache_clear()  # noqa: SLF001
    supports_symlink = vinstall._fs_supports_symlink()  # noqa: SLF001
    vinstall._fs_supports_symlink.cache_clear()  # noqa: SLF001

    assert supports_symlink is has_symlink


def test_install_short_circuits(
    mocker: pytest_mock.MockerFixture,
):
    with vinstall.DefaultIsolatedEnv() as env:
        install_requirements = mocker.patch.object(
            env._env_backend,  # noqa: SLF001
            "install_requirements",
        )

        env.install([])
        install_requirements.assert_not_called()

        env.install(["foo"])
        install_requirements.assert_called_once()


@pytest.mark.usefixtures("local_pip")
def test_default_impl_install_cmd_well_formed(mocker: pytest_mock.MockerFixture):
    with vinstall.DefaultIsolatedEnv() as env:
        run_subprocess = mocker.patch("variantlib.installer.run_subprocess")

        env.install(["some", "requirements"])

        run_subprocess.assert_called_once_with(
            [
                env.python_executable,
                "-Im",
                "pip",
                "install",
                "--use-pep517",
                "--no-warn-script-location",
                "--no-compile",
                "-r",
                mocker.ANY,
            ]
        )


@pytest.mark.skipif(IS_PYPY, reason="uv cannot find PyPy executable")
@pytest.mark.skipif(MISSING_UV, reason="uv executable not found")
def test_uv_impl_install_cmd_well_formed(mocker: pytest_mock.MockerFixture):
    with vinstall.DefaultIsolatedEnv(installer="uv") as env:
        run_subprocess = mocker.patch("variantlib.installer.run_subprocess")

        env.install(["some", "requirements"])

        (install_call,) = run_subprocess.call_args_list
        assert len(install_call.args) == 1
        assert install_call.args[0][1:] == [
            "pip",
            "install",
            "some",
            "requirements",
        ]
        assert len(install_call.kwargs) == 1
        assert install_call.kwargs["env"]["VIRTUAL_ENV"] == env.path


@pytest.mark.usefixtures("local_pip")
@pytest.mark.parametrize(
    ("installer", "env_backend_display_name", "has_virtualenv"),
    [
        ("pip", "venv+pip", False),
        ("pip", "virtualenv+pip", True),
        ("pip", "virtualenv+pip", None),  # Fall-through
        pytest.param(
            "uv",
            "venv+uv",
            None,
            marks=pytest.mark.skipif(MISSING_UV, reason="uv executable not found"),
        ),
    ],
    indirect=("has_virtualenv",),
)
def test_venv_creation(
    installer: vinstall.Installer,
    env_backend_display_name: str,
):
    with vinstall.DefaultIsolatedEnv(installer=installer) as env:
        assert env._env_backend.display_name == env_backend_display_name  # noqa: SLF001


@pytest.mark.network
@pytest.mark.usefixtures("local_pip")
@pytest.mark.parametrize(
    "installer",
    [
        "pip",
        pytest.param(
            "uv",
            marks=[
                pytest.mark.xfail(
                    IS_PYPY and IS_WINDOWS and sys.version_info < (3, 9),
                    reason="uv cannot find PyPy 3.8 executable on Windows",
                ),
                pytest.mark.skipif(MISSING_UV, reason="uv executable not found"),
            ],
        ),
    ],
)
def test_requirement_installation(
    package_test_flit: str,
    installer: vinstall.Installer,
):
    with vinstall.DefaultIsolatedEnv(installer=installer) as env:
        env.install([f"test-flit @ {Path(package_test_flit).as_uri()}"])


@pytest.mark.skipif(MISSING_UV, reason="uv executable not found")
def test_external_uv_detection_success(
    caplog: pytest.LogCaptureFixture,
    mocker: pytest_mock.MockerFixture,
):
    mocker.patch.dict(sys.modules, {"uv": None})

    with vinstall.DefaultIsolatedEnv(installer="uv"):
        pass

    assert any(
        r.message
        == (
            "Using external uv from "
            f"`{shutil.which('uv', path=sysconfig.get_path('scripts'))}`"
        )
        for r in caplog.records
    )


def test_external_uv_detection_failure(
    mocker: pytest_mock.MockerFixture,
):
    mocker.patch.dict(sys.modules, {"uv": None})
    mocker.patch("shutil.which", return_value=None)

    with pytest.raises(RuntimeError, match="uv executable not found"):  # noqa: SIM117
        with vinstall.DefaultIsolatedEnv(installer="uv"):
            pass

from __future__ import annotations

from typing import TYPE_CHECKING

from variantlib.commands.main import main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_analyze_wheel_regular(
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
    test_plugin_package_wheel_path: Path,
) -> None:
    main(["analyze-wheel", "-i", str(test_plugin_package_wheel_path)])
    assert capsys.readouterr().out == ""
    assert "Standard Wheel" in caplog.text


def test_analyze_wheel_null_variant(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
    test_plugin_package_wheel_path: Path,
) -> None:
    main(
        [
            "analyze-wheel",
            "-i",
            "tests/artifacts/test_plugin_package-0-py3-none-any-00000000.whl",
        ]
    )
    assert (
        capsys.readouterr().out
        == """\
############################## Variant: `00000000` #############################
################################################################################
"""
    )


def test_analyze_wheel_variant(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
    test_plugin_package_wheel_path: Path,
) -> None:
    main(
        [
            "analyze-wheel",
            "-i",
            "tests/artifacts/test_plugin_package-0-py3-none-any-5d8be4b9.whl",
        ]
    )
    assert (
        capsys.readouterr().out
        == """\
############################## Variant: `5d8be4b9` #############################
installable_plugin :: feat1 :: val1c
installable_plugin :: feat2 :: val2b
################################################################################
"""
    )

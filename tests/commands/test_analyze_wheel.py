from __future__ import annotations

from typing import TYPE_CHECKING

from variantlib.commands.main import main
from variantlib.constants import NULL_VARIANT_LABEL

if TYPE_CHECKING:
    import pytest


def test_analyze_wheel_regular(
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(
        [
            "analyze-wheel",
            "-i",
            "tests/artifacts/test-package/dist/test_package-0-py3-none-any.whl",
        ]
    )
    assert capsys.readouterr().out == ""
    assert "Standard Wheel" in caplog.text


def test_analyze_wheel_null_variant(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(
        [
            "analyze-wheel",
            "-i",
            "tests/artifacts/test-package/dist/test_package-0-py3-none-any-"
            f"{NULL_VARIANT_LABEL}.whl",
        ]
    )
    assert (
        capsys.readouterr().out
        == f"""\
############################## Variant: `{NULL_VARIANT_LABEL}` \
#############################
################################################################################
"""
    )


def test_analyze_wheel_variant(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(
        [
            "analyze-wheel",
            "-i",
            "tests/artifacts/test-package/dist/test_package-0-py3-none-any-5d8be4b9857b08d4.whl",
        ]
    )
    assert (
        capsys.readouterr().out
        == """\
############################## Variant: `5d8be4b9857b08d4` #############################
installable_plugin :: feat1 :: val1c
installable_plugin :: feat2 :: val2b
################################################################################
"""
    )


def test_analyze_wheel_variant_custom_label(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(
        [
            "analyze-wheel",
            "-i",
            "tests/artifacts/test-package/dist/test_package-0-py3-none-any-foo.whl",
        ]
    )
    assert (
        capsys.readouterr().out
        == """\
############################## Variant: `60567bd9089307ec` #############################
installable_plugin :: feat1 :: val1c
################################################################################
"""
    )

from __future__ import annotations

import pytest

from variantlib.commands.main import main


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
            "tests/artifacts/test-package/dist/test_package-0-py3-none-any-00000000.whl",
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
) -> None:
    main(
        [
            "analyze-wheel",
            "-i",
            "tests/artifacts/test-package/dist/test_package-0-py3-none-any-5d8be4b9.whl",
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
############################## Variant: `60567bd9` #############################
installable_plugin :: feat1 :: val1c
################################################################################
"""
    )


@pytest.mark.parametrize("suffix", ["00000000", "null"])
def test_analyze_wheel_variant_null(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
    suffix: str,
) -> None:
    main(
        [
            "analyze-wheel",
            "-i",
            f"tests/artifacts/test-package/dist/test_package-0-py3-none-any-{suffix}.whl",
        ]
    )
    assert (
        capsys.readouterr().out
        == """\
############################## Variant: `00000000` #############################
################################################################################
"""
    )

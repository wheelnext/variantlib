from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import pytest

from tests.utils import assert_zips_equal
from variantlib.commands.main import main
from variantlib.constants import NULL_VARIANT_LABEL

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@pytest.fixture
def non_variant_wheel(test_artifact_path: Path) -> Path:
    whl_f = test_artifact_path / "test-package/dist/test_package-0-py3-none-any.whl"
    if not whl_f.exists() or not whl_f.is_file():
        raise FileNotFoundError(f"Test package wheel not found: `{whl_f}`")
    return whl_f


@pytest.fixture
def mocked_plugin_reqs(
    mocker: MockerFixture,
    test_plugin_package_req: str,
) -> None:
    mocker.patch(
        "variantlib.models.variant_info.VariantInfo.get_provider_requires"
    ).return_value = [test_plugin_package_req]


@pytest.mark.parametrize(
    ("label", "properties"),
    [
        # Null Variant
        (NULL_VARIANT_LABEL, None),
        # Variant 1
        (
            "5d8be4b9857b08d4",
            [
                "installable_plugin::feat1::val1c",
                "installable_plugin::feat2::val2b",
            ],
        ),
        # Variant 2
        ("60567bd9089307ec", ["installable_plugin::feat1::val1c"]),
        ("60567bd9089307ec", ["installable_plugin :: feat1::val1c"]),
        ("60567bd9089307ec", ["installable_plugin::feat1 :: val1c"]),
        ("60567bd9089307ec", ["installable_plugin :: feat1 :: val1c"]),
        # Variant 3
        ("fbe8264248d394d8", ["installable_plugin::feat2::val2b"]),
        ("fbe8264248d394d8", ["installable_plugin :: feat2::val2b"]),
        ("fbe8264248d394d8", ["installable_plugin::feat2 :: val2b"]),
        ("fbe8264248d394d8", ["installable_plugin :: feat2 :: val2b"]),
        # Custom labels
        ("foo", ["installable_plugin::feat1::val1c"]),
        ("bar", ["installable_plugin::feat2::val2b"]),
    ],
)
def test_make_variant(
    label: str,
    properties: list[str] | None,
    non_variant_wheel: Path,
    test_artifact_path: Path,
    tmp_path: Path,
    mocked_plugin_reqs: None,
) -> None:
    cmd_args = [
        "make-variant",
        "-f",
        str(non_variant_wheel.resolve()),
        "-o",
        str(tmp_path),
        "--pyproject-toml",
        str((test_artifact_path / "test-package/pyproject.toml").resolve()),
    ]

    if properties is None:
        cmd_args.append("--null-variant")
    else:
        cmd_args.extend(
            itertools.chain.from_iterable(["-p", vprop] for vprop in properties)
        )

    if label != "null":
        cmd_args.append(f"--variant-label={label}")

    main([*cmd_args])

    target_variant_wheel = (
        non_variant_wheel.parent / f"test_package-0-py3-none-any-{label}.whl"
    )

    output_f = tmp_path / target_variant_wheel.name
    assert output_f.exists(), (
        f"Expected output file {output_f} to exist, but it does not."
    )

    assert_zips_equal(target_variant_wheel, output_f)


@pytest.mark.parametrize(
    ("args", "error"),
    [
        ([], "error: one of the arguments -p/--property --null-variant is required"),
        (["--property=x::y"], "argument -p/--property: invalid from_str value"),
        (
            ["--property=x::y::z", "--variant-label=0123456789abcdefg"],
            "error: invalid variant label",
        ),
        (
            ["--property=x::y::z", "--variant-label=null"],
            "error: invalid variant label",
        ),
        (
            ["--null-variant", "--variant-label=null"],
            "error: --variant-label cannot be used with --null-variant",
        ),
    ],
)
def test_make_variant_error(
    args: list[str],
    error: str,
    non_variant_wheel: Path,
    test_artifact_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pyproject_f = test_artifact_path / "test-package/pyproject.toml"

    with pytest.raises(SystemExit):
        main(
            [
                "make-variant",
                "-f",
                str(non_variant_wheel.resolve()),
                "-o",
                str(tmp_path),
                "--pyproject-toml",
                str(pyproject_f.resolve()),
                *args,
            ]
        )

    assert error in capsys.readouterr().err

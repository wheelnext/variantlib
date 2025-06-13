from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import pytest

from tests.utils import assert_zips_equal
from variantlib.commands.main import main

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def non_variant_wheel(test_artifact_path: Path) -> Path:
    whl_f = test_artifact_path / "test-package/dist/test_package-0-py3-none-any.whl"
    if not whl_f.exists() or not whl_f.is_file():
        raise FileNotFoundError(f"Test package wheel not found: `{whl_f}`")
    return whl_f


@pytest.fixture
def pyproject_toml(test_artifact_path: Path) -> Path:
    pyproject_f = test_artifact_path / "test-package/pyproject.toml"
    if not pyproject_f.exists() or not pyproject_f.is_file():
        raise FileNotFoundError(
            f"Test package pyproject.toml not found: `{pyproject_f}`"
        )
    return pyproject_f


def validate_make_variant(
    tmp_dir_path: Path,
    non_variant_wheel: Path,
    pyproject_toml: Path,
    target_variant_wheel: Path,
    properties: list[str] | None = None,
) -> None:
    cmd_args = [
        "make-variant",
        "-f",
        str(non_variant_wheel.resolve()),
        "-o",
        str(tmp_dir_path),
        "--pyproject-toml",
        str(pyproject_toml.resolve()),
    ]

    if properties is None:
        cmd_args.append("--null-variant")
    else:
        cmd_args.extend(
            itertools.chain.from_iterable(["-p", vprop] for vprop in properties)
        )

    if properties is not None:
        with pytest.raises(RuntimeError, match="No module named 'test_plugin_package'"):
            # This should fail because the plugin is not installed
            main(cmd_args)

    main([*cmd_args, "--skip-plugin-validation"])

    output_f = tmp_dir_path / target_variant_wheel.name
    assert output_f.exists(), (
        f"Expected output file {output_f} to exist, but it does not."
    )

    assert_zips_equal(target_variant_wheel, output_f)


@pytest.mark.parametrize(
    ("vhash", "properties"),
    [
        # Null Variant
        ("00000000", None),
        # Variant 1
        (
            "5d8be4b9",
            [
                "installable_plugin::feat1::val1c",
                "installable_plugin::feat2::val2b",
            ],
        ),
        # Variant 2
        ("60567bd9", ["installable_plugin::feat1::val1c"]),
        ("60567bd9", ["installable_plugin :: feat1::val1c"]),
        ("60567bd9", ["installable_plugin::feat1 :: val1c"]),
        ("60567bd9", ["installable_plugin :: feat1 :: val1c"]),
        # Variant 3
        ("fbe82642", ["installable_plugin::feat2::val2b"]),
        ("fbe82642", ["installable_plugin :: feat2::val2b"]),
        ("fbe82642", ["installable_plugin::feat2 :: val2b"]),
        ("fbe82642", ["installable_plugin :: feat2 :: val2b"]),
    ],
)
def test_make_variant(
    vhash: str,
    properties: list[str] | None,
    non_variant_wheel: Path,
    pyproject_toml: Path,
    tmp_path: Path,
) -> None:
    validate_make_variant(
        tmp_dir_path=tmp_path,
        non_variant_wheel=non_variant_wheel,
        pyproject_toml=pyproject_toml,
        target_variant_wheel=(
            non_variant_wheel.parent / f"test_package-0-py3-none-any-{vhash}.whl"
        ),
        properties=properties,
    )


def test_make_variant_error(
    non_variant_wheel: Path,
    pyproject_toml: Path,
    tmp_path: Path,
) -> None:
    with pytest.raises(SystemExit):
        # "error: one of the arguments -p/--property --null-variant is required"
        main(
            [
                "make-variant",
                "-f",
                str(non_variant_wheel.resolve()),
                "-o",
                str(tmp_path),
                "--pyproject-toml",
                str(pyproject_toml.resolve()),
            ]
        )

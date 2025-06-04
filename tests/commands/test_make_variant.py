from __future__ import annotations

import itertools
import tempfile
from pathlib import Path

import pytest

from tests.utils import assert_zips_equal
from variantlib.commands.main import main


@pytest.fixture
def non_variant_wheel() -> Path:
    return Path("tests/artifacts/test-package/dist/test_package-0-py3-none-any.whl")


@pytest.fixture
def pyproject_toml() -> Path:
    return Path("tests/artifacts/test-package/pyproject.toml")


def validate_make_variant(
    non_variant_wheel: Path,
    pyproject_toml: Path,
    target_variant_wheel: Path,
    properties: list[str] | None = None,
) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)

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
            with pytest.raises(
                RuntimeError, match="No module named 'test_plugin_package'"
            ):
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
        (
            "5d8be4b9",
            [
                "installable_plugin::feat1::val1c",
                "installable_plugin::feat2::val2b",
            ],
        ),
        ("60567bd9", ["installable_plugin::feat1::val1c"]),
        ("fbe82642", ["installable_plugin::feat2::val2b"]),
        ("00000000", None),
    ],
)
def test_make_variant(
    vhash: str,
    properties: list[str] | None,
    non_variant_wheel: Path,
    pyproject_toml: Path,
) -> None:
    validate_make_variant(
        non_variant_wheel=non_variant_wheel,
        pyproject_toml=pyproject_toml,
        target_variant_wheel=(
            non_variant_wheel.parent / f"test_package-0-py3-none-any-{vhash}.whl"
        ),
        properties=properties,
    )

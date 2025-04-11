import pytest

from variantlib.envspec import evaluate_variant_requirements
from variantlib.errors import InvalidVariantEnvSpecError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty


@pytest.mark.parametrize(
    ("properties", "expected"),
    [
        ([VariantProperty("x86_64", "level", "v3")], ["variant-x86-64"]),
        ([VariantProperty("x86_64", "sse3", "on")], ["variant-x86-64"]),
        ([VariantProperty("cuda", "runtime", "12.6")], ["variant-cuda"]),
        ([VariantProperty("cuda", "other", "x")], []),
        ([VariantProperty("x", "y", "z")], []),
        (
            [
                VariantProperty("x86_64", "level", "v3"),
                VariantProperty("cuda", "runtime", "12.6"),
            ],
            ["variant-cuda", "variant-x86-64"],
        ),
    ],
)
def test_evaluate_variant_requirements(
    properties: list[VariantProperty], expected: list[str]
) -> None:
    requirements = [
        "setuptools",
        "typing-extensions; python_version < '3.11'",
        "variant-cuda; 'cuda :: runtime' in variants",
        "variant-x86-64; 'x86_64' in variants",
    ]
    variant_desc = VariantDescription(properties)

    assert evaluate_variant_requirements(requirements, variant_desc) == [
        "setuptools",
        "typing-extensions; python_version < '3.11'",
        *expected,
    ]


@pytest.mark.parametrize(
    "env_spec",
    [
        "variants == 'x'",
        "variants in 'x'",
        "'x' == variants",
    ],
)
def test_invalid_variant_requirements(env_spec: str) -> None:
    with pytest.raises(InvalidVariantEnvSpecError):
        evaluate_variant_requirements(
            [f"variant-test; {env_spec}"],
            VariantDescription([VariantProperty("x", "y", "z")]),
        )

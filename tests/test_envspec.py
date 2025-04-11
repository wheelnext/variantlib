import pytest

from variantlib.envspec import FALSE_STR
from variantlib.envspec import TRUE_STR
from variantlib.envspec import evaluate_variant_requirements
from variantlib.errors import InvalidVariantEnvSpecError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty


@pytest.mark.parametrize(
    ("properties", "expected"),
    [
        ([VariantProperty("x86_64", "level", "v3")], [False, True, False]),
        ([VariantProperty("x86_64", "sse3", "on")], [False, True, False]),
        ([VariantProperty("cuda", "runtime", "12.6")], [True, False, True]),
        ([VariantProperty("cuda", "other", "x")], [False, False, True]),
        ([VariantProperty("x", "y", "z")], [False, False, False]),
        (
            [
                VariantProperty("x86_64", "level", "v3"),
                VariantProperty("cuda", "runtime", "12.6"),
            ],
            [True, True, True],
        ),
    ],
)
def test_evaluate_variant_requirements(
    properties: list[VariantProperty], expected: list[bool]
) -> None:
    requirements = [
        "setuptools",
        "typing-extensions; python_version < '3.11'",
        "variant-cuda; 'cuda :: runtime' in variants",
        "variant-x86-64; 'x86_64' in variants",
        "variant-cuda-extra; 'cuda' in variants and python_version >= '3.11'",
        "no-cuda; 'cuda' not in variants",
    ]
    variant_desc = VariantDescription(properties)

    assert evaluate_variant_requirements(requirements, variant_desc) == [
        "setuptools",
        "typing-extensions; python_version < '3.11'",
        f"variant-cuda; {TRUE_STR if expected[0] else FALSE_STR}",
        f"variant-x86-64; {TRUE_STR if expected[1] else FALSE_STR}",
        f"variant-cuda-extra; {TRUE_STR if expected[2] else FALSE_STR} "
        'and python_version >= "3.11"',
        f"no-cuda; {TRUE_STR if not expected[2] else FALSE_STR}",
    ]


@pytest.mark.parametrize(
    "env_spec",
    [
        "variants == 'x'",
        "variants in 'x'",
        "variants not in 'x'",
        "'x' == variants",
        "variants!='x'",
        "variants in'x'",
        "variants not in'x'",
        "'x'!=variants",
    ],
)
def test_invalid_variant_requirements(env_spec: str) -> None:
    with pytest.raises(InvalidVariantEnvSpecError):
        evaluate_variant_requirements(
            [f"variant-test; {env_spec}"],
            VariantDescription([VariantProperty("x", "y", "z")]),
        )

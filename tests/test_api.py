from __future__ import annotations

import string
from email.message import EmailMessage
from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck
from hypothesis import assume
from hypothesis import example
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from tests.utils import get_combinations
from variantlib.api import ProviderConfig
from variantlib.api import VariantDescription
from variantlib.api import VariantFeatureConfig
from variantlib.api import VariantProperty
from variantlib.api import VariantValidationResult
from variantlib.api import get_variant_hashes_by_priority
from variantlib.api import set_variant_metadata
from variantlib.api import validate_variant
from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.loader import PluginLoader
from variantlib.models import provider as pconfig
from variantlib.models import variant as vconfig
from variantlib.models.configuration import VariantConfiguration as VConfigurationModel

if TYPE_CHECKING:
    from collections.abc import Generator


def test_api_accessible():
    """Test that the API is accessible."""
    assert get_variant_hashes_by_priority is not None
    assert pconfig.VariantFeatureConfig is VariantFeatureConfig
    assert pconfig.ProviderConfig is ProviderConfig
    assert vconfig.VariantDescription is VariantDescription
    assert vconfig.VariantProperty is VariantProperty


@pytest.fixture
def configs(mocked_plugin_loader: type[PluginLoader]):
    return list(PluginLoader.get_supported_configs().values())


def test_get_variant_hashes_by_priority_roundtrip(mocker, configs):
    """Test that we can round-trip all combinations via variants.json and get the same
    result."""

    namespace_priorities = ["test_namespace", "second_namespace"]

    # The null-variant is always the last one and implicitly added
    combinations: list[VariantDescription] = [
        *list(get_combinations(configs, namespace_priorities)),
    ]
    variants_json = {
        VARIANTS_JSON_VARIANT_DATA_KEY: {
            vdesc.hexdigest: vdesc.to_dict() for vdesc in combinations
        }
    }

    mocker.patch(
        "variantlib.configuration.VariantConfiguration.get_config"
    ).return_value = VConfigurationModel(namespace_priorities=namespace_priorities)

    assert get_variant_hashes_by_priority(variants_json=variants_json) == [
        vdesc.hexdigest for vdesc in combinations
    ]


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@example(
    [
        ProviderConfig(
            namespace="A",
            configs=[
                VariantFeatureConfig(name="A1", values=["x"]),
                VariantFeatureConfig(name="A2", values=["x"]),
            ],
        ),
        ProviderConfig(
            namespace="B", configs=[VariantFeatureConfig(name="B1", values=["x"])]
        ),
        ProviderConfig(
            namespace="C", configs=[VariantFeatureConfig(name="C1", values=["x"])]
        ),
    ]
)
@given(
    st.lists(
        min_size=1,
        max_size=3,
        unique_by=lambda provider_cfg: provider_cfg.namespace,
        elements=st.builds(
            ProviderConfig,
            namespace=st.from_regex(VALIDATION_NAMESPACE_REGEX, fullmatch=True),
            configs=st.lists(
                min_size=1,
                max_size=2,
                unique_by=lambda vfeat_cfg: vfeat_cfg.name,
                elements=st.builds(
                    VariantFeatureConfig,
                    name=st.from_regex(VALIDATION_FEATURE_REGEX, fullmatch=True),
                    values=st.lists(
                        min_size=1,
                        max_size=3,
                        unique=True,
                        elements=st.from_regex(VALIDATION_VALUE_REGEX, fullmatch=True),
                    ),
                ),
            ),
        ),
    )
)
def test_get_variant_hashes_by_priority_roundtrip_fuzz(mocker, configs):
    namespace_priorities = list({provider_cfg.namespace for provider_cfg in configs})
    mocker.patch(
        "variantlib.configuration.VariantConfiguration.get_config"
    ).return_value = VConfigurationModel(namespace_priorities=namespace_priorities)

    def get_or_skip_combinations() -> Generator[VariantDescription]:
        for i, x in enumerate(get_combinations(configs, namespace_priorities)):
            assume(i < 65536)
            yield x

    # The null-variant is always the last one and implicitly added
    combinations: list[VariantDescription] = [*list(get_or_skip_combinations())]

    variants_json = {
        VARIANTS_JSON_VARIANT_DATA_KEY: {
            vdesc.hexdigest: vdesc.to_dict() for vdesc in combinations
        }
    }

    mocker.patch(
        "variantlib.loader.PluginLoader.get_supported_configs"
    ).return_value = {provider_cfg.namespace: provider_cfg for provider_cfg in configs}

    assert get_variant_hashes_by_priority(variants_json=variants_json) == [
        vdesc.hexdigest for vdesc in combinations
    ]


@pytest.mark.parametrize(
    ("bools", "valid", "valid_strict"),
    [
        ((True,), True, True),
        ((None,), True, False),
        ((False,), False, False),
        ((True, True, True), True, True),
        ((True, True, None), True, False),
        ((None, None, None), True, False),
        ((True, True, False), False, False),
        ((True, None, False), False, False),
        ((None, None, False), False, False),
        # corner case: the base variant is also valid
        ((), True, True),
    ],
)
def test_validation_result_is_valid(
    bools: tuple[bool, ...], valid: bool, valid_strict: bool
):
    res = VariantValidationResult(
        {
            VariantProperty(
                string.ascii_lowercase[i],
                string.ascii_lowercase[i],
                string.ascii_lowercase[i],
            ): var_res
            for i, var_res in enumerate(bools)
        }
    )
    assert res.is_valid() == valid
    assert res.is_valid(allow_unknown_plugins=False) == valid_strict


def test_validation_result_properties():
    res = VariantValidationResult(
        {
            VariantProperty("blas", "variant", "mkl"): True,
            VariantProperty("cuda", "runtime", "12.0"): None,
            VariantProperty("blas", "invariant", "lkm"): False,
            VariantProperty("x86_64", "baseline", "v10"): False,
            VariantProperty("orange", "juice", "good"): None,
        }
    )

    assert res.invalid_properties == [
        VariantProperty("blas", "invariant", "lkm"),
        VariantProperty("x86_64", "baseline", "v10"),
    ]
    assert res.unknown_properties == [
        VariantProperty("cuda", "runtime", "12.0"),
        VariantProperty("orange", "juice", "good"),
    ]


def test_validate_variant(mocked_plugin_loader: type[PluginLoader]):
    res = validate_variant(
        VariantDescription(
            [
                VariantProperty("test_namespace", "name1", "val1d"),
                VariantProperty("test_namespace", "name2", "val2d"),
                VariantProperty("test_namespace", "name3", "val3a"),
                VariantProperty("second_namespace", "name3", "val3a"),
                VariantProperty("incompatible_namespace", "flag1", "on"),
                VariantProperty("incompatible_namespace", "flag2", "off"),
                VariantProperty("incompatible_namespace", "flag5", "on"),
                VariantProperty("missing_namespace", "name", "val"),
                VariantProperty("private", "build_type", "debug"),
            ]
        )
    )

    assert res == VariantValidationResult(
        {
            VariantProperty("test_namespace", "name1", "val1d"): True,
            VariantProperty("test_namespace", "name2", "val2d"): False,
            VariantProperty("test_namespace", "name3", "val3a"): False,
            VariantProperty("second_namespace", "name3", "val3a"): True,
            VariantProperty("incompatible_namespace", "flag1", "on"): True,
            VariantProperty("incompatible_namespace", "flag2", "off"): False,
            VariantProperty("incompatible_namespace", "flag5", "on"): False,
            VariantProperty("missing_namespace", "name", "val"): None,
            VariantProperty("private", "build_type", "debug"): None,
        }
    )
    assert not res.is_valid()


@pytest.fixture
def metadata() -> EmailMessage:
    metadata = EmailMessage()
    metadata.set_content("long description\nof a package")
    # remove implicitly added Content-* headers to match Python metadata
    for key in metadata:
        del metadata[key]
    metadata["Metadata-Version"] = "2.1"
    metadata["Name"] = "test-package"
    metadata["Version"] = "1.2.3"
    return metadata


@pytest.mark.parametrize("replace", [False, True])
def test_set_variant_metadata(
    mocked_plugin_loader: type[PluginLoader],
    metadata: EmailMessage,
    replace: bool,
):
    if replace:
        # deliberately using different case
        metadata["Variant-Hash"] = "12345678"
        metadata["variant"] = "a :: b :: c"
        metadata["variant"] = "d :: e :: f"
        metadata["variant-Provider"] = "a, frobnicate"

    set_variant_metadata(
        metadata,
        VariantDescription(
            [
                VariantProperty("test_namespace", "name1", "val1d"),
                VariantProperty("test_namespace", "name2", "val2a"),
                VariantProperty("second_namespace", "name3", "val3a"),
            ]
        ),
    )
    assert metadata.as_string() == (
        "Metadata-Version: 2.1\n"
        "Name: test-package\n"
        "Version: 1.2.3\n"
        "Variant: second_namespace :: name3 :: val3a\n"
        "Variant: test_namespace :: name1 :: val1d\n"
        "Variant: test_namespace :: name2 :: val2a\n"
        "Variant-hash: c9267e19\n"
        "Variant-provider: second_namespace: second-plugin\n"
        "Variant-provider: test_namespace: test-plugin\n"
        "\n"
        "long description\n"
        "of a package\n"
    )

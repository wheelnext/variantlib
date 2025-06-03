from __future__ import annotations

import json
import string
from collections.abc import Generator
from typing import TYPE_CHECKING
from typing import Any

import pytest
from hypothesis import HealthCheck
from hypothesis import assume
from hypothesis import example
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from tests.test_pyproject_toml import PYPROJECT_TOML
from tests.test_pyproject_toml import PYPROJECT_TOML_MINIMAL
from tests.utils import get_combinations
from variantlib.api import ProviderConfig
from variantlib.api import VariantDescription
from variantlib.api import VariantFeatureConfig
from variantlib.api import VariantProperty
from variantlib.api import VariantValidationResult
from variantlib.api import check_variant_supported
from variantlib.api import get_variant_hashes_by_priority
from variantlib.api import make_variant_dist_info
from variantlib.api import validate_variant
from variantlib.constants import VALIDATION_FEATURE_NAME_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.constants import VARIANTS_JSON_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANTS_JSON_NAMESPACE_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_DATA_KEY
from variantlib.constants import VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.models import provider as pconfig
from variantlib.models import variant as vconfig
from variantlib.models.configuration import VariantConfiguration as VConfigurationModel
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.pyproject_toml import VariantPyProjectToml
from variantlib.variants_json import VariantsJson

if TYPE_CHECKING:
    from collections.abc import Generator

    from variantlib.plugins.loader import BasePluginLoader


def test_api_accessible():
    """Test that the API is accessible."""
    assert get_variant_hashes_by_priority is not None
    assert pconfig.VariantFeatureConfig is VariantFeatureConfig
    assert pconfig.ProviderConfig is ProviderConfig
    assert vconfig.VariantDescription is VariantDescription
    assert vconfig.VariantProperty is VariantProperty


@pytest.fixture
def configs(
    mocked_plugin_loader: BasePluginLoader,
):
    return list(mocked_plugin_loader.get_supported_configs().values())


@pytest.mark.parametrize("construct", [False, True])
def test_get_variant_hashes_by_priority_roundtrip(
    configs,
    construct: bool,
):
    """Test that we can round-trip all combinations via variants.json and get the same
    result."""

    namespace_priorities = ["test_namespace", "second_namespace"]
    plugin_apis = {
        "test_namespace": "tests.mocked_plugins:MockedPluginA",
        "second_namespace": "tests.mocked_plugins:MockedPluginB",
    }

    # The null-variant is always the last one and implicitly added
    combinations: list[VariantDescription] = [
        *list(get_combinations(configs, namespace_priorities)),
    ]
    variants_json: dict | VariantsJson = {
        VARIANTS_JSON_DEFAULT_PRIO_KEY: {
            VARIANTS_JSON_NAMESPACE_KEY: namespace_priorities,
        },
        VARIANTS_JSON_PROVIDER_DATA_KEY: {
            namespace: {VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY: plugin_api}
            for namespace, plugin_api in plugin_apis.items()
        },
        VARIANTS_JSON_VARIANT_DATA_KEY: {
            vdesc.hexdigest: vdesc.to_dict() for vdesc in combinations
        },
    }
    variants_json = VariantsJson(variants_json)

    assert get_variant_hashes_by_priority(
        variants_json=variants_json, use_auto_install=False, venv_path=None
    ) == [vdesc.hexdigest for vdesc in combinations]


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@example(
    [
        ProviderConfig(
            namespace="a",
            configs=[
                VariantFeatureConfig(name="a1", values=["x"]),
                VariantFeatureConfig(name="a2", values=["x"]),
            ],
        ),
        ProviderConfig(
            namespace="b", configs=[VariantFeatureConfig(name="b1", values=["x"])]
        ),
        ProviderConfig(
            namespace="c", configs=[VariantFeatureConfig(name="c1", values=["x"])]
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
                    name=st.from_regex(VALIDATION_FEATURE_NAME_REGEX, fullmatch=True),
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
def test_get_variant_hashes_by_priority_roundtrip_fuzz(
    mocker, configs: list[ProviderConfig]
):
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
        "variantlib.plugins.loader.BasePluginLoader._load_all_plugins_from_tuple"
    ).return_value = None
    mocker.patch(
        "variantlib.plugins.loader.BasePluginLoader.get_supported_configs"
    ).return_value = {provider_cfg.namespace: provider_cfg for provider_cfg in configs}

    assert get_variant_hashes_by_priority(
        variants_json=variants_json, use_auto_install=False, venv_path=None
    ) == [vdesc.hexdigest for vdesc in combinations]


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


def test_validate_variant(mocked_plugin_apis: list[str]):
    vmeta = VariantMetadata(
        namespace_priorities=[
            "test_namespace",
            "second_namespace",
            "incompatible_namespace",
        ],
        providers={
            "test_namespace": ProviderInfo(
                plugin_api="tests.mocked_plugins:MockedPluginA"
            ),
            "second_namespace": ProviderInfo(
                plugin_api="tests.mocked_plugins:MockedPluginB"
            ),
            "incompatible_namespace": ProviderInfo(
                plugin_api="tests.mocked_plugins:MockedPluginC"
            ),
        },
    )

    # Verify whether the variant properties are valid
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
        ),
        metadata=vmeta,
        use_auto_install=False,
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


@pytest.mark.parametrize(
    "pyproject_toml", [None, PYPROJECT_TOML, PYPROJECT_TOML_MINIMAL]
)
def test_make_variant_dist_info(
    pyproject_toml: dict | None,
):
    expected: dict[str, Any] = {
        "$schema": "https://variants-schema.wheelnext.dev/",
        "default-priorities": {
            "namespace": [],
            "feature": [],
            "property": [],
        },
        "providers": {},
        "variants": {
            "67fcaf38": {
                "ns1": {
                    "f1": "p1",
                    "f2": "p2",
                },
                "ns2": {"f1": "p1"},
            },
        },
    }

    if pyproject_toml is not None:
        expected["providers"].update(
            {
                "ns1": {
                    "requires": ["ns1-provider >= 1.2.3"],
                    "enable-if": "python_version >= '3.12'",
                    "plugin-api": "ns1_provider.plugin:NS1Plugin",
                },
                "ns2": {
                    "requires": [
                        "ns2_provider; python_version >= '3.11'",
                        "old_ns2_provider; python_version < '3.11'",
                    ],
                    "plugin-api": "ns2_provider:Plugin",
                },
            }
        )
        expected["default-priorities"].update(
            {
                "namespace": ["ns1", "ns2"],
            },
        )
    if pyproject_toml is PYPROJECT_TOML:
        expected["default-priorities"].update(
            {
                "feature": ["ns2 :: f1", "ns1 :: f2"],
                "property": ["ns1 :: f2 :: p1", "ns2 :: f1 :: p2"],
            }
        )

    assert (
        json.loads(
            make_variant_dist_info(
                VariantDescription(
                    [
                        VariantProperty("ns1", "f1", "p1"),
                        VariantProperty("ns1", "f2", "p2"),
                        VariantProperty("ns2", "f1", "p1"),
                    ]
                ),
                variant_metadata=VariantPyProjectToml(pyproject_toml)
                if pyproject_toml is not None
                else None,
            )
        )
        == expected
    )


@pytest.fixture
def common_metadata() -> VariantMetadata:
    return VariantMetadata(
        namespace_priorities=["test_namespace", "second_namespace"],
        providers={
            "test_namespace": ProviderInfo(
                plugin_api="tests.mocked_plugins:MockedPluginA"
            ),
            "second_namespace": ProviderInfo(
                plugin_api="tests.mocked_plugins:MockedPluginB"
            ),
        },
    )


@pytest.mark.parametrize(
    ("vdesc", "expected"),
    [
        (VariantDescription(), True),
        (
            VariantDescription(
                [
                    VariantProperty("test_namespace", "name2", "val2c"),
                    VariantProperty("second_namespace", "name3", "val3a"),
                ]
            ),
            True,
        ),
        (
            VariantDescription(
                [
                    VariantProperty("test_namespace", "name1", "val1c"),
                ]
            ),
            False,
        ),
    ],
)
def test_check_variant_supported_dist(
    common_metadata: VariantMetadata, vdesc: VariantDescription, expected: bool
) -> None:
    variant_json = VariantsJson(common_metadata)
    variant_json.variants[vdesc.hexdigest] = vdesc
    assert (
        check_variant_supported(
            metadata=variant_json, use_auto_install=False, venv_path=None
        )
        is expected
    )


def test_check_variant_supported_generic():
    # metadata should only be used to load plugins
    vmeta = VariantMetadata(
        namespace_priorities=["test_namespace", "second_namespace"],
        providers={
            "test_namespace": ProviderInfo(
                plugin_api="tests.mocked_plugins:MockedPluginA"
            ),
            "second_namespace": ProviderInfo(
                plugin_api="tests.mocked_plugins:MockedPluginB"
            ),
        },
    )

    # test the null variant
    assert check_variant_supported(
        vdesc=VariantDescription(),
        metadata=vmeta,
        use_auto_install=False,
        venv_path=None,
    )

    # test a supported variant
    assert check_variant_supported(
        vdesc=VariantDescription(
            [
                VariantProperty("test_namespace", "name2", "val2c"),
                VariantProperty("second_namespace", "name3", "val3a"),
            ]
        ),
        metadata=vmeta,
        use_auto_install=False,
        venv_path=None,
    )

    # test an usupported variant
    assert not check_variant_supported(
        vdesc=VariantDescription([VariantProperty("test_namespace", "name1", "val1c")]),
        metadata=vmeta,
        use_auto_install=False,
        venv_path=None,
    )

from __future__ import annotations

import json
import re
import string
from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck
from hypothesis import assume
from hypothesis import example
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st
from trycast import trycast

from tests.test_pyproject_toml import PYPROJECT_TOML
from tests.test_pyproject_toml import PYPROJECT_TOML_MINIMAL
from tests.utils import get_combinations
from variantlib.api import ProviderConfig
from variantlib.api import VariantDescription
from variantlib.api import VariantFeatureConfig
from variantlib.api import VariantProperty
from variantlib.api import VariantValidationResult
from variantlib.api import check_variant_supported
from variantlib.api import get_variant_environment_dict
from variantlib.api import get_variant_label
from variantlib.api import get_variants_by_priority
from variantlib.api import make_variant_dist_info
from variantlib.api import validate_variant
from variantlib.constants import NULL_VARIANT_LABEL
from variantlib.constants import PYPROJECT_TOML_TOP_KEY
from variantlib.constants import VALIDATION_FEATURE_NAME_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.constants import VARIANT_INFO_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_INFO_FEATURE_KEY
from variantlib.constants import VARIANT_INFO_NAMESPACE_KEY
from variantlib.constants import VARIANT_INFO_PROPERTY_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_ENABLE_IF_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_OPTIONAL_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_PLUGIN_API_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANT_LABEL_LENGTH
from variantlib.constants import VARIANTS_JSON_SCHEMA_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_URL
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.constants import VariantsJsonDict
from variantlib.errors import ValidationError
from variantlib.models import provider as pconfig
from variantlib.models import variant as vconfig
from variantlib.models.configuration import VariantConfiguration as VConfigurationModel
from variantlib.models.variant_info import PluginUse
from variantlib.models.variant_info import ProviderInfo
from variantlib.models.variant_info import VariantInfo
from variantlib.pyproject_toml import VariantPyProjectToml
from variantlib.variants_json import VariantsJson

if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest_mock import MockerFixture

    from variantlib.plugins.loader import BasePluginLoader


def test_api_accessible() -> None:
    """Test that the API is accessible."""
    assert get_variants_by_priority is not None
    assert pconfig.VariantFeatureConfig is VariantFeatureConfig
    assert pconfig.ProviderConfig is ProviderConfig
    assert vconfig.VariantDescription is VariantDescription
    assert vconfig.VariantProperty is VariantProperty


@pytest.fixture
def configs(
    mocked_plugin_loader: BasePluginLoader,
) -> list[ProviderConfig]:
    return list(mocked_plugin_loader.get_supported_configs().values())


@pytest.mark.parametrize("construct", [False, True])
@pytest.mark.parametrize("test_dynamic", [False, True])
@pytest.mark.parametrize("custom_labels", [False, True])
@pytest.mark.parametrize("explicit_null", [False, True])
def test_get_variants_by_priority_roundtrip(
    configs: list[ProviderConfig],
    construct: bool,
    test_dynamic: bool,
    custom_labels: bool,
    explicit_null: bool,
) -> None:
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
    if test_dynamic:
        combinations.insert(
            -1,
            VariantDescription(
                properties=[
                    VariantProperty(
                        namespace="second_namespace",
                        feature="name3",
                        value="val3dynamic",
                    )
                ]
            ),
        )

    variants_json = {
        VARIANTS_JSON_SCHEMA_KEY: VARIANTS_JSON_SCHEMA_URL,
        VARIANT_INFO_DEFAULT_PRIO_KEY: {
            VARIANT_INFO_NAMESPACE_KEY: namespace_priorities,
        },
        VARIANT_INFO_PROVIDER_DATA_KEY: {
            namespace: {
                VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: plugin_api,
                VARIANT_INFO_PROVIDER_REQUIRES_KEY: [],
            }
            for namespace, plugin_api in plugin_apis.items()
        },
        VARIANTS_JSON_VARIANT_DATA_KEY: {
            f"foo{vdesc.hexdigest[:4]}"
            if custom_labels and not vdesc.is_null_variant()
            else get_variant_label(vdesc): vdesc.to_dict()
            for vdesc in combinations
            if explicit_null or not vdesc.is_null_variant()
        },
    }

    if (typed_variants_json := trycast(VariantsJsonDict, variants_json)) is None:
        raise ValueError(
            f"Did not conform the `VariantsJsonDict` format: {variants_json}"
        )

    # variants_json = VariantsJson(typed_variants_json)

    assert get_variants_by_priority(variants_json=typed_variants_json) == [
        f"foo{vdesc.hexdigest[:4]}"
        if custom_labels and not vdesc.is_null_variant()
        else get_variant_label(vdesc)
        for vdesc in combinations
    ]


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
            namespace="b",
            configs=[
                VariantFeatureConfig(name="b1", values=["x"]),
            ],
        ),
        ProviderConfig(
            namespace="c",
            configs=[
                VariantFeatureConfig(name="c1", values=["x"]),
            ],
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
def test_get_variants_by_priority_roundtrip_fuzz(
    mocker: MockerFixture, configs: list[ProviderConfig]
) -> None:
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
            get_variant_label(vdesc): vdesc.to_dict() for vdesc in combinations
        }
    }

    if (typed_variants_json := trycast(VariantsJsonDict, variants_json)) is None:
        raise ValueError(
            f"Did not conform the `VariantsJsonDict` format: {variants_json}"
        )

    mocker.patch(
        "variantlib.plugins.loader.BasePluginLoader.get_supported_configs"
    ).return_value = {provider_cfg.namespace: provider_cfg for provider_cfg in configs}

    assert get_variants_by_priority(variants_json=typed_variants_json) == [
        get_variant_label(vdesc) for vdesc in combinations
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
) -> None:
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


def test_validation_result_properties() -> None:
    res = VariantValidationResult(
        {
            VariantProperty("blas", PYPROJECT_TOML_TOP_KEY, "mkl"): True,
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


@pytest.mark.parametrize("optional", [False, True])
def test_validate_variant(optional: bool) -> None:
    variant_info = VariantInfo(
        namespace_priorities=[
            "test_namespace",
            "second_namespace",
            "incompatible_namespace",
        ],
        providers={
            "test_namespace": ProviderInfo(
                plugin_api="tests.mocked_plugins:MockedPluginA", optional=optional
            ),
            "second_namespace": ProviderInfo(
                plugin_api="tests.mocked_plugins:MockedPluginB", optional=optional
            ),
            "incompatible_namespace": ProviderInfo(
                plugin_api="tests.mocked_plugins:MockedPluginC", optional=optional
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
        variant_info=variant_info,
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
@pytest.mark.parametrize("label", [None, "foo", "xy1.2"])
def test_make_variant_dist_info(
    pyproject_toml: VariantsJsonDict | None,
    label: str | None,
) -> None:
    expected: VariantsJsonDict = {
        VARIANTS_JSON_SCHEMA_KEY: VARIANTS_JSON_SCHEMA_URL,
        VARIANT_INFO_DEFAULT_PRIO_KEY: {
            VARIANT_INFO_NAMESPACE_KEY: [],
        },
        VARIANT_INFO_PROVIDER_DATA_KEY: {},
        VARIANTS_JSON_VARIANT_DATA_KEY: {
            label if label else "67fcaf38": {
                "ns1": {
                    "f1": ["p1"],
                    "f2": ["p2"],
                },
                "ns2": {"f1": ["p1"]},
            },
        },
    }

    if pyproject_toml is not None:
        expected[VARIANT_INFO_PROVIDER_DATA_KEY].update(
            {
                "ns1": {
                    VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["ns1-provider >= 1.2.3"],
                    VARIANT_INFO_PROVIDER_ENABLE_IF_KEY: "python_version >= '3.12'",
                    VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "ns1_provider.plugin:NS1Plugin",  # noqa: E501
                },
                "ns2": {
                    VARIANT_INFO_PROVIDER_REQUIRES_KEY: [
                        "ns2_provider; python_version >= '3.11'",
                        "old_ns2_provider; python_version < '3.11'",
                    ],
                    VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: "ns2_provider:Plugin",
                    VARIANT_INFO_PROVIDER_OPTIONAL_KEY: True,
                    VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY: "build",
                },
            }
        )
        expected[VARIANT_INFO_DEFAULT_PRIO_KEY].update(
            {
                VARIANT_INFO_NAMESPACE_KEY: ["ns1", "ns2"],
            },
        )

    if pyproject_toml is PYPROJECT_TOML:
        expected[VARIANT_INFO_DEFAULT_PRIO_KEY].update(
            {
                VARIANT_INFO_FEATURE_KEY: {
                    "ns1": ["f2"],
                    "ns2": ["f1", "f2"],
                },
                VARIANT_INFO_PROPERTY_KEY: {
                    "ns1": {
                        "f2": ["p1"],
                    },
                    "ns2": {
                        "f1": ["p2"],
                    },
                },
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
                variant_info=VariantPyProjectToml(pyproject_toml)  # type: ignore[arg-type]
                if pyproject_toml is not None
                else None,
                variant_label=label,
                expand_build_plugin_properties=False,
            )
        )
        == expected
    )


@pytest.fixture
def common_variant_info() -> VariantInfo:
    return VariantInfo(
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
    common_variant_info: VariantInfo, vdesc: VariantDescription, expected: bool
) -> None:
    variant_json = VariantsJson(common_variant_info)
    variant_json.variants[vdesc.hexdigest] = vdesc
    assert check_variant_supported(variant_info=variant_json) is expected


def test_check_variant_supported_generic() -> None:
    # variant_info should only be used to load plugins
    variant_info = VariantInfo(
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
        variant_info=variant_info,
    )

    # test a supported variant
    assert check_variant_supported(
        vdesc=VariantDescription(
            [
                VariantProperty("test_namespace", "name2", "val2c"),
                VariantProperty("second_namespace", "name3", "val3a"),
            ]
        ),
        variant_info=variant_info,
    )

    # test an usupported variant
    assert not check_variant_supported(
        vdesc=VariantDescription([VariantProperty("test_namespace", "name1", "val1c")]),
        variant_info=variant_info,
    )


def test_get_variant_environment_dict() -> None:
    vdesc = VariantDescription(
        [
            VariantProperty("ns1", "feat1", "val1"),
            VariantProperty("ns1", "feat2", "val2"),
            VariantProperty("ns2", "feat1", "val1"),
            VariantProperty("ns3", "feat2", "val2"),
        ]
    )
    assert get_variant_environment_dict(vdesc) == {
        "variant_features": {
            "ns1 :: feat1",
            "ns1 :: feat2",
            "ns2 :: feat1",
            "ns3 :: feat2",
        },
        "variant_namespaces": {
            "ns1",
            "ns2",
            "ns3",
        },
        "variant_properties": {
            "ns1 :: feat1 :: val1",
            "ns1 :: feat2 :: val2",
            "ns2 :: feat1 :: val1",
            "ns3 :: feat2 :: val2",
        },
    }


def test_make_variant_dist_info_invalid_label():
    with pytest.raises(
        ValidationError,
        match=rf"Null variant must always use {NULL_VARIANT_LABEL!r} label",
    ):
        make_variant_dist_info(VariantDescription([]), variant_label="foo")
    with pytest.raises(
        ValidationError,
        match=rf"{NULL_VARIANT_LABEL!r} label can be used only for the null variant",
    ):
        make_variant_dist_info(
            VariantDescription([VariantProperty("a", "b", "c")]),
            variant_label=NULL_VARIANT_LABEL,
        )
    with pytest.raises(
        ValidationError,
        match=re.escape(
            f"Invalid variant label: 'foo/bar' (must be up to {VARIANT_LABEL_LENGTH} "
            "alphanumeric characters)"
        ),
    ):
        make_variant_dist_info(
            VariantDescription([VariantProperty("a", "b", "c")]),
            variant_label="foo/bar",
        )
    with pytest.raises(
        ValidationError,
        match=re.escape(
            "Invalid variant label: '12345678901234567' (must be up to "
            f"{VARIANT_LABEL_LENGTH} alphanumeric characters)"
        ),
    ):
        make_variant_dist_info(
            VariantDescription([VariantProperty("a", "b", "c")]),
            variant_label="12345678901234567",
        )


def test_get_variant_label() -> None:
    assert get_variant_label(VariantDescription()) == NULL_VARIANT_LABEL
    assert (
        get_variant_label(VariantDescription(), NULL_VARIANT_LABEL)
        == NULL_VARIANT_LABEL
    )

    assert (
        get_variant_label(VariantDescription([VariantProperty("a", "b", "c")]))
        == "01a9783a"
    )
    assert (
        get_variant_label(
            VariantDescription(
                [VariantProperty("a", "b", "c"), VariantProperty("d", "e", "f")]
            )
        )
        == "eb9a66a7"
    )
    assert (
        get_variant_label(
            VariantDescription(
                [VariantProperty("d", "e", "f"), VariantProperty("a", "b", "c")]
            )
        )
        == "eb9a66a7"
    )

    assert (
        get_variant_label(VariantDescription([VariantProperty("a", "b", "c")]), "foo")
        == "foo"
    )
    assert (
        get_variant_label(
            VariantDescription(
                [VariantProperty("a", "b", "c"), VariantProperty("d", "e", "f")]
            ),
            "foo",
        )
        == "foo"
    )

    with pytest.raises(
        ValidationError,
        match=rf"Null variant must always use {NULL_VARIANT_LABEL!r} label",
    ):
        get_variant_label(VariantDescription([]), "foo")
    with pytest.raises(
        ValidationError,
        match=rf"{NULL_VARIANT_LABEL!r} label can be used only for the null variant",
    ):
        get_variant_label(
            VariantDescription([VariantProperty("a", "b", "c")]),
            NULL_VARIANT_LABEL,
        )
    with pytest.raises(
        ValidationError,
        match=re.escape(
            f"Invalid variant label: 'foo/bar' (must be up to {VARIANT_LABEL_LENGTH} "
            "alphanumeric characters)"
        ),
    ):
        get_variant_label(
            VariantDescription([VariantProperty("a", "b", "c")]),
            "foo/bar",
        )
    with pytest.raises(
        ValidationError,
        match=re.escape(
            "Invalid variant label: '12345678901234567' (must be up to "
            f"{VARIANT_LABEL_LENGTH} alphanumeric characters)"
        ),
    ):
        get_variant_label(
            VariantDescription([VariantProperty("a", "b", "c")]),
            "12345678901234567",
        )


@pytest.mark.parametrize("plugin_use", PluginUse.__members__.values())
def test_make_variant_dist_info_expand_build_plugin_properties(
    plugin_use: PluginUse,
) -> None:
    vdesc = VariantDescription(
        [
            VariantProperty("test_namespace", "name1", "val1a"),
        ]
    )
    plugin_api = "tests.mocked_plugins:MockedPluginA"
    vinfo = VariantInfo(
        namespace_priorities=["test_namespace"],
        providers={
            "test_namespace": ProviderInfo(
                plugin_api=plugin_api,
                optional=True,
                plugin_use=plugin_use,
            )
        },
    )

    expected: VariantsJsonDict = {
        VARIANTS_JSON_SCHEMA_KEY: VARIANTS_JSON_SCHEMA_URL,
        VARIANT_INFO_DEFAULT_PRIO_KEY: {
            VARIANT_INFO_NAMESPACE_KEY: ["test_namespace"],
        },
        VARIANT_INFO_PROVIDER_DATA_KEY: {
            "test_namespace": {
                VARIANT_INFO_PROVIDER_OPTIONAL_KEY: True,
                VARIANT_INFO_PROVIDER_PLUGIN_API_KEY: plugin_api,
            },
        },
        VARIANTS_JSON_VARIANT_DATA_KEY: {
            "test": {
                "test_namespace": {
                    "name1": ["val1a"],
                }
            },
        },
    }

    if plugin_use == PluginUse.NONE:
        expected[VARIANT_INFO_PROVIDER_DATA_KEY]["test_namespace"][
            VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY
        ] = "none"
    if plugin_use == PluginUse.BUILD:
        expected[VARIANT_INFO_PROVIDER_DATA_KEY]["test_namespace"][
            VARIANT_INFO_PROVIDER_PLUGIN_USE_KEY
        ] = "build"
        expected[VARIANT_INFO_DEFAULT_PRIO_KEY][VARIANT_INFO_FEATURE_KEY] = {
            "test_namespace": ["name1", "name2"],
        }
        expected[VARIANT_INFO_DEFAULT_PRIO_KEY][VARIANT_INFO_PROPERTY_KEY] = {
            "test_namespace": {
                "name1": ["val1a", "val1b"],
                "name2": ["val2a", "val2b", "val2c"],
            },
        }

    assert (
        json.loads(
            make_variant_dist_info(
                vdesc,
                variant_info=vinfo,
                variant_label="test",
                expand_build_plugin_properties=True,
            )
        )
        == expected
    )


def test_make_variant_dist_info_invalid_build_plugin() -> None:
    vdesc = VariantDescription(
        [
            VariantProperty("test_namespace", "name1", "val1d"),
        ]
    )
    plugin_api = "tests.mocked_plugins:MockedPluginA"
    vinfo = VariantInfo(
        namespace_priorities=["test_namespace"],
        providers={
            "test_namespace": ProviderInfo(
                plugin_api=plugin_api,
                optional=True,
                plugin_use=PluginUse.BUILD,
            )
        },
    )

    with pytest.raises(
        ValidationError,
        match=r"Property 'test_namespace :: name1 :: val1d' is not installable "
        r"according to the respective provider plugin; is plugin-use == 'build' valid "
        "for this plugin?",
    ):
        make_variant_dist_info(
            vdesc,
            variant_info=vinfo,
            expand_build_plugin_properties=True,
        )

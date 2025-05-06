from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from variantlib.constants import VALIDATION_FEATURE_NAME_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.models.configuration import VariantConfiguration
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty


def test_default_configuration():
    config = VariantConfiguration.default()
    assert config.namespace_priorities == []
    assert config.feature_priorities == []
    assert config.property_priorities == []


@pytest.mark.parametrize(
    "config_params",
    [
        {
            "namespaces": ["omnicorp"],
            "features": [],
            "properties": [],
        },
        {
            "namespaces": ["omnicorp"],
            "features": ["omnicorp::custom_feat"],
            "properties": ["omnicorp::custom_feat::secret_value"],
        },
        {
            "namespaces": ["omnicorp", "acme_corp"],
            "features": ["omnicorp::custom_feat", "acme_corp :: custom_feat"],
            "properties": [
                "omnicorp :: custom_feat_a  ::   secret_value",
                "omnicorp :: custom_feat_b::   secret_value",
                "acme_corp::custom_feat::secret_value",
            ],
        },
    ],
)
def test_from_toml_config(config_params: dict[str, list[str]]):
    _ = VariantConfiguration.from_toml_config(
        namespace_priorities=config_params["namespaces"],
        feature_priorities=config_params["features"],
        property_priorities=config_params["properties"],
    )


@given(st.lists(st.from_regex(VALIDATION_NAMESPACE_REGEX, fullmatch=True)))
def test_namespace_priorities_validation(namespaces: list[str]):
    config = VariantConfiguration(namespace_priorities=namespaces)
    assert config.namespace_priorities == namespaces


@given(
    st.lists(st.from_regex(VALIDATION_NAMESPACE_REGEX, fullmatch=True)),
    st.lists(
        st.builds(
            VariantFeature,
            namespace=st.just("omnicorp"),
            feature=st.from_regex(VALIDATION_FEATURE_NAME_REGEX, fullmatch=True),
        )
    ),
)
def test_feature_priorities_validation(
    namespaces: list[str], features: list[VariantFeature]
):
    config = VariantConfiguration(
        namespace_priorities=namespaces, feature_priorities=features
    )
    assert config.feature_priorities == features


@given(
    st.lists(st.from_regex(VALIDATION_NAMESPACE_REGEX, fullmatch=True)),
    st.lists(
        st.builds(
            VariantFeature,
            namespace=st.from_regex(VALIDATION_NAMESPACE_REGEX, fullmatch=True),
            feature=st.from_regex(VALIDATION_FEATURE_NAME_REGEX, fullmatch=True),
        )
    ),
    st.lists(
        st.builds(
            VariantProperty,
            namespace=st.from_regex(VALIDATION_NAMESPACE_REGEX, fullmatch=True),
            feature=st.from_regex(VALIDATION_FEATURE_NAME_REGEX, fullmatch=True),
            value=st.from_regex(VALIDATION_VALUE_REGEX, fullmatch=True),
        )
    ),
)
def test_property_priorities_validation(
    namespaces: list[str],
    features: list[VariantFeature],
    properties: list[VariantProperty],
):
    config = VariantConfiguration(
        namespace_priorities=namespaces,
        feature_priorities=features,
        property_priorities=properties,
    )
    assert config.property_priorities == properties

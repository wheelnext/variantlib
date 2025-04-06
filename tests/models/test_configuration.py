from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from variantlib.constants import VALIDATION_FEATURE_REGEX
from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_VALUE_REGEX
from variantlib.models.configuration import VariantConfiguration
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty


def test_default_configuration():
    config = VariantConfiguration.default()
    assert config.namespaces_priority == []
    assert config.features_priority == []
    assert config.property_priority == []


@pytest.mark.parametrize(
    "config_params",
    [
        {
            "namespaces": ["OmniCorp"],
            "features": [],
            "properties": [],
        },
        {
            "namespaces": ["OmniCorp"],
            "features": ["OmniCorp::custom_feat"],
            "properties": ["OmniCorp::custom_feat::secret_value"],
        },
        {
            "namespaces": ["OmniCorp", "AcmeCorp"],
            "features": ["OmniCorp::custom_feat", "AcmeCorp :: custom_feat"],
            "properties": [
                "OmniCorp :: custom_featA  ::   secret_value",
                "OmniCorp :: custom_featB::   secret_value",
                "AcmeCorp::custom_feat::secret_value",
            ],
        },
    ],
)
def test_from_toml_config(config_params: dict[str, list[str]]):
    _ = VariantConfiguration.from_toml_config(
        namespaces_priority=config_params["namespaces"],
        features_priority=config_params["features"],
        property_priority=config_params["properties"],
    )


@given(st.lists(st.from_regex(VALIDATION_NAMESPACE_REGEX)))
def test_namespaces_priority_validation(namespaces: list[str]):
    config = VariantConfiguration(namespaces_priority=namespaces)
    assert config.namespaces_priority == namespaces


@given(
    st.lists(st.from_regex(VALIDATION_NAMESPACE_REGEX)),
    st.lists(
        st.builds(
            VariantFeature,
            namespace=st.just("OmniCorp"),
            feature=st.from_regex(VALIDATION_FEATURE_REGEX),
        )
    ),
)
def test_features_priority_validation(
    namespaces: list[str], features: list[VariantFeature]
):
    config = VariantConfiguration(
        namespaces_priority=namespaces, features_priority=features
    )
    assert config.features_priority == features


@given(
    st.lists(st.from_regex(VALIDATION_NAMESPACE_REGEX)),
    st.lists(
        st.builds(
            VariantFeature,
            namespace=st.from_regex(VALIDATION_NAMESPACE_REGEX),
            feature=st.from_regex(VALIDATION_FEATURE_REGEX),
        )
    ),
    st.lists(
        st.builds(
            VariantProperty,
            namespace=st.from_regex(VALIDATION_NAMESPACE_REGEX),
            feature=st.from_regex(VALIDATION_FEATURE_REGEX),
            value=st.from_regex(VALIDATION_VALUE_REGEX),
        )
    ),
)
def test_property_priority_validation(
    namespaces: list[str],
    features: list[VariantFeature],
    properties: list[VariantProperty],
):
    config = VariantConfiguration(
        namespaces_priority=namespaces,
        features_priority=features,
        property_priority=properties,
    )
    assert config.property_priority == properties

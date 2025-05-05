from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from variantlib.constants import VALIDATION_NAMESPACE_REGEX
from variantlib.constants import VALIDATION_PYTHON_PACKAGE_NAME_REGEX
from variantlib.errors import ValidationError
from variantlib.models.provider import ProviderConfig
from variantlib.models.provider import ProviderPackage
from variantlib.models.provider import VariantFeatureConfig
from variantlib.models.variant import VariantProperty

# ======================== VariantFeatureConfig ======================== #


def test_vfeat_config_creation_valid():
    """Test valid creation of VariantFeatureConfig."""
    vfeat_config = VariantFeatureConfig(name="attr_NAME", values=["7", "4", "8", "12"])
    assert vfeat_config.name == "attr_name"
    assert vfeat_config.values == ["7", "4", "8", "12"]


def test_provider_config_creation_valid():
    """Test valid creation of ProviderConfig."""
    vfeat_config1 = VariantFeatureConfig(
        name="attr_name_A", values=["7", "4", "8", "12"]
    )
    vfeat_config2 = VariantFeatureConfig(
        name="attr_name_B", values=["3", "7", "2", "18", "22"]
    )
    provider_config = ProviderConfig(
        namespace="PROVIDER", configs=[vfeat_config1, vfeat_config2]
    )

    assert provider_config.namespace == "provider"
    assert len(provider_config.configs) == 2
    assert provider_config.configs[0].name == "attr_name_a"
    assert provider_config.configs[1].name == "attr_name_b"


def test_duplicate_vfeat_config():
    """Test that a duplicate name raises a ValueError in ProviderConfig."""
    vfeat_config_1 = VariantFeatureConfig(
        name="attr_NAME", values=["7", "4", "8", "12"]
    )
    vfeat_config_2 = VariantFeatureConfig(
        name="attr_NAME", values=["7", "4", "8", "12"]
    )

    with pytest.raises(ValidationError, match="Duplicate value found: `attr_name`"):
        ProviderConfig(
            namespace="provider_name", configs=[vfeat_config_1, vfeat_config_2]
        )


def test_empty_values_list_in_vfeat_config():
    """Test VariantFeatureConfig creation with empty values."""
    with pytest.raises(
        ValidationError, match="List must have at least 1 elements, got 0"
    ):
        _ = VariantFeatureConfig(name="attr_name", values=[])


def test_single_item_values_list_in_vfeat_config():
    """Test VariantFeatureConfig creation with a single value."""
    vfeat_config = VariantFeatureConfig(name="attr_name", values=["7"])
    assert vfeat_config.name == "attr_name"
    assert vfeat_config.values == ["7"]


def test_duplicate_values_in_vfeat_config():
    """Test that duplicate values in VariantFeatureConfig do not raise an error."""
    with pytest.raises(ValidationError, match="Duplicate value found: `7` in list"):
        _ = VariantFeatureConfig(name="attr_name", values=["7", "7", "8", "12"])


def test_invalid_name_type_in_vfeat_config():
    """Test an invalid name - VariantFeatureConfig raises a ValidationError."""
    with pytest.raises(ValidationError):
        # Expecting string for `name`
        VariantFeatureConfig(name=1, values=["7", "4", "8", "12"])  # type: ignore[arg-type]


def test_invalid_values_type_in_vfeat_config():
    """Test invalid values - VariantFeatureConfig raises a ValidationError."""
    with pytest.raises(ValidationError):
        VariantFeatureConfig(
            name="attr_name",
            values="not_a_list",  # type: ignore[arg-type]
        )  # Expecting a list for `values`


def test_vfeat_config_invalid_values_type():
    """Test a invalid values VariantFeatureConfig raises a ValidationError."""
    with pytest.raises(ValidationError):
        VariantFeatureConfig(name="attr_name", values="invalid_values")  # type: ignore[arg-type]


def test_vfeat_config_non_string_name():
    """Test that non-string name in VariantFeatureConfig raise an error."""
    with pytest.raises(ValidationError):
        VariantFeatureConfig(name=12345, values=["7", "4", "8", "12"])  # type: ignore[arg-type]


def test_name_config_repr():
    """Test the __repr__ method of VariantFeatureConfig."""
    vfeat_config = VariantFeatureConfig(
        name="attr_NAME", values=["7", "4", "8.4.3", "12.1"]
    )
    expected_repr = (
        "VariantFeatureConfig(name='attr_name', values=['7', '4', '8.4.3', '12.1'])"
    )
    assert repr(vfeat_config) == expected_repr


def test_failing_regex_name():
    with pytest.raises(ValidationError, match="must match regex"):
        _ = VariantFeatureConfig(name="", values=["7", "4", "8", "12"])

    for c in "@#$%&*^()[]?.!-{}[]\\/ ":
        with pytest.raises(ValidationError, match="must match regex"):
            _ = VariantFeatureConfig(name=f"name{c}value", values=["7", "4", "8", "12"])


def test_failing_regex_value():
    with pytest.raises(ValidationError, match="must match regex"):
        _ = VariantFeatureConfig(name="name", values=[""])

    for c in "@#$%&*^()[]?!-{}[]\\/ ":
        with pytest.raises(ValidationError, match="must match regex"):
            _ = VariantFeatureConfig(name="name", values=[f"val{c}ue"])


# ======================== ProviderConfig ======================== #


def test_provider_config_invalid_namespace_type():
    """Test that an invalid namespace type raises a validation error."""
    with pytest.raises(ValidationError):
        ProviderConfig(
            namespace=1,  # type: ignore[arg-type]
            configs=[
                VariantFeatureConfig(name="attr_name", values=["7", "4", "8", "12"])
            ],
        )


def test_provider_config_invalid_configs_type():
    """Test that an invalid configs type raises a validation error."""
    with pytest.raises(ValidationError):
        ProviderConfig(
            namespace="provider_name",
            configs="not_a_list_of_vfeat_configs",  # type: ignore[arg-type]
        )


def test_provider_config_invalid_name_type_in_configs():
    """Test that invalid `VariantFeatureConfig` inside `ProviderConfig` raises a
    ValidationError."""
    with pytest.raises(ValidationError):
        ProviderConfig(
            namespace="provider_name",
            configs=[{"name": "attr_name", "values": ["7", "4", "8", "12"]}],  # type: ignore[list-item]
        )


def test_empty_provider_config():
    """Test creation of ProviderConfig with an empty list of VariantFeatureConfigs."""
    with pytest.raises(
        ValidationError, match="List must have at least 1 elements, got 0"
    ):
        _ = ProviderConfig(namespace="provider_name", configs=[])


def test_provider_config_invalid_vfeat_config_type():
    """Test that invalid `VariantFeatureConfig` types within ProviderConfig raise an
    error."""
    from types import SimpleNamespace

    with pytest.raises(ValidationError):
        ProviderConfig(
            namespace="provider_name",
            configs=[
                VariantFeatureConfig(name="attr_name", values=["7", "4", "8", "12"]),
                SimpleNamespace(name=1, values=["1", "2"]),  # type: ignore[list-item]
            ],
        )


def test_provider_config_repr():
    """Test the __repr__ method of ProviderConfig."""
    vfeat_config_1 = VariantFeatureConfig(
        name="attr_name_A", values=["7", "4", "8", "12"]
    )
    vfeat_config_2 = VariantFeatureConfig(
        name="attr_name_B", values=["3", "7", "2", "18"]
    )
    provider_config = ProviderConfig(
        namespace="provider_name", configs=[vfeat_config_1, vfeat_config_2]
    )

    expected_repr = (
        "ProviderConfig(namespace='provider_name', "
        "configs=[VariantFeatureConfig(name='attr_name_a', values=['7', '4', '8', '12']), "  # noqa: E501
        "VariantFeatureConfig(name='attr_name_b', values=['3', '7', '2', '18'])])"
    )
    assert repr(provider_config) == expected_repr


def test_to_list_of_properties():
    provider_cfg = ProviderConfig(
        namespace="ns",
        configs=[
            VariantFeatureConfig("a", ["a1", "a2", "a3"]),
            VariantFeatureConfig("c", ["c3", "c2", "c1"]),
            VariantFeatureConfig("b", ["b1"]),
        ],
    )

    assert list(provider_cfg.to_list_of_properties()) == [
        VariantProperty("ns", "a", "a1"),
        VariantProperty("ns", "a", "a2"),
        VariantProperty("ns", "a", "a3"),
        VariantProperty("ns", "c", "c3"),
        VariantProperty("ns", "c", "c2"),
        VariantProperty("ns", "c", "c1"),
        VariantProperty("ns", "b", "b1"),
    ]


# ======================== ProviderPackage ======================== #


@pytest.fixture
def valid_namespace():
    return "namespace"


@pytest.fixture
def valid_package_name():
    return "package_name"


def test_provider_package_init(valid_namespace, valid_package_name):
    provider_package = ProviderPackage(
        namespace=valid_namespace, package_name=valid_package_name
    )
    assert provider_package.namespace == valid_namespace
    assert provider_package.package_name == valid_package_name


@given(
    namespace=st.text(
        alphabet=st.characters(min_codepoint=0, max_codepoint=32)
        | st.characters(min_codepoint=58, max_codepoint=64)
        | st.characters(min_codepoint=91, max_codepoint=96)
        | st.characters(min_codepoint=123, max_codepoint=127)
    ),
    package_name=st.text(
        alphabet=st.characters(min_codepoint=0, max_codepoint=32)
        | st.characters(min_codepoint=58, max_codepoint=64)
        | st.characters(min_codepoint=91, max_codepoint=96)
        | st.characters(min_codepoint=123, max_codepoint=127)
    ),
)
def test_provider_package_init_invalid(namespace, package_name):
    with pytest.raises(ValidationError):
        ProviderPackage(namespace=namespace, package_name=package_name)


@given(
    namespace=st.from_regex(VALIDATION_NAMESPACE_REGEX, fullmatch=True),
    package_name=st.from_regex(VALIDATION_PYTHON_PACKAGE_NAME_REGEX, fullmatch=True),
)
def test_provider_package(namespace: str, package_name: str):
    provider_package = ProviderPackage(namespace=namespace, package_name=package_name)
    assert provider_package.namespace == namespace.lower()
    assert provider_package.package_name == package_name
    assert provider_package.to_str() == f"{namespace.lower()}: {package_name}"

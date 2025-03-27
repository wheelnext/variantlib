from __future__ import annotations

import pytest

from variantlib.config import KeyConfig
from variantlib.config import ProviderConfig


def test_key_config_creation_valid():
    """Test valid creation of KeyConfig."""
    key_config = KeyConfig(key="attr_nameA", values=["7", "4", "8", "12"])
    assert key_config.key == "attr_nameA"
    assert key_config.values == ["7", "4", "8", "12"]


def test_provider_config_creation_valid():
    """Test valid creation of ProviderConfig."""
    key_config_1 = KeyConfig(key="attr_nameA", values=["7", "4", "8", "12"])
    key_config_2 = KeyConfig(key="attr_nameB", values=["3", "7", "2", "18", "22"])
    provider_config = ProviderConfig(
        namespace="provider_name", configs=[key_config_1, key_config_2]
    )

    assert provider_config.namespace == "provider_name"
    assert len(provider_config.configs) == 2
    assert provider_config.configs[0].key == "attr_nameA"
    assert provider_config.configs[1].key == "attr_nameB"


def test_duplicate_key_config():
    """Test that a duplicate key raises a ValueError in ProviderConfig."""
    key_config_1 = KeyConfig(key="attr_nameA", values=["7", "4", "8", "12"])
    key_config_2 = KeyConfig(key="attr_nameA", values=["7", "4", "8", "12"])

    with pytest.raises(
        ValueError, match="Duplicate `KeyConfig` for key='attr_nameA' found."
    ):
        ProviderConfig(namespace="provider_name", configs=[key_config_1, key_config_2])


def test_empty_values_list_in_key_config():
    """Test KeyConfig creation with empty values."""
    with pytest.raises(AssertionError):
        _ = KeyConfig(key="attr_nameA", values=[])


def test_single_item_values_list_in_key_config():
    """Test KeyConfig creation with a single value."""
    key_config = KeyConfig(key="attr_nameA", values=["7"])
    assert key_config.key == "attr_nameA"
    assert key_config.values == ["7"]


def test_duplicate_values_in_key_config():
    """Test that duplicate values in KeyConfig do not raise an error."""
    with pytest.raises(ValueError, match="Duplicate value found: '7' in `values`"):
        _ = KeyConfig(key="attr_nameA", values=["7", "7", "8", "12"])


def test_invalid_key_type_in_key_config():
    """Test that an invalid key type in KeyConfig raises a validation error."""
    with pytest.raises(TypeError):
        # Expecting string for `key`
        KeyConfig(key=1, values=["7", "4", "8", "12"])  # type: ignore[arg-type]


def test_invalid_values_type_in_key_config():
    """Test that invalid values type in KeyConfig raises a validation error."""
    with pytest.raises(TypeError):
        KeyConfig(
            key="attr_nameA",
            values="not_a_list",  # type: ignore[arg-type]
        )  # Expecting a list for `values`


def test_provider_config_invalid_namespace_type():
    """Test that an invalid namespace type raises a validation error."""
    with pytest.raises(TypeError):
        ProviderConfig(
            namespace=1,  # type: ignore[arg-type]
            configs=[KeyConfig(key="attr_nameA", values=["7", "4", "8", "12"])],
        )


def test_provider_config_invalid_configs_type():
    """Test that an invalid configs type raises a validation error."""
    with pytest.raises(TypeError):
        ProviderConfig(
            namespace="provider_name",
            configs="not_a_list_of_key_configs",  # type: ignore[arg-type]
        )


def test_provider_config_invalid_key_type_in_configs():
    """Test that invalid `KeyConfig` inside `ProviderConfig` raises an error."""
    with pytest.raises(TypeError):
        ProviderConfig(
            namespace="provider_name",
            configs=[{"key": "attr_nameA", "values": ["7", "4", "8", "12"]}],  # type: ignore[list-item]
        )


def test_empty_provider_config():
    """Test creation of ProviderConfig with an empty list of KeyConfigs."""
    with pytest.raises(AssertionError):
        _ = ProviderConfig(namespace="provider_name", configs=[])


def test_provider_config_invalid_key_config_type():
    """Test that invalid key config types within ProviderConfig raise an error."""
    from types import SimpleNamespace

    with pytest.raises(TypeError):
        ProviderConfig(
            namespace="provider_name",
            configs=[
                KeyConfig(key="attr_nameA", values=["7", "4", "8", "12"]),
                SimpleNamespace(key=1, values=["1", "2"]),  # type: ignore[list-item]
            ],
        )


def test_key_config_invalid_values_type():
    """Test that KeyConfig raises a validation error for non-list type values."""
    with pytest.raises(TypeError):
        KeyConfig(key="attr_nameA", values="invalid_values")  # type: ignore[arg-type]


def test_key_config_non_string_key():
    """Test that non-string keys in KeyConfig raise an error."""
    with pytest.raises(TypeError):
        KeyConfig(key=12345, values=["7", "4", "8", "12"])  # type: ignore[arg-type]


def test_provider_config_repr():
    """Test the __repr__ method of ProviderConfig."""
    key_config_1 = KeyConfig(key="attr_nameA", values=["7", "4", "8", "12"])
    key_config_2 = KeyConfig(key="attr_nameB", values=["3", "7", "2", "18", "22"])
    provider_config = ProviderConfig(
        namespace="provider_name", configs=[key_config_1, key_config_2]
    )

    expected_repr = (
        "ProviderConfig(namespace='provider_name', "
        "configs=[KeyConfig(key='attr_nameA', values=['7', '4', '8', '12']), "
        "KeyConfig(key='attr_nameB', values=['3', '7', '2', '18', '22'])])"
    )
    assert repr(provider_config) == expected_repr


def test_key_config_repr():
    """Test the __repr__ method of KeyConfig."""
    key_config = KeyConfig(key="attr_nameA", values=["7", "4", "8.4.3", "12.1"])
    expected_repr = "KeyConfig(key='attr_nameA', values=['7', '4', '8.4.3', '12.1'])"
    assert repr(key_config) == expected_repr


def test_failing_regex_key():
    with pytest.raises(ValueError, match="must match regex"):
        _ = KeyConfig(key="", values=["7", "4", "8", "12"])

    for c in "@#$%&*^()[]?.!-{}[]\\/ ":
        with pytest.raises(ValueError, match="must match regex"):
            _ = KeyConfig(key=f"key{c}value", values=["7", "4", "8", "12"])


def test_failing_regex_value():
    with pytest.raises(ValueError, match="does not follow the proper format"):
        _ = KeyConfig(key="key", values=[""])

    for c in "@#$%&*^()[]?!-{}[]\\/ ":
        with pytest.raises(ValueError, match="does not follow the proper format"):
            _ = KeyConfig(key="key", values=[f"val{c}ue"])

import hashlib
import random
import string

import pytest
from variantlib import VARIANT_HASH_LEN
from variantlib.meta import VariantDescription
from variantlib.meta import VariantMeta

# -----------------------------------------------
# Test for VariantMeta Class
# -----------------------------------------------


def test_variantmeta_initialization():
    # Valid initialization
    valid_variant = VariantMeta(
        provider="OmniCorp", key="access_key", value="secret_value"
    )
    assert valid_variant.provider == "OmniCorp"
    assert valid_variant.key == "access_key"
    assert valid_variant.value == "secret_value"


def test_variantmeta_invalid_type():
    # Invalid initialization for provider (should raise TypeError)
    with pytest.raises(TypeError):
        VariantMeta(provider="OmniCorp", key="access_key", value=123)

    # Invalid initialization for key (should raise TypeError)
    with pytest.raises(TypeError):
        VariantMeta(provider="OmniCorp", key=123, value="secret_value")

    # Invalid initialization for value (should raise TypeError)
    with pytest.raises(TypeError):
        VariantMeta(provider="OmniCorp", key="access_key", value=123)


def test_variantmeta_data():
    # Test the repr method of VariantMeta
    variant = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    expected_data = "OmniCorp :: access_key :: secret_value"
    assert variant.data == expected_data


def test_variantmeta_repr():
    # Test the repr method of VariantMeta
    variant = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    expected_data = "<VariantMeta: `OmniCorp :: access_key :: secret_value`>"
    assert repr(variant) == expected_data


def test_variantmeta_hash():
    # Test the hashing functionality of VariantMeta
    variant1 = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    variant2 = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    assert hash(variant1) == hash(variant2)

    # Different value, same provider and key. Should also result in identical hash
    variant3 = VariantMeta(
        provider="OmniCorp", key="access_key", value="different_value"
    )
    assert hash(variant1) == hash(variant3)


def test_variantmeta_val_property():
    # Test the val property
    variant = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    expected_val = "OmniCorp :: access_key :: secret_value"
    assert variant.data == expected_val


def test_failing_regex_provider():
    with pytest.raises(ValueError, match="must match regex"):
        _ = VariantMeta(provider="", key="key", value="value")

    for c in "@#$%&*^()[]!-{}[]\\/ ":
        with pytest.raises(ValueError, match="must match regex"):
            _ = VariantMeta(provider=f"Omni{c}Corp", key="key", value="value")


def test_failing_regex_key():
    with pytest.raises(ValueError, match="must match regex"):
        _ = VariantMeta(provider="provider", key="", value="value")

    for c in "@#$%&*^()[]!-{}[]\\/ ":
        with pytest.raises(ValueError, match="must match regex"):
            _ = VariantMeta(provider="provider", key=f"access{c}key", value="value")


def test_failing_regex_value():
    with pytest.raises(ValueError, match="must match regex"):
        _ = VariantMeta(provider="provider", key="key", value="")

    for c in "@#$%&*^()[]!-{}[]\\/ ":
        with pytest.raises(ValueError, match="must match regex"):
            _ = VariantMeta(provider="provider", key="key", value=f"val{c}ue")


def test_from_str_valid():
    # Test case: Valid string input
    input_str = "OmniCorp :: access_key :: secret_value"
    variant_meta = VariantMeta.from_str(input_str)

    # Check if the resulting object matches the expected values
    assert variant_meta.provider == "OmniCorp"
    assert variant_meta.key == "access_key"
    assert variant_meta.value == "secret_value"
    assert (
        repr(variant_meta) == "<VariantMeta: `OmniCorp :: access_key :: secret_value`>"
    )


def test_from_str_missing_parts():
    with pytest.raises(ValueError, match="Invalid format"):
        VariantMeta.from_str("OmniCorp :: access_key")


def test_from_str_extra_colons():
    with pytest.raises(ValueError, match="Invalid format"):
        VariantMeta.from_str("OmniCorp :: access_key :: secret_value :: extra")


def test_from_str_empty_value():
    with pytest.raises(ValueError, match="Invalid format"):
        VariantMeta.from_str("OmniCorp :: access_key ::")


def test_from_str_edge_case_empty_string():
    with pytest.raises(ValueError, match="Invalid format"):
        VariantMeta.from_str("")


def test_from_str_trailing_spaces():
    # Test case: Input with leading/trailing spaces
    input_str = "   OmniCorp :: access_key :: secret_value   "
    variant_meta = VariantMeta.from_str(input_str.strip())

    # Check if it still correctly parses and matches the expected values
    assert variant_meta.provider == "OmniCorp"
    assert variant_meta.key == "access_key"
    assert variant_meta.value == "secret_value"
    assert (
        repr(variant_meta) == "<VariantMeta: `OmniCorp :: access_key :: secret_value`>"
    )


def test_from_str_invalid_format():
    # Test case: Input with invalid format
    input_str = "OmniCorp, access_key, secret_value"

    with pytest.raises(ValueError, match="Invalid format"):
        VariantMeta.from_str(input_str)


# -----------------------------------------------
# Test for VariantDescription Class
# -----------------------------------------------


def test_variantdesc_repr():
    # Test the repr method of VariantMeta
    variant = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    variant_description = VariantDescription([variant])
    expected_data = (
        "<VariantDescription: "
        "[<VariantMeta: `OmniCorp :: access_key :: secret_value`>]>"
    )
    assert repr(variant_description) == expected_data


def test_variantdescription_initialization():
    # Valid input: List of VariantMeta instances
    meta1 = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    meta2 = VariantMeta(
        provider="TyrellCorporation", key="client_id", value="secret_key"
    )
    variant_description = VariantDescription([meta1, meta2])

    # Check that the _data property is a list
    assert isinstance(variant_description.data, list)
    assert len(variant_description.data) == 2
    assert variant_description.data == [meta1, meta2]


def test_variantdescription_invalid_data():
    # Test invalid data (not a list or tuple)
    with pytest.raises(AssertionError):
        VariantDescription("invalid_data")

    # Test data containing non-VariantMeta instances
    invalid_meta = {
        "provider": "OmniCorp",
        "key": "access_key",
        "value": "secret_value",
    }
    with pytest.raises(AssertionError):
        VariantDescription([invalid_meta])


def test_variantdescription_duplicate_data():
    # Test that duplicate VariantMeta instances are removed
    meta1 = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    with pytest.raises(ValueError, match="Duplicate value"):
        _ = VariantDescription([meta1, meta1])


def test_variantdescription_partial_duplicate_data():
    # Test that duplicate VariantMeta instances are removed
    meta1 = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    meta2 = VariantMeta(provider="OmniCorp", key="access_key", value="another_value")
    with pytest.raises(ValueError, match="Duplicate value"):
        _ = VariantDescription([meta1, meta2])


def test_variantdescription_sorted_data():
    # Ensure that the data is sorted by provider, key, value
    meta1 = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    meta2 = VariantMeta(
        provider="TyrellCorporation", key="client_id", value="secret_key"
    )
    meta3 = VariantMeta(provider="OmniCorp", key="secret_key", value="client_value")
    variant_description = VariantDescription([meta1, meta2, meta3])

    # Check that data is sorted by provider, key, and value
    sorted_data = sorted(
        [meta1, meta2, meta3], key=lambda x: (x.provider, x.key, x.value)
    )
    assert list(variant_description) == sorted_data


def test_variantdescription_hexdigest():
    # Ensure that the hexdigest property works correctly
    meta1 = VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")
    meta2 = VariantMeta(
        provider="TyrellCorporation", key="client_id", value="secret_key"
    )
    variant_description = VariantDescription([meta1, meta2])

    # Compute the expected hash using shake_128 (mock the hash output for testing)
    expected_hash = hashlib.shake_128()
    expected_hash.update(meta1.data.encode("utf-8"))
    expected_hash.update(meta2.data.encode("utf-8"))
    expected_hexdigest = expected_hash.hexdigest(int(VARIANT_HASH_LEN / 2))

    assert variant_description.hexdigest == expected_hexdigest


# -----------------------------------------------
# Fuzzy Testing
# -----------------------------------------------


@pytest.mark.parametrize(
    ("provider", "key", "value"),
    [
        ("OmniCorp", "access_key", "secret_value"),
        ("TyrellCorporation", "client_id", "secret_key"),
        ("InGenTechnologies", "tenant_id", "secret_value123"),
        ("CyberdyneSystems", "app_id", "app_secret"),
        ("SoylentCorporation", "token", "auth_value_123"),
    ],
)
def test_fuzzy_variantmeta(provider, key, value):
    # Fuzzy test for random combinations of VariantMeta
    variant = VariantMeta(provider=provider, key=key, value=value)
    assert variant.provider == provider
    assert variant.key == key
    assert variant.value == value


@pytest.mark.parametrize(
    "meta_data",
    [
        ([VariantMeta(provider="OmniCorp", key="access_key", value="secret_value")]),
        (
            [
                VariantMeta(
                    provider="TyrellCorporation", key="client_id", value="secret_key"
                ),
                VariantMeta(
                    provider="OmniCorp", key="access_key", value="secret_value"
                ),
            ]
        ),
        (
            [
                VariantMeta(
                    provider="OmniCorp", key="access_key", value="secret_value"
                ),
                VariantMeta(
                    provider="TyrellCorporation", key="client_id", value="secret_key"
                ),
                VariantMeta(
                    provider="OmniCorp", key="secret_key", value="client_value"
                ),
            ]
        ),
    ],
)
def test_fuzzy_variantdescription(meta_data):
    # Fuzzy test for random combinations of VariantDescription
    variant_description = VariantDescription(meta_data)
    assert isinstance(variant_description.data, list)
    assert len(variant_description.data) >= 1


# -----------------------------------------------
# Test Hexdigest with Random Values
# -----------------------------------------------


@pytest.mark.parametrize("num_entries", [1, 3, 5, 10])
def test_random_hexdigest(num_entries):
    # Generate random data for VariantMeta instances
    def random_string(length: int) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    meta_data = [
        VariantMeta(
            provider=random_string(5), key=random_string(5), value=random_string(8)
        )
        for _ in range(num_entries)
    ]
    variant_description = VariantDescription(meta_data)
    assert isinstance(variant_description.hexdigest, str)
    assert len(variant_description.hexdigest) == VARIANT_HASH_LEN

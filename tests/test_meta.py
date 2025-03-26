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
        namespace="OmniCorp", key="access_key", value="secret_value"
    )
    assert valid_variant.namespace == "OmniCorp"
    assert valid_variant.key == "access_key"
    assert valid_variant.value == "secret_value"


def test_variantmeta_invalid_type():
    # Invalid initialization for provider (should raise TypeError)
    with pytest.raises(TypeError):
        VariantMeta(namespace="OmniCorp", key="access_key", value=123)

    # Invalid initialization for key (should raise TypeError)
    with pytest.raises(TypeError):
        VariantMeta(namespace="OmniCorp", key=123, value="secret_value")

    # Invalid initialization for value (should raise TypeError)
    with pytest.raises(TypeError):
        VariantMeta(namespace="OmniCorp", key="access_key", value=123)


def test_variantmeta_data():
    # Test the repr method of VariantMeta
    vmeta = VariantMeta(namespace="OmniCorp", key="access_key", value="secret_value")
    expected_data = "OmniCorp :: access_key :: secret_value"
    assert vmeta.to_str() == expected_data


def test_variantmeta_hash():
    # Test the hashing functionality of VariantMeta
    variant1 = VariantMeta(namespace="OmniCorp", key="access_key", value="secret_value")
    variant2 = VariantMeta(namespace="OmniCorp", key="access_key", value="secret_value")
    assert hash(variant1) == hash(variant2)

    # Different value, same namespace and key. Should also result in identical hash
    variant3 = VariantMeta(
        namespace="OmniCorp", key="access_key", value="different_value"
    )
    assert hash(variant1) == hash(variant3)


def test_variantmeta_val_property():
    # Test the val property
    vmeta = VariantMeta(namespace="OmniCorp", key="access_key", value="secret_value")
    expected_val = "OmniCorp :: access_key :: secret_value"
    assert vmeta.to_str() == expected_val


def test_failing_regex_namespace():
    with pytest.raises(ValueError, match="must match regex"):
        _ = VariantMeta(namespace="", key="key", value="value")

    for c in "@#$%&*^()[]?.!-{}[]\\/ ":
        with pytest.raises(ValueError, match="must match regex"):
            _ = VariantMeta(namespace=f"Omni{c}Corp", key="key", value="value")


def test_failing_regex_key():
    with pytest.raises(ValueError, match="must match regex"):
        _ = VariantMeta(namespace="provider", key="", value="value")

    for c in "@#$%&*^()[]?.!-{}[]\\/ ":
        with pytest.raises(ValueError, match="must match regex"):
            _ = VariantMeta(namespace="provider", key=f"access{c}key", value="value")


def test_failing_regex_value():
    with pytest.raises(ValueError, match="must match regex"):
        _ = VariantMeta(namespace="provider", key="key", value="")

    for c in "@#$%&*^()[]?!-{}[]\\/ ":
        with pytest.raises(ValueError, match="must match regex"):
            _ = VariantMeta(namespace="provider", key="key", value=f"val{c}ue")


@pytest.mark.parametrize(
    "input_str",
    [
        "OmniCorp :: access_key :: secret_value",
        "OmniCorp::access_key::secret_value",
        "OmniCorp ::access_key::     secret_value",
    ],
)
def test_from_str_valid(input_str: str):
    # Test case: Valid string input
    variant_meta = VariantMeta.from_str(input_str)

    # Check if the resulting object matches the expected values
    assert variant_meta.namespace == "OmniCorp"
    assert variant_meta.key == "access_key"
    assert variant_meta.value == "secret_value"


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
    assert variant_meta.namespace == "OmniCorp"
    assert variant_meta.key == "access_key"
    assert variant_meta.value == "secret_value"


def test_from_str_invalid_format():
    # Test case: Input with invalid format
    input_str = "OmniCorp, access_key, secret_value"

    with pytest.raises(ValueError, match="Invalid format"):
        VariantMeta.from_str(input_str)


def test_variantmeta_serialization():
    vmeta = VariantMeta(namespace="provider", key="key", value="value")
    assert vmeta.serialize() == {
        "namespace": "provider",
        "key": "key",
        "value": "value",
    }


def test_variantmeta_deserialization():
    data = {
        "namespace": "provider",
        "key": "key",
        "value": "value",
    }

    vmeta = VariantMeta.deserialize(data)

    assert vmeta.namespace == data["namespace"]
    assert vmeta.key == data["key"]
    assert vmeta.value == data["value"]


# -----------------------------------------------
# Test for VariantDescription Class
# -----------------------------------------------


def test_variantdescription_initialization():
    # Valid input: List of VariantMeta instances
    meta1 = VariantMeta(namespace="OmniCorp", key="access_key", value="secret_value")
    meta2 = VariantMeta(
        namespace="TyrellCorporation", key="client_id", value="secret_key"
    )
    variant_description = VariantDescription([meta1, meta2])

    # Check that the _data property is a list
    assert isinstance(variant_description.data, list)
    assert len(variant_description.data) == 2
    assert variant_description.data == [meta1, meta2]


def test_variantdescription_invalid_data():
    # Test invalid data (not a list or tuple)
    with pytest.raises(TypeError):
        VariantDescription("invalid_data")

    # Test data containing non-VariantMeta instances
    invalid_meta = {
        "namespace": "OmniCorp",
        "key": "access_key",
        "value": "secret_value",
    }
    with pytest.raises(TypeError):
        VariantDescription([invalid_meta])


def test_variantdescription_duplicate_data():
    # Test that duplicate VariantMeta instances are removed
    meta1 = VariantMeta(namespace="OmniCorp", key="access_key", value="secret_value")
    with pytest.raises(ValueError, match="Duplicate value"):
        _ = VariantDescription([meta1, meta1])


def test_variantdescription_partial_duplicate_data():
    # Test that duplicate VariantMeta instances are removed
    meta1 = VariantMeta(namespace="OmniCorp", key="access_key", value="secret_value")
    meta2 = VariantMeta(namespace="OmniCorp", key="access_key", value="another_value")
    with pytest.raises(ValueError, match="Duplicate value"):
        _ = VariantDescription([meta1, meta2])


def test_variantdescription_sorted_data():
    # Ensure that the data is sorted by namespace, key, value
    meta1 = VariantMeta(namespace="OmniCorp", key="access_key", value="secret_value")
    meta2 = VariantMeta(
        namespace="TyrellCorporation", key="client_id", value="secret_key"
    )
    meta3 = VariantMeta(namespace="OmniCorp", key="secret_key", value="client_value")
    variant_description = VariantDescription([meta1, meta2, meta3])

    # Check that data is sorted by namespace, key, and value
    sorted_data = sorted(
        [meta1, meta2, meta3], key=lambda x: (x.namespace, x.key, x.value)
    )
    assert list(variant_description) == sorted_data


def test_variantdescription_hexdigest():
    # Ensure that the hexdigest property works correctly
    meta1 = VariantMeta(namespace="OmniCorp", key="access_key", value="secret_value")
    meta2 = VariantMeta(
        namespace="TyrellCorporation", key="client_id", value="secret_key"
    )
    variant_description = VariantDescription([meta1, meta2])

    # Compute the expected hash using shake_128 (mock the hash output for testing)
    expected_hash = hashlib.shake_128()
    expected_hash.update(meta1.to_str().encode("utf-8"))
    expected_hash.update(meta2.to_str().encode("utf-8"))
    expected_hexdigest = expected_hash.hexdigest(int(VARIANT_HASH_LEN / 2))

    assert variant_description.hexdigest == expected_hexdigest


def test_variantdescription_serialization():
    vmeta = VariantMeta(namespace="provider", key="key", value="value")
    vdesc = VariantDescription(data=[vmeta])

    assert vdesc.serialize() == [
        {
            "namespace": "provider",
            "key": "key",
            "value": "value",
        }
    ]


def test_variantdescription_deserialization():
    data = [
        {
            "namespace": "provider",
            "key": "key",
            "value": "value",
        }
    ]

    vdesc = VariantDescription.deserialize(data)

    assert len(vdesc.data) == 1
    assert vdesc.data[0].namespace == "provider"
    assert vdesc.data[0].key == "key"
    assert vdesc.data[0].value == "value"
    assert vdesc.hexdigest == "5b7306b3"


# -----------------------------------------------
# Fuzzy Testing
# -----------------------------------------------


@pytest.mark.parametrize(
    ("namespace", "key", "value"),
    [
        ("OmniCorp", "access_key", "secret_value"),
        ("TyrellCorporation", "client_id", "secret_key"),
        ("InGenTechnologies", "tenant_id", "secret_value123"),
        ("SoylentCorporation", "token", "auth_value_123"),
        ("CyberdyneSystems", "version", "10.1"),
        ("CyberdyneSystems", "version", "10.1.4"),
    ],
)
def test_fuzzy_variantmeta(namespace, key, value):
    # Fuzzy test for random combinations of VariantMeta
    variant = VariantMeta(namespace=namespace, key=key, value=value)
    assert variant.namespace == namespace
    assert variant.key == key
    assert variant.value == value


@pytest.mark.parametrize(
    "meta_data",
    [
        ([VariantMeta(namespace="OmniCorp", key="access_key", value="secret_value")]),
        (
            [
                VariantMeta(
                    namespace="TyrellCorporation", key="client_id", value="secret_key"
                ),
                VariantMeta(
                    namespace="OmniCorp", key="access_key", value="secret_value"
                ),
            ]
        ),
        (
            [
                VariantMeta(
                    namespace="OmniCorp", key="access_key", value="secret_value"
                ),
                VariantMeta(
                    namespace="TyrellCorporation", key="client_id", value="secret_key"
                ),
                VariantMeta(
                    namespace="OmniCorp", key="secret_key", value="client_value"
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
            namespace=random_string(5), key=random_string(5), value=random_string(8)
        )
        for _ in range(num_entries)
    ]
    variant_description = VariantDescription(meta_data)
    assert isinstance(variant_description.hexdigest, str)
    assert len(variant_description.hexdigest) == VARIANT_HASH_LEN

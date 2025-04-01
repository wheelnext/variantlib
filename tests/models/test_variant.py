from __future__ import annotations

import hashlib
import random
import string

import pytest

from variantlib.constants import VARIANT_HASH_LEN
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantMetadata

# -----------------------------------------------
# Test for VariantMetadata Class
# -----------------------------------------------


def test_variantmeta_initialization():
    # Valid initialization
    valid_variant = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    assert valid_variant.namespace == "OmniCorp"
    assert valid_variant.feature == "custom_feat"
    assert valid_variant.value == "secret_value"


def test_variantmeta_invalid_type():
    # Invalid initialization for provider (should raise ValidationError)
    with pytest.raises(ValidationError):
        VariantMetadata(namespace="OmniCorp", feature="custom_feat", value=123)  # type: ignore[arg-type]

    # Invalid initialization for feature (should raise ValidationError)
    with pytest.raises(ValidationError):
        VariantMetadata(namespace="OmniCorp", feature=123, value="secret_value")  # type: ignore[arg-type]

    # Invalid initialization for value (should raise ValidationError)
    with pytest.raises(ValidationError):
        VariantMetadata(namespace="OmniCorp", feature="custom_feat", value=123)  # type: ignore[arg-type]


def test_variantmeta_data():
    # Test the repr method of VariantMetadata
    vmeta = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    expected_data = "OmniCorp :: custom_feat :: secret_value"
    assert vmeta.to_str() == expected_data


def test_variantmeta_hexdigest():
    # Test the hashing functionality of VariantMetadata
    vmeta1 = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="value1"
    )
    vmeta2 = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="value2"
    )
    assert vmeta1.hexdigest == vmeta2.hexdigest

    # Different value, same namespace and feature. Should also result in identical hash
    vmeta3 = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="value2"
    )
    assert vmeta1.hexdigest == vmeta3.hexdigest


def test_variantmeta_val_property():
    # Test the val property
    vmeta = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    expected_val = "OmniCorp :: custom_feat :: secret_value"
    assert vmeta.to_str() == expected_val


def test_failing_regex_namespace():
    with pytest.raises(ValidationError, match="must match regex"):
        _ = VariantMetadata(namespace="", feature="feature", value="value")

    for c in "@#$%&*^()[]?.!-{}[]\\/ ":
        with pytest.raises(ValidationError, match="must match regex"):
            _ = VariantMetadata(
                namespace=f"Omni{c}Corp", feature="feature", value="value"
            )


def test_failing_regex_feature():
    with pytest.raises(ValidationError, match="must match regex"):
        _ = VariantMetadata(namespace="provider", feature="", value="value")

    for c in "@#$%&*^()[]?.!-{}[]\\/ ":
        with pytest.raises(ValidationError, match="must match regex"):
            _ = VariantMetadata(
                namespace="provider", feature=f"access{c}feature", value="value"
            )


def test_failing_regex_value():
    with pytest.raises(ValidationError, match="must match regex"):
        _ = VariantMetadata(namespace="provider", feature="feature", value="")

    for c in "@#$%&*^()[]?!-{}[]\\/ ":
        with pytest.raises(ValidationError, match="must match regex"):
            _ = VariantMetadata(
                namespace="provider", feature="feature", value=f"val{c}ue"
            )


@pytest.mark.parametrize(
    "input_str",
    [
        "OmniCorp :: custom_feat :: secret_value",
        "OmniCorp::custom_feat::secret_value",
        "OmniCorp ::custom_feat::     secret_value",
    ],
)
def test_from_str_valid(input_str: str):
    # Test case: Valid string input
    variant_meta = VariantMetadata.from_str(input_str)

    # Check if the resulting object matches the expected values
    assert variant_meta.namespace == "OmniCorp"
    assert variant_meta.feature == "custom_feat"
    assert variant_meta.value == "secret_value"


def test_from_str_missing_parts():
    with pytest.raises(ValidationError, match="Invalid format"):
        VariantMetadata.from_str("OmniCorp :: custom_feat")


def test_from_str_extra_colons():
    with pytest.raises(ValidationError, match="Invalid format"):
        VariantMetadata.from_str("OmniCorp :: custom_feat :: secret_value :: extra")


def test_from_str_empty_value():
    with pytest.raises(ValidationError, match="Invalid format"):
        VariantMetadata.from_str("OmniCorp :: custom_feat ::")


def test_from_str_edge_case_empty_string():
    with pytest.raises(ValidationError, match="Invalid format"):
        VariantMetadata.from_str("")


def test_from_str_trailing_spaces():
    # Test case: Input with leading/trailing spaces
    input_str = "   OmniCorp :: custom_feat :: secret_value   "
    variant_meta = VariantMetadata.from_str(input_str.strip())

    # Check if it still correctly parses and matches the expected values
    assert variant_meta.namespace == "OmniCorp"
    assert variant_meta.feature == "custom_feat"
    assert variant_meta.value == "secret_value"


def test_from_str_invalid_format():
    # Test case: Input with invalid format
    input_str = "OmniCorp, custom_feat, secret_value"

    with pytest.raises(ValidationError, match="Invalid format"):
        VariantMetadata.from_str(input_str)


def test_variantmeta_serialization():
    vmeta = VariantMetadata(namespace="provider", feature="feature", value="value")
    assert vmeta.serialize() == {
        "namespace": "provider",
        "feature": "feature",
        "value": "value",
    }


def test_variantmeta_deserialization():
    data = {
        "namespace": "provider",
        "feature": "feature",
        "value": "value",
    }

    vmeta = VariantMetadata.deserialize(data)

    assert vmeta.namespace == data["namespace"]
    assert vmeta.feature == data["feature"]
    assert vmeta.value == data["value"]


# -----------------------------------------------
# Test for VariantDescription Class
# -----------------------------------------------


def test_variantdescription_initialization():
    # Valid input: List of VariantMetadata instances
    meta1 = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    meta2 = VariantMetadata(
        namespace="TyrellCorporation", feature="client_id", value="secret_pass"
    )
    variant_description = VariantDescription([meta1, meta2])

    # Check that the _data property is a list
    assert isinstance(variant_description.data, list)
    assert len(variant_description.data) == 2
    assert variant_description.data == [meta1, meta2]


def test_variantdescription_invalid_data():
    # Test invalid data (not a list or tuple)
    with pytest.raises(ValidationError):
        VariantDescription("invalid_data")  # type: ignore[arg-type]

    # Test data containing non-VariantMetadata instances
    invalid_meta = {
        "namespace": "OmniCorp",
        "feature": "custom_feat",
        "value": "secret_value",
    }
    with pytest.raises(ValidationError):
        VariantDescription([invalid_meta])  # type: ignore[list-item]


def test_variantdescription_duplicate_data():
    # Test that duplicate VariantMetadata instances are removed
    meta1 = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    with pytest.raises(ValidationError, match="Duplicate value"):
        _ = VariantDescription([meta1, meta1])


def test_variantdescription_partial_duplicate_data():
    # Test that duplicate VariantMetadata instances are removed
    meta1 = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    meta2 = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="another_value"
    )
    with pytest.raises(ValidationError, match="Duplicate value"):
        _ = VariantDescription([meta1, meta2])


def test_variantdescription_sorted_data():
    # Ensure that the data is sorted by namespace, feature, value
    meta1 = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    meta2 = VariantMetadata(
        namespace="TyrellCorporation", feature="client_id", value="secret_pass"
    )
    meta3 = VariantMetadata(
        namespace="OmniCorp", feature="secret_pass", value="client_value"
    )
    variant_description = VariantDescription([meta1, meta2, meta3])

    # Check that data is sorted by namespace, feature, and value
    sorted_data = sorted(
        [meta1, meta2, meta3], key=lambda x: (x.namespace, x.feature, x.value)
    )
    assert list(variant_description) == sorted_data


def test_variantdescription_hexdigest():
    # Ensure that the hexdigest property works correctly
    meta1 = VariantMetadata(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    meta2 = VariantMetadata(
        namespace="TyrellCorporation", feature="client_id", value="secret_pass"
    )
    variant_description = VariantDescription([meta1, meta2])

    # Compute the expected hash using shake_128 (mock the hash output for testing)
    expected_hash = hashlib.shake_128()
    expected_hash.update(meta1.to_str().encode("utf-8"))
    expected_hash.update(meta2.to_str().encode("utf-8"))
    expected_hexdigest = expected_hash.hexdigest(int(VARIANT_HASH_LEN / 2))

    assert variant_description.hexdigest == expected_hexdigest


def test_variantdescription_serialization():
    vmeta = VariantMetadata(namespace="provider", feature="feature", value="value")
    vdesc = VariantDescription(data=[vmeta])

    assert vdesc.serialize() == [
        {
            "namespace": "provider",
            "feature": "feature",
            "value": "value",
        }
    ]


def test_variantdescription_deserialization():
    data = [
        {
            "namespace": "provider",
            "feature": "feature",
            "value": "value",
        }
    ]

    vdesc = VariantDescription.deserialize(data)

    assert len(vdesc.data) == 1
    assert vdesc.data[0].namespace == "provider"
    assert vdesc.data[0].feature == "feature"
    assert vdesc.data[0].value == "value"
    assert vdesc.hexdigest == "fafeda9c"


# -----------------------------------------------
# Fuzzy Testing
# -----------------------------------------------


@pytest.mark.parametrize(
    ("namespace", "feature", "value"),
    [
        ("OmniCorp", "custom_feat", "secret_value"),
        ("TyrellCorporation", "client_id", "secret_pass"),
        ("InGenTechnologies", "tenant_id", "secret_value123"),
        ("SoylentCorporation", "token", "auth_value_123"),
        ("CyberdyneSystems", "version", "10.1"),
        ("CyberdyneSystems", "version", "10.1.4"),
    ],
)
def test_fuzzy_variantmeta(namespace, feature, value):
    # Fuzzy test for random combinations of VariantMetadata
    variant = VariantMetadata(namespace=namespace, feature=feature, value=value)
    assert variant.namespace == namespace
    assert variant.feature == feature
    assert variant.value == value


@pytest.mark.parametrize(
    "meta_data",
    [
        (
            [
                VariantMetadata(
                    namespace="OmniCorp", feature="custom_feat", value="secret_value"
                )
            ]
        ),
        (
            [
                VariantMetadata(
                    namespace="TyrellCorporation",
                    feature="client_id",
                    value="secret_pass",
                ),
                VariantMetadata(
                    namespace="OmniCorp", feature="custom_feat", value="secret_value"
                ),
            ]
        ),
        (
            [
                VariantMetadata(
                    namespace="OmniCorp", feature="custom_feat", value="secret_value"
                ),
                VariantMetadata(
                    namespace="TyrellCorporation",
                    feature="client_id",
                    value="secret_pass",
                ),
                VariantMetadata(
                    namespace="OmniCorp", feature="secret_pass", value="client_value"
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
    # Generate random data for VariantMetadata instances
    def random_string(length: int) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    meta_data = [
        VariantMetadata(
            namespace=random_string(5), feature=random_string(5), value=random_string(8)
        )
        for _ in range(num_entries)
    ]
    variant_description = VariantDescription(meta_data)
    assert isinstance(variant_description.hexdigest, str)
    assert len(variant_description.hexdigest) == VARIANT_HASH_LEN

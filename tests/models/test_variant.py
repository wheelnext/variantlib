from __future__ import annotations

import hashlib
import random
import string

import pytest

from variantlib.constants import VARIANT_HASH_LEN
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty

# -----------------------------------------------
# Test for VariantProperty Class
# -----------------------------------------------


def test_variantprop_initialization():
    # Valid initialization
    vprop = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    assert vprop.namespace == "OmniCorp"
    assert vprop.feature == "custom_feat"
    assert vprop.value == "secret_value"


def test_variantprop_invalid_type():
    # Invalid initialization for provider (should raise ValidationError)
    with pytest.raises(ValidationError):
        VariantProperty(namespace="OmniCorp", feature="custom_feat", value=123)  # type: ignore[arg-type]

    # Invalid initialization for feature (should raise ValidationError)
    with pytest.raises(ValidationError):
        VariantProperty(namespace="OmniCorp", feature=123, value="secret_value")  # type: ignore[arg-type]

    # Invalid initialization for value (should raise ValidationError)
    with pytest.raises(ValidationError):
        VariantProperty(namespace="OmniCorp", feature="custom_feat", value=123)  # type: ignore[arg-type]


def test_variantprop_data():
    # Test the repr method of VariantProperty
    vprop = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    expected_data = "OmniCorp :: custom_feat :: secret_value"
    assert vprop.to_str() == expected_data


def test_variantprop_hexdigest():
    # Test the hashing functionality of VariantProperty
    vprop1 = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="value1"
    )
    vprop2 = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="value2"
    )
    assert vprop1.feature_hash == vprop2.feature_hash
    assert vprop1.property_hash != vprop2.property_hash

    # Different object, same everything. Should also result in identical hash
    vprop3 = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="value1"
    )
    assert vprop1.feature_hash == vprop3.feature_hash


def test_variantprop_to_str():
    vprop = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )

    assert vprop.to_str() == "OmniCorp :: custom_feat :: secret_value"


def test_failing_regex_namespace():
    with pytest.raises(ValidationError, match="must match regex"):
        _ = VariantProperty(namespace="", feature="feature", value="value")

    for c in "@#$%&*^()[]?.!-{}[]\\/ ":
        with pytest.raises(ValidationError, match="must match regex"):
            _ = VariantProperty(
                namespace=f"Omni{c}Corp", feature="feature", value="value"
            )


def test_failing_regex_feature():
    with pytest.raises(ValidationError, match="must match regex"):
        _ = VariantProperty(namespace="provider", feature="", value="value")

    for c in "@#$%&*^()[]?.!-{}[]\\/ ":
        with pytest.raises(ValidationError, match="must match regex"):
            _ = VariantProperty(
                namespace="provider", feature=f"access{c}feature", value="value"
            )


def test_failing_regex_value():
    with pytest.raises(ValidationError, match="must match regex"):
        _ = VariantProperty(namespace="provider", feature="feature", value="")

    for c in "@#$%&*^()[]?!-{}[]\\/ ":
        with pytest.raises(ValidationError, match="must match regex"):
            _ = VariantProperty(
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
    vprop = VariantProperty.from_str(input_str)

    # Check if the resulting object matches the expected values
    assert vprop.namespace == "OmniCorp"
    assert vprop.feature == "custom_feat"
    assert vprop.value == "secret_value"


def test_from_str_missing_parts():
    with pytest.raises(ValidationError, match="Invalid format"):
        VariantProperty.from_str("OmniCorp :: custom_feat")


def test_from_str_extra_colons():
    with pytest.raises(ValidationError, match="Invalid format"):
        VariantProperty.from_str("OmniCorp :: custom_feat :: secret_value :: extra")


def test_from_str_empty_value():
    with pytest.raises(ValidationError, match="Invalid format"):
        VariantProperty.from_str("OmniCorp :: custom_feat ::")


def test_from_str_edge_case_empty_string():
    with pytest.raises(ValidationError, match="Invalid format"):
        VariantProperty.from_str("")


def test_from_str_trailing_spaces():
    # Test case: Input with leading/trailing spaces
    input_str = "   OmniCorp :: custom_feat :: secret_value   "
    vprop = VariantProperty.from_str(input_str.strip())

    # Check if it still correctly parses and matches the expected values
    assert vprop.namespace == "OmniCorp"
    assert vprop.feature == "custom_feat"
    assert vprop.value == "secret_value"


def test_from_str_invalid_format():
    # Test case: Input with invalid format
    input_str = "OmniCorp, custom_feat, secret_value"

    with pytest.raises(ValidationError, match="Invalid format"):
        VariantProperty.from_str(input_str)


def test_variantprop_serialization():
    vprop = VariantProperty(namespace="provider", feature="feature", value="value")
    assert vprop.serialize() == {
        "namespace": "provider",
        "feature": "feature",
        "value": "value",
    }


def test_variantprop_deserialization():
    data = {
        "namespace": "provider",
        "feature": "feature",
        "value": "value",
    }

    vprop = VariantProperty.deserialize(data)

    assert vprop.namespace == data["namespace"]
    assert vprop.feature == data["feature"]
    assert vprop.value == data["value"]


def test_variantprop_sorting():
    data = [
        VariantProperty("z", "a", "a"),
        VariantProperty("z", "a", "b"),
        VariantProperty("a", "b", "a"),
        VariantProperty("a", "a", "a"),
        VariantProperty("a", "a", "z"),
        VariantProperty("c", "x", "a"),
        VariantProperty("z", "a", "a"),
        VariantProperty("b", "b", "a"),
        VariantProperty("b", "b", "b"),
        VariantProperty("z", "b", "a"),
    ]

    assert sorted(data) == [
        VariantProperty("a", "a", "a"),
        VariantProperty("a", "a", "z"),
        VariantProperty("a", "b", "a"),
        VariantProperty("b", "b", "a"),
        VariantProperty("b", "b", "b"),
        VariantProperty("c", "x", "a"),
        VariantProperty("z", "a", "a"),
        VariantProperty("z", "a", "a"),
        VariantProperty("z", "a", "b"),
        VariantProperty("z", "b", "a"),
    ]


# -----------------------------------------------
# Test for VariantDescription Class
# -----------------------------------------------


def test_variantdescription_initialization():
    # Valid input: List of VariantProperty instances
    vprop1 = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    vprop2 = VariantProperty(
        namespace="TyrellCorporation", feature="client_id", value="secret_pass"
    )
    vdesc = VariantDescription([vprop1, vprop2])

    # Check that the _data property is a list
    assert isinstance(vdesc.properties, list)
    assert len(vdesc.properties) == 2
    assert vdesc.properties == [vprop1, vprop2]


def test_variantdescription_invalid_data():
    # Test invalid data (not a list or tuple)
    with pytest.raises(ValidationError):
        VariantDescription("invalid_data")  # type: ignore[arg-type]

    # Test data containing non-VariantProperty instances
    invalid_vprop = {
        "namespace": "OmniCorp",
        "feature": "custom_feat",
        "value": "secret_value",
    }
    with pytest.raises(ValidationError):
        VariantDescription([invalid_vprop])  # type: ignore[list-item]


def test_variantdescription_duplicate_data():
    # Test that duplicate VariantProperty instances are removed
    vprop1 = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    with pytest.raises(ValidationError, match="Duplicate value"):
        _ = VariantDescription([vprop1, vprop1])


def test_variantdescription_partial_duplicate_data():
    # Test that duplicate VariantProperty instances are removed
    vprop1 = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    vprop2 = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="another_value"
    )
    with pytest.raises(ValidationError, match="Duplicate value"):
        _ = VariantDescription([vprop1, vprop2])


def test_variantdescription_sorted_data():
    # Ensure that the data is sorted by namespace, feature, value
    vprop1 = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    vprop2 = VariantProperty(
        namespace="TyrellCorporation", feature="client_id", value="secret_pass"
    )
    vprop3 = VariantProperty(
        namespace="OmniCorp", feature="secret_pass", value="client_value"
    )
    vdesc = VariantDescription([vprop1, vprop2, vprop3])

    # Check that data is sorted by namespace, feature, and value
    sorted_vprops = sorted(
        [vprop1, vprop2, vprop3], key=lambda x: (x.namespace, x.feature, x.value)
    )
    assert vdesc.properties == sorted_vprops


def test_variantdescription_hexdigest():
    # Ensure that the hexdigest property works correctly
    vprop1 = VariantProperty(
        namespace="OmniCorp", feature="custom_feat", value="secret_value"
    )
    vprop2 = VariantProperty(
        namespace="TyrellCorporation", feature="client_id", value="secret_pass"
    )
    vprops = [vprop1, vprop2]
    vdesc = VariantDescription(vprops)

    # Compute the expected hash using shake_128 (mock the hash output for testing)
    hash_object = hashlib.sha256(
        b"OmniCorp :: custom_feat :: secret_value\n"
        b"TyrellCorporation :: client_id :: secret_pass\n"
    )
    expected_hexdigest = hash_object.hexdigest()[:VARIANT_HASH_LEN]

    assert vdesc.hexdigest == expected_hexdigest


def test_variantdescription_hexdigest_adjacent_strings():
    assert (
        VariantDescription(
            [
                VariantProperty("a", "b", "cx"),
                VariantProperty("d", "e", "f"),
            ]
        ).hexdigest
        != VariantDescription(
            [
                VariantProperty("a", "b", "c"),
                VariantProperty("xd", "e", "f"),
            ]
        ).hexdigest
    )


def test_variantdescription_serialization():
    vprop = VariantProperty(namespace="provider", feature="feature", value="value")
    vdesc = VariantDescription(properties=[vprop])

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

    assert len(vdesc.properties) == 1
    assert vdesc.properties[0].namespace == "provider"
    assert vdesc.properties[0].feature == "feature"
    assert vdesc.properties[0].value == "value"
    assert vdesc.hexdigest == "c44d3adf"


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
def test_fuzzy_variantprop(namespace, feature, value):
    # Fuzzy test for random combinations of VariantProperty
    variant = VariantProperty(namespace=namespace, feature=feature, value=value)
    assert variant.namespace == namespace
    assert variant.feature == feature
    assert variant.value == value


@pytest.mark.parametrize(
    "vprop",
    [
        (
            [
                VariantProperty(
                    namespace="OmniCorp", feature="custom_feat", value="secret_value"
                )
            ]
        ),
        (
            [
                VariantProperty(
                    namespace="TyrellCorporation",
                    feature="client_id",
                    value="secret_pass",
                ),
                VariantProperty(
                    namespace="OmniCorp", feature="custom_feat", value="secret_value"
                ),
            ]
        ),
        (
            [
                VariantProperty(
                    namespace="OmniCorp", feature="custom_feat", value="secret_value"
                ),
                VariantProperty(
                    namespace="TyrellCorporation",
                    feature="client_id",
                    value="secret_pass",
                ),
                VariantProperty(
                    namespace="OmniCorp", feature="secret_pass", value="client_value"
                ),
            ]
        ),
    ],
)
def test_fuzzy_variantdescription(vprop: list[VariantProperty]):
    # Fuzzy test for random combinations of VariantDescription
    vdesc = VariantDescription(vprop)
    assert isinstance(vdesc.properties, list)
    assert len(vdesc.properties) >= 1


# -----------------------------------------------
# Test Hexdigest with Random Values
# -----------------------------------------------


@pytest.mark.parametrize("num_entries", [1, 3, 5, 10])
def test_random_hexdigest(num_entries):
    # Generate random data for VariantProperty instances
    def random_string(length: int) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    vprop = [
        VariantProperty(
            namespace=random_string(5), feature=random_string(5), value=random_string(8)
        )
        for _ in range(num_entries)
    ]
    vdesc = VariantDescription(vprop)
    assert isinstance(vdesc.hexdigest, str)
    assert len(vdesc.hexdigest) == VARIANT_HASH_LEN

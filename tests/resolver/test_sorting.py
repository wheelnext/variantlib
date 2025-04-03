import sys

import pytest

from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.resolver.sorting import get_feature_priority
from variantlib.resolver.sorting import get_namespace_priority
from variantlib.resolver.sorting import get_property_priority
from variantlib.resolver.sorting import get_variant_property_priority_tuple
from variantlib.resolver.sorting import sort_variant_properties
from variantlib.resolver.sorting import sort_variants_descriptions

# ========================= get_property_priority =========================== #


def test_get_property_priority():
    vprop1 = VariantProperty(namespace="OmniCorp", feature="feat", value="value1")
    vprop2 = VariantProperty(namespace="OmniCorp", feature="feat", value="value2")
    vprop3 = VariantProperty(namespace="OmniCorp", feature="feat", value="value3")
    assert get_property_priority(vprop1, [vprop1, vprop2]) == 0
    assert get_property_priority(vprop2, [vprop1, vprop2]) == 1
    assert get_property_priority(vprop1, [vprop1, vprop2, vprop3]) == 0
    assert get_property_priority(vprop2, [vprop1, vprop2, vprop3]) == 1


def test_negative_get_property_priority():
    vprop1 = VariantProperty(namespace="OmniCorp", feature="feat", value="value1")
    vprop2 = VariantProperty(namespace="OmniCorp", feature="feat", value="value2")

    assert get_property_priority(vprop1, None) == sys.maxsize
    assert get_property_priority(vprop1, []) == sys.maxsize
    assert get_property_priority(vprop1, [vprop2]) == sys.maxsize


def test_get_property_priority_validation_error():
    with pytest.raises(ValidationError):
        get_property_priority(vprop="not a `VariantProperty`", property_priorities=None)  # type: ignore[arg-type]

    vprop = VariantProperty(namespace="OmniCorp", feature="feature", value="value")

    with pytest.raises(ValidationError):
        get_property_priority(vprop=vprop, property_priorities="not a list or None")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        get_property_priority(
            vprop=vprop,
            property_priorities=[{"not a VariantProperty": True}],  # type: ignore[list-item]
        )


# ========================== get_feature_priority =========================== #


def test_get_feature_priority():
    vprop1 = VariantProperty(namespace="OmniCorp", feature="feature", value="value")
    vprop2 = VariantProperty(namespace="OmniCorp", feature="other_feat", value="value")
    feature_priorities = [
        VariantFeature(namespace="OmniCorp", feature="feature"),
        VariantFeature(namespace="OmniCorp", feature="other_feat"),
    ]
    assert get_feature_priority(vprop1, feature_priorities) == 0
    assert get_feature_priority(vprop2, feature_priorities) == 1


def test_negative_get_feature_priority():
    vprop = VariantProperty(namespace="OmniCorp", feature="no_exist", value="value")
    vfeat = VariantFeature(namespace="OmniCorp", feature="feature")

    assert get_feature_priority(vprop, None) == sys.maxsize
    assert get_feature_priority(vprop, []) == sys.maxsize
    assert get_feature_priority(vprop, [vfeat]) == sys.maxsize


def test_get_feature_priority_validation_error():
    with pytest.raises(ValidationError):
        get_feature_priority(vprop="not a `VariantProperty`", feature_priorities=None)  # type: ignore[arg-type]

    vprop = VariantProperty(namespace="OmniCorp", feature="feature", value="value")

    with pytest.raises(ValidationError):
        get_feature_priority(vprop=vprop, feature_priorities="not a list or None")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        get_feature_priority(
            vprop=vprop,
            feature_priorities=[{"not a VariantFeature": True}],  # type: ignore[list-item]
        )


# ========================= get_namespace_priority ========================== #


def test_get_namespace_priority():
    vprop1 = VariantProperty(namespace="OmniCorp", feature="feature", value="value")
    vprop2 = VariantProperty(namespace="OtherCorp", feature="feature", value="value")
    vprop3 = VariantProperty(namespace="NoCorp", feature="feature", value="value")
    namespace_priorities = ["OmniCorp", "OtherCorp"]
    assert get_namespace_priority(vprop1, namespace_priorities) == 0
    assert get_namespace_priority(vprop2, namespace_priorities) == 1
    assert get_namespace_priority(vprop3, namespace_priorities) == sys.maxsize


def test_negative_get_namespace_priority():
    vprop = VariantProperty(namespace="OmniCorp", feature="no_exist", value="value")

    assert get_namespace_priority(vprop, None) == sys.maxsize
    assert get_namespace_priority(vprop, []) == sys.maxsize
    assert get_namespace_priority(vprop, ["OtherCorp"]) == sys.maxsize


def test_get_namespace_priority_validation_error():
    with pytest.raises(ValidationError):
        get_namespace_priority(
            vprop="not a `VariantProperty`",  # type: ignore[arg-type]
            namespace_priorities=None,
        )

    vprop = VariantProperty(namespace="OmniCorp", feature="feature", value="value")

    with pytest.raises(ValidationError):
        get_namespace_priority(vprop=vprop, namespace_priorities="not a list or None")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        get_namespace_priority(vprop=vprop, namespace_priorities=[{"not a str": True}])  # type: ignore[list-item]


# =================== get_variant_property_priority_tuple =================== #


def test_get_variant_property_priority_tuple():
    vprop = VariantProperty(namespace="OmniCorp", feature="custom_feat", value="value1")
    property_priorities = [
        VariantProperty(namespace="OtherCorp", feature="other_feat", value="value2"),
        vprop,
    ]
    feature_priorities = [
        VariantFeature(namespace=vprop.namespace, feature=vprop.feature),
        VariantFeature(namespace="OmniCorp", feature="feature"),
    ]
    namespace_priorities = ["OtherCorp"]
    assert get_variant_property_priority_tuple(
        vprop, property_priorities, feature_priorities, namespace_priorities
    ) == (1, 0, sys.maxsize)


def test_get_variant_property_priority_tuple_validation_error():
    with pytest.raises(ValidationError):
        get_variant_property_priority_tuple(
            vprop="not a VariantProperty",  # type: ignore[arg-type]
            property_priorities=None,
            feature_priorities=None,
            namespace_priorities=None,
        )


# ========================= sort_variant_properties ========================= #


def test_sort_variant_properties():
    vprop_list = [
        VariantProperty(namespace="OmniCorp", feature="featA", value="value"),
        VariantProperty(namespace="OmniCorp", feature="featB", value="value1"),
        VariantProperty(namespace="OmniCorp", feature="featB", value="value2"),
        VariantProperty(namespace="OmniCorp", feature="featC", value="value"),
        VariantProperty(namespace="OmniCorp", feature="featD", value="value"),
        VariantProperty(namespace="OtherCorp", feature="featA", value="value"),
        VariantProperty(namespace="OtherCorp", feature="featB", value="value1"),
        VariantProperty(namespace="OtherCorp", feature="featB", value="value2"),
        VariantProperty(namespace="OtherCorp", feature="featC", value="value"),
        VariantProperty(namespace="OtherCorp", feature="featD", value="value"),
        VariantProperty(namespace="AnyCorp", feature="feature", value="value"),
    ]
    property_priorities = [
        VariantProperty(namespace="OtherCorp", feature="featA", value="value"),
        VariantProperty(namespace="OmniCorp", feature="featA", value="value"),
        VariantProperty(namespace="OmniCorp", feature="featC", value="value"),
        VariantProperty(namespace="OtherCorp", feature="featC", value="value"),
    ]
    feature_priorities = [
        VariantFeature(namespace="OtherCorp", feature="featB"),
        VariantFeature(namespace="OmniCorp", feature="featB"),
    ]
    namespace_priorities = ["OmniCorp", "OtherCorp"]
    sorted_vprops = sort_variant_properties(
        vprop_list, property_priorities, feature_priorities, namespace_priorities
    )
    assert sorted_vprops == [
        # sorted by property priorities
        VariantProperty(namespace="OtherCorp", feature="featA", value="value"),
        VariantProperty(namespace="OmniCorp", feature="featA", value="value"),
        VariantProperty(namespace="OmniCorp", feature="featC", value="value"),
        VariantProperty(namespace="OtherCorp", feature="featC", value="value"),
        # sorted by feature priorities
        VariantProperty(namespace="OtherCorp", feature="featB", value="value1"),
        VariantProperty(namespace="OtherCorp", feature="featB", value="value2"),
        VariantProperty(namespace="OmniCorp", feature="featB", value="value1"),
        VariantProperty(namespace="OmniCorp", feature="featB", value="value2"),
        # sorted by namespace priorities
        VariantProperty(namespace="OmniCorp", feature="featD", value="value"),
        VariantProperty(namespace="OtherCorp", feature="featD", value="value"),
        # not a listed namespace or feature or property
        VariantProperty(namespace="AnyCorp", feature="feature", value="value"),
    ]


def test_sort_variant_properties_validation_error():
    vprops = [VariantProperty(namespace="OmniCorp", feature="feat", value="value")]
    with pytest.raises(ValidationError):
        sort_variant_properties(
            vprops="not a list",  # type: ignore[arg-type]
            property_priorities=None,
            feature_priorities=None,
            namespace_priorities=None,
        )

    with pytest.raises(ValidationError):
        sort_variant_properties(
            vprops=["not a VariantProperty"],  # type: ignore[list-item]
            property_priorities=None,
            feature_priorities=None,
            namespace_priorities=None,
        )

    with pytest.raises(ValidationError):
        sort_variant_properties(
            vprops=vprops,
            property_priorities="not a list",  # type: ignore[arg-type]
            feature_priorities=None,
            namespace_priorities=None,
        )

    with pytest.raises(ValidationError):
        sort_variant_properties(
            vprops=vprops,
            property_priorities=["not a VariantProperty"],  # type: ignore[list-item]
            feature_priorities=None,
            namespace_priorities=None,
        )

    with pytest.raises(ValidationError):
        sort_variant_properties(
            vprops=vprops,
            property_priorities=None,
            feature_priorities="not a list",  # type: ignore[arg-type]
            namespace_priorities=None,
        )

    with pytest.raises(ValidationError):
        sort_variant_properties(
            vprops=vprops,
            property_priorities=None,
            feature_priorities=["not a VariantProperty"],  # type: ignore[list-item]
            namespace_priorities=None,
        )

    with pytest.raises(ValidationError):
        sort_variant_properties(
            vprops=vprops,
            property_priorities=None,
            feature_priorities=None,
            namespace_priorities="not a list",  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError):
        sort_variant_properties(
            vprops=vprops,
            property_priorities=None,
            feature_priorities=None,
            namespace_priorities=[{"not a str": True}],  # type: ignore[list-item]
        )


# ========================= sort_variants_descriptions ========================= #


def test_sort_variants_descriptions():
    vprops_proprioty_list = [
        VariantProperty(namespace="OmniCorp", feature="featA", value="value"),
        VariantProperty(namespace="OmniCorp", feature="featB", value="value1"),
        VariantProperty(namespace="OmniCorp", feature="featB", value="value2"),
        VariantProperty(namespace="OmniCorp", feature="featC", value="value"),
        VariantProperty(namespace="OmniCorp", feature="featD", value="value"),
        VariantProperty(namespace="OtherCorp", feature="featA", value="value"),
        VariantProperty(namespace="OtherCorp", feature="featB", value="value1"),
        VariantProperty(namespace="OtherCorp", feature="featB", value="value2"),
        VariantProperty(namespace="OtherCorp", feature="featC", value="value"),
        VariantProperty(namespace="OtherCorp", feature="featD", value="value"),
        VariantProperty(namespace="AnyCorp", feature="feature", value="value"),
    ]

    vdesc1 = VariantDescription(
        [
            VariantProperty(namespace="OtherCorp", feature="featA", value="value"),
            VariantProperty(namespace="OmniCorp", feature="featB", value="value1"),
            VariantProperty(namespace="OmniCorp", feature="featC", value="value"),
            VariantProperty(namespace="OtherCorp", feature="featC", value="value"),
        ]
    )
    vdesc2 = VariantDescription(
        [VariantProperty(namespace="OtherCorp", feature="featA", value="value")]
    )
    vdesc3 = VariantDescription(
        [VariantProperty(namespace="OmniCorp", feature="featA", value="value")]
    )

    assert sort_variants_descriptions(
        vdescs=[vdesc1], property_priorities=vprops_proprioty_list
    ) == [vdesc1]

    assert sort_variants_descriptions(
        vdescs=[vdesc1, vdesc2], property_priorities=vprops_proprioty_list
    ) == [vdesc1, vdesc2]

    # order permutation
    assert sort_variants_descriptions(
        vdescs=[vdesc2, vdesc1], property_priorities=vprops_proprioty_list
    ) == [vdesc1, vdesc2]

    assert sort_variants_descriptions(
        vdescs=[vdesc1, vdesc3], property_priorities=vprops_proprioty_list
    ) == [vdesc3, vdesc1]

    # order permutation
    assert sort_variants_descriptions(
        vdescs=[vdesc3, vdesc1], property_priorities=vprops_proprioty_list
    ) == [vdesc3, vdesc1]

    assert sort_variants_descriptions(
        vdescs=[vdesc2, vdesc3], property_priorities=vprops_proprioty_list
    ) == [vdesc3, vdesc2]

    # order permutation
    assert sort_variants_descriptions(
        vdescs=[vdesc3, vdesc2], property_priorities=vprops_proprioty_list
    ) == [vdesc3, vdesc2]

    assert sort_variants_descriptions(
        vdescs=[vdesc1, vdesc2, vdesc3], property_priorities=vprops_proprioty_list
    ) == [vdesc3, vdesc1, vdesc2]

    # order permutation
    assert sort_variants_descriptions(
        vdescs=[vdesc2, vdesc1, vdesc3], property_priorities=vprops_proprioty_list
    ) == [vdesc3, vdesc1, vdesc2]

    # order permutation
    assert sort_variants_descriptions(
        vdescs=[vdesc1, vdesc3, vdesc2], property_priorities=vprops_proprioty_list
    ) == [vdesc3, vdesc1, vdesc2]

    # order permutation
    assert sort_variants_descriptions(
        vdescs=[vdesc2, vdesc3, vdesc1], property_priorities=vprops_proprioty_list
    ) == [vdesc3, vdesc1, vdesc2]

    # order permutation
    assert sort_variants_descriptions(
        vdescs=[vdesc3, vdesc2, vdesc1], property_priorities=vprops_proprioty_list
    ) == [vdesc3, vdesc1, vdesc2]

    # order permutation
    assert sort_variants_descriptions(
        vdescs=[vdesc3, vdesc1, vdesc2], property_priorities=vprops_proprioty_list
    ) == [vdesc3, vdesc1, vdesc2]


def test_sort_variants_descriptions_ranking_validation_error():
    vprops = [VariantProperty(namespace="OmniCorp", feature="feat", value="value")]
    vdesc1 = [
        VariantDescription(
            properties=[
                VariantProperty(
                    namespace="OmniCorp", feature="feat", value="other_value"
                )
            ]
        )
    ]

    # Test with a completely different property (same feature, different value)
    with pytest.raises(ValidationError, match="Filtering should be applied first."):
        sort_variants_descriptions(
            vdescs=vdesc1,
            property_priorities=vprops,
        )

    vdescs2 = [
        VariantDescription(
            properties=[
                *vprops,
                VariantProperty(
                    namespace="OmniCorp", feature="other_feat", value="other_value"
                ),
            ],
        )
    ]

    # Test with an extra property not included in the property priorities
    with pytest.raises(ValidationError, match="Filtering should be applied first."):
        sort_variants_descriptions(
            vdescs=vdescs2,
            property_priorities=vprops,
        )


def test_sort_variants_descriptions_validation_error():
    vprops = [VariantProperty(namespace="OmniCorp", feature="feat", value="value")]
    vdescs = [VariantDescription(properties=vprops)]

    with pytest.raises(ValidationError):
        sort_variants_descriptions(
            vdescs="not a list",  # type: ignore[arg-type]
            property_priorities=vprops,
        )

    with pytest.raises(ValidationError):
        sort_variants_descriptions(
            vdescs=vprops,  # type: ignore[arg-type]
            property_priorities=vprops,
        )

    with pytest.raises(ValidationError):
        sort_variants_descriptions(
            vdescs=vdescs,
            property_priorities="not a list",  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError):
        sort_variants_descriptions(
            vdescs=vdescs,
            property_priorities=vdescs,  # type: ignore[arg-type]
        )

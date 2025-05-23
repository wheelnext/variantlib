from __future__ import annotations

import sys

import pytest

from variantlib.errors import ConfigurationError
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.resolver.sorting import get_feature_priorities
from variantlib.resolver.sorting import get_namespace_priorities
from variantlib.resolver.sorting import get_property_priorities
from variantlib.resolver.sorting import get_variant_property_priorities_tuple
from variantlib.resolver.sorting import sort_variant_properties
from variantlib.resolver.sorting import sort_variants_descriptions

# ========================= get_property_priorities =========================== #


def test_get_property_priorities():
    vprop1 = VariantProperty(namespace="omnicorp", feature="feat", value="value1")
    vprop2 = VariantProperty(namespace="omnicorp", feature="feat", value="value2")
    vprop3 = VariantProperty(namespace="omnicorp", feature="feat", value="value3")
    assert get_property_priorities(vprop1, [vprop1, vprop2]) == 0
    assert get_property_priorities(vprop2, [vprop1, vprop2]) == 1
    assert get_property_priorities(vprop1, [vprop1, vprop2, vprop3]) == 0
    assert get_property_priorities(vprop2, [vprop1, vprop2, vprop3]) == 1


def test_negative_get_property_priorities():
    vprop1 = VariantProperty(namespace="omnicorp", feature="feat", value="value1")
    vprop2 = VariantProperty(namespace="omnicorp", feature="feat", value="value2")

    assert get_property_priorities(vprop1, None) == sys.maxsize
    assert get_property_priorities(vprop1, []) == sys.maxsize
    assert get_property_priorities(vprop1, [vprop2]) == sys.maxsize


@pytest.mark.parametrize(
    ("vprop", "property_priorities"),
    [
        ("not a `VariantProperty`", None),
        (VariantProperty("a", "b", "c"), "not a list or None"),
        (VariantProperty("a", "b", "c"), VariantProperty("not", "a", "list")),
        (VariantProperty("a", "b", "c"), [{"not a VariantProperty": True}]),
    ],
)
def test_get_property_priorities_validation_error(
    vprop: VariantProperty, property_priorities: list[VariantProperty] | None
):
    with pytest.raises(ValidationError):
        get_property_priorities(vprop=vprop, property_priorities=property_priorities)


# ========================== get_feature_priorities =========================== #


def test_get_feature_priorities():
    vprop1 = VariantProperty(namespace="omnicorp", feature="feature", value="value")
    vprop2 = VariantProperty(namespace="omnicorp", feature="other_feat", value="value")
    feature_priorities = [
        VariantFeature(namespace="omnicorp", feature="feature"),
        VariantFeature(namespace="omnicorp", feature="other_feat"),
    ]
    assert get_feature_priorities(vprop1, feature_priorities) == 0
    assert get_feature_priorities(vprop2, feature_priorities) == 1


def test_negative_get_feature_priorities():
    vprop = VariantProperty(namespace="omnicorp", feature="no_exist", value="value")
    vfeat = VariantFeature(namespace="omnicorp", feature="feature")

    assert get_feature_priorities(vprop, None) == sys.maxsize
    assert get_feature_priorities(vprop, []) == sys.maxsize
    assert get_feature_priorities(vprop, [vfeat]) == sys.maxsize


@pytest.mark.parametrize(
    ("vprop", "feature_priorities"),
    [
        ("not a `VariantProperty`", None),
        (VariantProperty("a", "b", "c"), "not a list or None"),
        (VariantProperty("a", "b", "c"), VariantFeature("not_a", "list")),
        (VariantProperty("a", "b", "c"), [{"not a VariantFeature": True}]),
    ],
)
def test_get_feature_priorities_validation_error(
    vprop: VariantProperty, feature_priorities: list[VariantFeature] | None
):
    with pytest.raises(ValidationError):
        get_feature_priorities(vprop=vprop, feature_priorities=feature_priorities)


# ========================= get_namespace_priorities ========================== #


def test_get_namespace_priorities():
    vprop1 = VariantProperty(namespace="omnicorp", feature="feature", value="value")
    vprop2 = VariantProperty(namespace="other_corp", feature="feature", value="value")
    vprop3 = VariantProperty(namespace="no_corp", feature="feature", value="value")
    namespace_priorities = ["omnicorp", "other_corp"]
    assert get_namespace_priorities(vprop1, namespace_priorities) == 0
    assert get_namespace_priorities(vprop2, namespace_priorities) == 1
    assert get_namespace_priorities(vprop3, namespace_priorities) == sys.maxsize


def test_negative_get_namespace_priorities():
    vprop = VariantProperty(namespace="omnicorp", feature="no_exist", value="value")

    assert get_namespace_priorities(vprop, None) == sys.maxsize
    assert get_namespace_priorities(vprop, []) == sys.maxsize
    assert get_namespace_priorities(vprop, ["other_corp"]) == sys.maxsize


@pytest.mark.parametrize(
    ("vprop", "namespace_priorities"),
    [
        ("not a `VariantProperty`", None),
        (VariantProperty("a", "b", "c"), "not a list or None"),
        (VariantProperty("a", "b", "c"), [{"not a str": True}]),
    ],
)
def test_get_namespace_priorities_validation_error(
    vprop: VariantProperty, namespace_priorities: list[str] | None
):
    with pytest.raises(ValidationError):
        get_namespace_priorities(vprop=vprop, namespace_priorities=namespace_priorities)


# =================== get_variant_property_priorities_tuple =================== #


def test_get_variant_property_priorities_tuple():
    vprop = VariantProperty(namespace="omnicorp", feature="custom_feat", value="value1")
    property_priorities = [
        VariantProperty(namespace="other_corp", feature="other_feat", value="value2"),
        vprop,
    ]
    feature_priorities = [
        VariantFeature(namespace=vprop.namespace, feature=vprop.feature),
        VariantFeature(namespace="omnicorp", feature="feature"),
    ]
    namespace_priorities = ["other_corp"]
    assert get_variant_property_priorities_tuple(
        vprop, namespace_priorities, feature_priorities, property_priorities
    ) == (1, 0, sys.maxsize)


@pytest.mark.parametrize(
    ("vprop", "namespace_priorities", "feature_priorities", "property_priorities"),
    [
        ("not a `VariantProperty`", None, None, None),
        (VariantProperty("a", "b", "c"), "not a list or None", None, None),
        (
            VariantProperty("a", "b", "c"),
            [VariantProperty("not", "a", "str")],
            None,
            None,
        ),
        (VariantProperty("a", "b", "c"), None, "not a list or None", None),
        (VariantProperty("a", "b", "c"), None, ["not a VariantFeature"], None),
        (VariantProperty("a", "b", "c"), None, None, "not a list or None"),
        (VariantProperty("a", "b", "c"), None, None, ["not a VariantProperty"]),
    ],
)
def test_get_variant_property_priorities_tuple_validation_error(
    vprop: VariantProperty,
    namespace_priorities: list[str] | None,
    feature_priorities: list[VariantFeature] | None,
    property_priorities: list[VariantProperty] | None,
):
    with pytest.raises(ValidationError):
        get_variant_property_priorities_tuple(
            vprop=vprop,
            namespace_priorities=namespace_priorities,
            feature_priorities=feature_priorities,
            property_priorities=property_priorities,
        )


# ========================= sort_variant_properties ========================= #


def test_sort_variant_properties():
    vprop_list = [
        VariantProperty(namespace="omnicorp", feature="feat_a", value="value"),
        VariantProperty(namespace="omnicorp", feature="feat_b", value="value1"),
        VariantProperty(namespace="omnicorp", feature="feat_b", value="value2"),
        VariantProperty(namespace="omnicorp", feature="feat_c", value="value"),
        VariantProperty(namespace="omnicorp", feature="feat_d", value="value"),
        VariantProperty(namespace="other_corp", feature="feat_a", value="value"),
        VariantProperty(namespace="other_corp", feature="feat_b", value="value1"),
        VariantProperty(namespace="other_corp", feature="feat_b", value="value2"),
        VariantProperty(namespace="other_corp", feature="feat_c", value="value"),
        VariantProperty(namespace="other_corp", feature="feat_d", value="value"),
    ]
    property_priorities = [
        VariantProperty(namespace="other_corp", feature="feat_a", value="value"),
        VariantProperty(namespace="omnicorp", feature="feat_a", value="value"),
        VariantProperty(namespace="omnicorp", feature="feat_c", value="value"),
        VariantProperty(namespace="other_corp", feature="feat_c", value="value"),
    ]
    feature_priorities = [
        VariantFeature(namespace="other_corp", feature="feat_b"),
        VariantFeature(namespace="omnicorp", feature="feat_b"),
    ]
    namespace_priorities = ["omnicorp", "other_corp"]
    sorted_vprops = sort_variant_properties(
        vprop_list, namespace_priorities, feature_priorities, property_priorities
    )
    assert sorted_vprops == [
        # sorted by property priorities
        VariantProperty(namespace="other_corp", feature="feat_a", value="value"),
        VariantProperty(namespace="omnicorp", feature="feat_a", value="value"),
        VariantProperty(namespace="omnicorp", feature="feat_c", value="value"),
        VariantProperty(namespace="other_corp", feature="feat_c", value="value"),
        # sorted by feature priorities
        VariantProperty(namespace="other_corp", feature="feat_b", value="value1"),
        VariantProperty(namespace="other_corp", feature="feat_b", value="value2"),
        VariantProperty(namespace="omnicorp", feature="feat_b", value="value1"),
        VariantProperty(namespace="omnicorp", feature="feat_b", value="value2"),
        # sorted by namespace priorities
        VariantProperty(namespace="omnicorp", feature="feat_d", value="value"),
        VariantProperty(namespace="other_corp", feature="feat_d", value="value"),
    ]


@pytest.mark.parametrize(
    ("vprops", "namespace_priorities", "feature_priorities", "property_priorities"),
    [
        ("not a list of `VariantProperty`", None, None, None),
        (VariantProperty("not", "a", "list"), None, None, None),
        (["not a `VariantProperty`"], None, None, None),
        ([VariantProperty("a", "b", "c")], "not a list or None", None, None),
        (
            [VariantProperty("a", "b", "c")],
            [VariantProperty("not", "a", "str")],
            None,
            None,
        ),
        ([VariantProperty("a", "b", "c")], None, "not a list or None", None),
        ([VariantProperty("a", "b", "c")], None, ["not a VariantFeature"], None),
        ([VariantProperty("a", "b", "c")], None, None, "not a list or None"),
        ([VariantProperty("a", "b", "c")], None, None, ["not a VariantProperty"]),
    ],
)
def test_sort_variant_properties_validation_error(
    vprops: list[VariantProperty],
    namespace_priorities: list[str] | None,
    feature_priorities: list[VariantFeature] | None,
    property_priorities: list[VariantProperty] | None,
):
    with pytest.raises(ValidationError):
        sort_variant_properties(
            vprops=vprops,
            namespace_priorities=namespace_priorities,
            feature_priorities=feature_priorities,
            property_priorities=property_priorities,
        )


def test_sort_variant_properties_configuration_error():
    with pytest.raises(ConfigurationError):
        sort_variant_properties(
            vprops=[VariantProperty("a", "b", "c"), VariantProperty("x", "y", "z")],
            namespace_priorities=None,
            feature_priorities=None,
            property_priorities=None,
        )


# ========================= sort_variants_descriptions ========================= #


def test_sort_variants_descriptions():
    vprops_proprioty_list = [
        VariantProperty(namespace="omnicorp", feature="feat_a", value="value"),
        VariantProperty(namespace="omnicorp", feature="feat_b", value="value1"),
        VariantProperty(namespace="omnicorp", feature="feat_b", value="value2"),
        VariantProperty(namespace="omnicorp", feature="feat_c", value="value"),
        VariantProperty(namespace="omnicorp", feature="feat_d", value="value"),
        VariantProperty(namespace="other_corp", feature="feat_a", value="value"),
        VariantProperty(namespace="other_corp", feature="feat_b", value="value1"),
        VariantProperty(namespace="other_corp", feature="feat_b", value="value2"),
        VariantProperty(namespace="other_corp", feature="feat_c", value="value"),
        VariantProperty(namespace="other_corp", feature="feat_d", value="value"),
        VariantProperty(namespace="any_corp", feature="feature", value="value"),
    ]

    vdesc1 = VariantDescription(
        [
            VariantProperty(namespace="other_corp", feature="feat_a", value="value"),
            VariantProperty(namespace="omnicorp", feature="feat_b", value="value1"),
            VariantProperty(namespace="omnicorp", feature="feat_c", value="value"),
            VariantProperty(namespace="other_corp", feature="feat_c", value="value"),
        ]
    )
    vdesc2 = VariantDescription(
        [VariantProperty(namespace="other_corp", feature="feat_a", value="value")]
    )
    vdesc3 = VariantDescription(
        [VariantProperty(namespace="omnicorp", feature="feat_a", value="value")]
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


@pytest.mark.parametrize(
    "vdesc",
    [
        VariantDescription(
            properties=[
                VariantProperty(
                    namespace="omnicorp", feature="feat", value="other_value"
                )
            ]
        ),
        VariantDescription(
            properties=[
                VariantProperty(namespace="omnicorp", feature="feat", value="value"),
                VariantProperty(
                    namespace="omnicorp", feature="other_feat", value="other_value"
                ),
            ],
        ),
    ],
)
def test_sort_variants_descriptions_ranking_validation_error(vdesc: VariantDescription):
    vprops = [VariantProperty(namespace="omnicorp", feature="feat", value="value")]

    # Test with a completely different property (same feature, different value)
    with pytest.raises(ValidationError, match="Filtering should be applied first."):
        sort_variants_descriptions(
            vdescs=[vdesc],
            property_priorities=vprops,
        )


@pytest.mark.parametrize(
    ("vdescs", "property_priorities"),
    [
        ("not a list", [VariantProperty("a", "b", "c")]),
        (["not a VariantDescription"], [VariantProperty("a", "b", "c")]),
        (VariantDescription([VariantProperty("a", "b", "c")]), "not a list or None"),
        (
            VariantDescription([VariantProperty("a", "b", "c")]),
            VariantProperty("not", "a", "list"),
        ),
        (
            VariantDescription([VariantProperty("a", "b", "c")]),
            [{"not a VariantProperty": True}],
        ),
    ],
)
def test_sort_variants_descriptions_validation_error(
    vdescs: list[VariantDescription], property_priorities: list[VariantProperty]
):
    with pytest.raises(ValidationError):
        sort_variants_descriptions(
            vdescs=vdescs,
            property_priorities=property_priorities,
        )

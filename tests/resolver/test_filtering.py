from __future__ import annotations

from collections import deque

import pytest
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.resolver.filtering import filter_unsupported_feature_values
from variantlib.resolver.filtering import filter_variants_by_features
from variantlib.resolver.filtering import filter_variants_by_namespaces
from variantlib.resolver.filtering import filter_variants_by_property


@pytest.fixture(scope="session")
def vprops() -> list[VariantProperty]:
    return [
        VariantProperty(namespace="omnicorp", feature="custom_feat", value="value1"),
        VariantProperty(
            namespace="tyrell_corporation", feature="client_id", value="value2"
        ),
    ]


@pytest.fixture(scope="session")
def vdescs(vprops: list[VariantProperty]) -> list[VariantDescription]:
    """Fixture to create a list of VariantDescription objects."""
    assert len(vprops) == 2
    vprop1, vprop2 = vprops

    return [
        VariantDescription([vprop1], label="a"),
        VariantDescription([vprop2], label="b"),
        VariantDescription([vprop1, vprop2], label="c"),
    ]


# ===================== `filter_variants_by_namespaces` ===================== #


def test_filter_variants_by_namespaces(vdescs: list[VariantDescription]) -> None:
    assert len(vdescs) == 3
    vdesc1, vdesc2, _ = vdescs

    # No namespace forbidden - should return everything
    assert (
        list(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                forbidden_namespaces=[],
            )
        )
        == vdescs
    )

    # Non existing namespace forbidden - should return everything
    assert (
        list(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                forbidden_namespaces=["NonExistentNamespace"],
            )
        )
        == vdescs
    )

    # Only `omnicorp` forbidden - should return `vdesc2`
    assert list(
        filter_variants_by_namespaces(
            vdescs=vdescs,
            forbidden_namespaces=["omnicorp"],
        )
    ) == [vdesc2]

    # Only `tyrell_corporation` forbidden - should return `vdesc1`
    assert list(
        filter_variants_by_namespaces(
            vdescs=vdescs,
            forbidden_namespaces=["tyrell_corporation"],
        )
    ) == [vdesc1]

    # Both `omnicorp` and `tyrell_corporation` forbidden - should return empty
    # Note: Order should not matter
    assert (
        list(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                forbidden_namespaces=["omnicorp", "tyrell_corporation"],
            )
        )
        == []
    )

    assert (
        list(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                forbidden_namespaces=["tyrell_corporation", "omnicorp"],
            )
        )
        == []
    )


@pytest.mark.parametrize(
    ("vdescs", "forbidden_namespaces"),
    [
        (
            [VariantDescription([VariantProperty("a", "b", "c")], label="test")],
            "not a list",
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")], label="test")],
            [VariantProperty("not", "a", "str")],
        ),
        ("not a list", ["omnicorp"]),
        (["not a `VariantDescription`"], ["omnicorp"]),
    ],
)
def test_filter_variants_by_namespaces_validation_error(
    vdescs: list[VariantDescription], forbidden_namespaces: list[str]
) -> None:
    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                forbidden_namespaces=forbidden_namespaces,
            ),
            maxlen=0,
        )


# ====================== `filter_variants_by_features` ====================== #


def test_filter_variants_by_features(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
) -> None:
    assert len(vprops) == 2
    vprop1, vprop2 = vprops

    assert len(vdescs) == 3
    vdesc1, vdesc2, _ = vdescs

    vfeat1 = vprop1.feature_object
    vfeat2 = vprop2.feature_object

    # No feature forbidden - should return everything
    assert (
        list(
            filter_variants_by_features(
                vdescs=vdescs,
                forbidden_features=[],
            )
        )
        == vdescs
    )

    # Non existing feature forbidden - should return everything
    assert (
        list(
            filter_variants_by_features(
                vdescs=vdescs,
                forbidden_features=[
                    VariantFeature(namespace="umbrella_corporation", feature="ai")
                ],
            )
        )
        == vdescs
    )

    # Only `vfeat1` forbidden - should return `vdesc2`
    assert list(
        filter_variants_by_features(
            vdescs=vdescs,
            forbidden_features=[vfeat1],
        )
    ) == [vdesc2]

    # Only `vfeat2` forbidden - should return `vdesc1`
    assert list(
        filter_variants_by_features(
            vdescs=vdescs,
            forbidden_features=[vfeat2],
        )
    ) == [vdesc1]

    # Both of vfeats forbidden - should return empty
    # Note: Order should not matter
    assert (
        list(
            filter_variants_by_features(
                vdescs=vdescs,
                forbidden_features=[vfeat1, vfeat2],
            )
        )
        == []
    )

    assert (
        list(
            filter_variants_by_features(
                vdescs=vdescs,
                forbidden_features=[vfeat2, vfeat1],
            )
        )
        == []
    )


@pytest.mark.parametrize(
    ("vdescs", "forbidden_features"),
    [
        (
            [VariantDescription([VariantProperty("a", "b", "c")], label="test")],
            "not a list",
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")], label="test")],
            ["not a `VariantFeature`"],
        ),
        ("not a list", VariantFeature("a", "b")),
        (["not a `VariantDescription`"], VariantFeature("a", "b")),
    ],
)
def test_filter_variants_by_features_validation_error(
    vdescs: list[VariantDescription], forbidden_features: list[VariantFeature]
) -> None:
    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_features(
                vdescs=vdescs, forbidden_features=forbidden_features
            ),
            maxlen=0,
        )


# ====================== `filter_variants_by_property` ====================== #


def test_filter_variants_by_property(
    vdescs: list[VariantDescription],
    vprops: list[VariantProperty],
) -> None:
    assert len(vprops) == 2
    vprop1, vprop2 = vprops

    assert len(vdescs) == 3
    vdesc1, vdesc2, _ = vdescs

    # No property allowed - should return empty list
    assert (
        list(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[],
                forbidden_properties=[],
            )
        )
        == []
    )

    # Non existing property allowed - should return empty list
    assert (
        list(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[
                    VariantProperty(
                        namespace="umbrella_corporation", feature="ai", value="chatbot"
                    )
                ],
                forbidden_properties=[],
            )
        )
        == []
    )

    # Non existing property forbidden - should return empty list
    assert (
        list(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[],
                forbidden_properties=[
                    VariantProperty(
                        namespace="umbrella_corporation", feature="ai", value="chatbot"
                    )
                ],
            )
        )
        == []
    )

    # Only `vprop1` allowed - should return `vdesc1` if not forbidden explicitly
    assert list(
        filter_variants_by_property(
            vdescs=vdescs,
            allowed_properties=[vprop1],
            forbidden_properties=[],
        )
    ) == [vdesc1]

    assert (
        list(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[vprop1],
                forbidden_properties=[vprop1],
            )
        )
        == []
    )

    assert list(
        filter_variants_by_property(
            vdescs=vdescs,
            allowed_properties=[vprop1],
            forbidden_properties=[vprop2],
        )
    ) == [vdesc1]

    # Only `vprop2` allowed - should return `vdesc2` if not forbidden explicitly
    assert list(
        filter_variants_by_property(
            vdescs=vdescs,
            allowed_properties=[vprop2],
            forbidden_properties=[],
        )
    ) == [vdesc2]

    assert list(
        filter_variants_by_property(
            vdescs=vdescs,
            allowed_properties=[vprop2],
            forbidden_properties=[vprop1],
        )
    ) == [vdesc2]

    assert (
        list(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[vprop2],
                forbidden_properties=[vprop2],
            )
        )
        == []
    )

    # Both of vprops - should return all `vdescs` if neither vprop1 or vprop2 is
    # forbidden explictly
    # Note: Order should not matter
    assert (
        list(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[vprop1, vprop2],
                forbidden_properties=[],
            )
        )
        == vdescs
    )

    assert list(
        filter_variants_by_property(
            vdescs=vdescs,
            allowed_properties=[vprop1, vprop2],
            forbidden_properties=[vprop1],
        )
    ) == [vdesc2]

    assert list(
        filter_variants_by_property(
            vdescs=vdescs,
            allowed_properties=[vprop1, vprop2],
            forbidden_properties=[vprop2],
        )
    ) == [vdesc1]

    assert (
        list(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[vprop2, vprop1],
                forbidden_properties=[],
            )
        )
        == vdescs
    )

    assert list(
        filter_variants_by_property(
            vdescs=vdescs,
            allowed_properties=[vprop2, vprop1],
            forbidden_properties=[vprop1],
        )
    ) == [vdesc2]

    assert list(
        filter_variants_by_property(
            vdescs=vdescs,
            allowed_properties=[vprop2, vprop1],
            forbidden_properties=[vprop2],
        )
    ) == [vdesc1]


@pytest.mark.parametrize(
    ("vdescs", "allowed_properties", "forbidden_properties"),
    [
        (
            "not a list",
            [VariantProperty("a", "b", "c")],
            [VariantProperty("a", "b", "c")],
        ),
        (
            [VariantProperty("not", "a", "variantdescription")],
            [VariantProperty("a", "b", "c")],
            [VariantProperty("a", "b", "c")],
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")], label="test")],
            "not a list",
            [VariantProperty("a", "b", "c")],
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")], label="test")],
            ["not a `VariantFeature`"],
            [VariantProperty("a", "b", "c")],
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")], label="test")],
            [VariantProperty("a", "b", "c")],
            "not a list",
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")], label="test")],
            [VariantProperty("a", "b", "c")],
            ["not a `VariantFeature`"],
        ),
    ],
)
def test_filter_variants_by_property_validation_error(
    vdescs: list[VariantDescription],
    allowed_properties: list[VariantProperty],
    forbidden_properties: list[VariantProperty],
) -> None:
    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=allowed_properties,
                forbidden_properties=forbidden_properties,
            ),
            maxlen=0,
        )


# ====================== `filter_unsupported_feature_values` ====================== #


def test_filter_unsupported_feature_values() -> None:
    vprop11 = VariantProperty("ns1", "f1", "v1")
    vprop12 = VariantProperty("ns1", "f1", "v2")
    vprop21 = VariantProperty("ns1", "f2", "v1")
    vprop22 = VariantProperty("ns1", "f2", "v2")
    vdescs = [
        VariantDescription(label="t1", properties=[vprop11, vprop12, vprop21]),
        VariantDescription(label="t2", properties=[vprop11, vprop21, vprop22]),
        VariantDescription(label="t3", properties=[vprop11, vprop21]),
    ]

    assert list(
        filter_unsupported_feature_values(vdescs, allowed_properties=[vprop11, vprop21])
    ) == [
        VariantDescription(label="t1", properties=[vprop11, vprop21]),
        VariantDescription(label="t2", properties=[vprop11, vprop21]),
        VariantDescription(label="t3", properties=[vprop11, vprop21]),
    ]

    assert list(
        filter_unsupported_feature_values(
            vdescs, allowed_properties=[vprop11, vprop12, vprop21, vprop22]
        )
    ) == [
        VariantDescription(label="t1", properties=[vprop11, vprop12, vprop21]),
        VariantDescription(label="t2", properties=[vprop11, vprop21, vprop22]),
        VariantDescription(label="t3", properties=[vprop11, vprop21]),
    ]

    assert list(
        filter_unsupported_feature_values(
            vdescs, allowed_properties=[vprop11, vprop21, vprop22]
        )
    ) == [
        VariantDescription(label="t1", properties=[vprop11, vprop21]),
        VariantDescription(label="t2", properties=[vprop11, vprop21, vprop22]),
        VariantDescription(label="t3", properties=[vprop11, vprop21]),
    ]

    with pytest.raises(
        ValidationError, match=r"None of `ns1 :: f2` values are allowed"
    ):
        list(
            filter_unsupported_feature_values(
                vdescs, allowed_properties=[vprop11, vprop22]
            )
        )

    with pytest.raises(
        ValidationError, match=r"None of `ns1 :: f1` values are allowed"
    ):
        list(filter_unsupported_feature_values(vdescs, allowed_properties=[vprop22]))

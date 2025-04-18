from __future__ import annotations

import copy
import random
from collections import deque

import pytest

from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.resolver.filtering import filter_variants_by_features
from variantlib.resolver.filtering import filter_variants_by_namespaces
from variantlib.resolver.filtering import filter_variants_by_property
from variantlib.resolver.filtering import remove_duplicates


@pytest.fixture(scope="session")
def vprops() -> list[VariantProperty]:
    return [
        VariantProperty(namespace="OmniCorp", feature="custom_feat", value="value1"),
        VariantProperty(
            namespace="TyrellCorporation", feature="client_id", value="value2"
        ),
    ]


@pytest.fixture(scope="session")
def vdescs(vprops: list[VariantProperty]) -> list[VariantDescription]:
    """Fixture to create a list of VariantDescription objects."""
    assert len(vprops) == 2
    vprop1, vprop2 = vprops

    return [
        VariantDescription([vprop1]),
        VariantDescription([vprop2]),
        VariantDescription([vprop1, vprop2]),
    ]


# =========================== `remove_duplicates` =========================== #


def test_remove_duplicates(vdescs: list[VariantDescription]):
    assert len(vdescs) == 3

    # using `copy.deepcopy` to ensure that all objects are actually unique
    input_vdescs = [copy.deepcopy(random.choice(vdescs)) for _ in range(100)]
    filtered_vdescs = list(remove_duplicates(input_vdescs))

    assert len(filtered_vdescs) == 3

    for vdesc in vdescs:
        assert vdesc in filtered_vdescs


def test_remove_duplicates_empty():
    assert list(remove_duplicates([])) == []


@pytest.mark.parametrize(
    "vdescs",
    ["not a list", ["not a VariantDescription"]],
)
def test_remove_duplicates_validation_error(vdescs: list[VariantDescription]):
    with pytest.raises(ValidationError):
        deque(remove_duplicates(vdescs=vdescs), maxlen=0)


# ===================== `filter_variants_by_namespaces` ===================== #


def test_filter_variants_by_namespaces(vdescs: list[VariantDescription]):
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

    # Only `OmniCorp` forbidden - should return `vdesc2`
    assert list(
        filter_variants_by_namespaces(
            vdescs=vdescs,
            forbidden_namespaces=["OmniCorp"],
        )
    ) == [vdesc2]

    # Only `TyrellCorporation` forbidden - should return `vdesc1`
    assert list(
        filter_variants_by_namespaces(
            vdescs=vdescs,
            forbidden_namespaces=["TyrellCorporation"],
        )
    ) == [vdesc1]

    # Both `OmniCorp` and `TyrellCorporation` forbidden - should return empty
    # Note: Order should not matter
    assert (
        list(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                forbidden_namespaces=["OmniCorp", "TyrellCorporation"],
            )
        )
        == []
    )

    assert (
        list(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                forbidden_namespaces=["TyrellCorporation", "OmniCorp"],
            )
        )
        == []
    )


@pytest.mark.parametrize(
    ("vdescs", "forbidden_namespaces"),
    [
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            "not a list",
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            [VariantProperty("not", "a", "str")],
        ),
        ("not a list", ["OmniCorp"]),
        (["not a `VariantDescription`"], ["OmniCorp"]),
    ],
)
def test_filter_variants_by_namespaces_validation_error(
    vdescs: list[VariantDescription], forbidden_namespaces: list[str]
):
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
):
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
                    VariantFeature(namespace="UmbrellaCorporation", feature="AI")
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
            [VariantDescription([VariantProperty("a", "b", "c")])],
            "not a list",
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            ["not a `VariantFeature`"],
        ),
        ("not a list", VariantFeature("a", "b")),
        (["not a `VariantDescription`"], VariantFeature("a", "b")),
    ],
)
def test_filter_variants_by_features_validation_error(
    vdescs: list[VariantDescription], forbidden_features: list[VariantFeature]
):
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
):
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
                        namespace="UmbrellaCorporation", feature="AI", value="ChatBot"
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
                        namespace="UmbrellaCorporation", feature="AI", value="ChatBot"
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
            [VariantProperty("not", "a", "VariantDescription")],
            [VariantProperty("a", "b", "c")],
            [VariantProperty("a", "b", "c")],
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            "not a list",
            [VariantProperty("a", "b", "c")],
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            ["not a `VariantFeature`"],
            [VariantProperty("a", "b", "c")],
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            [VariantProperty("a", "b", "c")],
            "not a list",
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            [VariantProperty("a", "b", "c")],
            ["not a `VariantFeature`"],
        ),
    ],
)
def test_filter_variants_by_property_validation_error(
    vdescs: list[VariantDescription],
    allowed_properties: list[VariantProperty],
    forbidden_properties: list[VariantProperty],
):
    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=allowed_properties,
                forbidden_properties=forbidden_properties,
            ),
            maxlen=0,
        )

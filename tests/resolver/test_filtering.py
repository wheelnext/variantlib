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
    prop1, prop2 = vprops

    return [
        VariantDescription([prop1]),
        VariantDescription([prop2]),
        VariantDescription([prop1, prop2]),
    ]


# =========================== `remove_duplicates` =========================== #


def test_remove_duplicates(vdescs: list[VariantDescription]):
    # using `copy.deepcopy` to ensure that all objects are actually unique
    input_vdescs = [copy.deepcopy(random.choice(vdescs)) for _ in range(100)]
    filtered_vdescs = list(remove_duplicates(input_vdescs))

    assert len(filtered_vdescs) == 3

    for vdesc in vdescs:
        assert vdesc in filtered_vdescs


def test_remove_duplicates_empty():
    assert list(remove_duplicates([])) == []


def test_remove_duplicates_validation_error():
    with pytest.raises(ValidationError):
        deque(remove_duplicates("not a list"), maxlen=0)  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        deque(remove_duplicates(["not a VariantDescription"]), maxlen=0)  # type: ignore[list-item]


# ===================== `filter_variants_by_namespaces` ===================== #


def test_filter_variants_by_namespaces(vdescs: list[VariantDescription]):
    vdesc1, vdesc2, _ = vdescs

    # No namespace allowed - should return empty list
    assert (
        list(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                allowed_namespaces=[],
            )
        )
        == []
    )

    # Non existing namespace allowed - should return empty list
    assert (
        list(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                allowed_namespaces=["NonExistentNamespace"],
            )
        )
        == []
    )

    # Only `OmniCorp` allowed - should return `vdesc1`
    assert list(
        filter_variants_by_namespaces(
            vdescs=vdescs,
            allowed_namespaces=["OmniCorp"],
        )
    ) == [vdesc1]

    # Only `TyrellCorporation` allowed - should return `vdesc2`
    assert list(
        filter_variants_by_namespaces(
            vdescs=vdescs,
            allowed_namespaces=["TyrellCorporation"],
        )
    ) == [vdesc2]

    # Both `OmniCorp` and `TyrellCorporation` - should return all `vdescs`
    # Note: order should not matter
    assert (
        list(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                allowed_namespaces=["OmniCorp", "TyrellCorporation"],
            )
        )
        == vdescs
    )

    assert (
        list(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                allowed_namespaces=["TyrellCorporation", "OmniCorp"],
            )
        )
        == vdescs
    )


def test_filter_variants_by_namespaces_validation_error(
    vdescs: list[VariantDescription],
):
    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                allowed_namespaces="not a list",  # type: ignore[arg-type]
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_namespaces(
                vdescs=vdescs,
                allowed_namespaces=[1234],  # type: ignore[list-item]
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_namespaces(
                vdescs="not a list",  # type: ignore[arg-type]
                allowed_namespaces=["OmniCorp"],
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_namespaces(
                vdescs=["not a `VariantDescription`"],  # type: ignore[list-item]
                allowed_namespaces=["OmniCorp"],
            ),
            maxlen=0,
        )


# ====================== `filter_variants_by_features` ====================== #


def test_filter_variants_by_features(vdescs: list[VariantDescription]):
    vdesc1, vdesc2, _ = vdescs

    vfeat1 = VariantFeature(namespace="OmniCorp", feature="custom_feat")
    vfeat2 = VariantFeature(namespace="TyrellCorporation", feature="client_id")

    # No feature allowed - should return empty list
    assert (
        list(
            filter_variants_by_features(
                vdescs=vdescs,
                allowed_features=[],
            )
        )
        == []
    )

    # Non existing feature allowed - should return empty list
    assert (
        list(
            filter_variants_by_features(
                vdescs=vdescs,
                allowed_features=[
                    VariantFeature(namespace="UmbrellaCorporation", feature="AI")
                ],
            )
        )
        == []
    )

    # Only `vfeat1` allowed - should return `vdesc1`
    assert list(
        filter_variants_by_features(
            vdescs=vdescs,
            allowed_features=[vfeat1],
        )
    ) == [vdesc1]

    # Only `vfeat2` allowed - should return `vdesc2`
    assert list(
        filter_variants_by_features(
            vdescs=vdescs,
            allowed_features=[vfeat2],
        )
    ) == [vdesc2]

    # Both of vfeats - should return all `vdescs`
    # Note: Order should not matter
    assert (
        list(
            filter_variants_by_features(
                vdescs=vdescs,
                allowed_features=[vfeat1, vfeat2],
            )
        )
        == vdescs
    )

    assert (
        list(
            filter_variants_by_features(
                vdescs=vdescs,
                allowed_features=[vfeat2, vfeat1],
            )
        )
        == vdescs
    )


def test_filter_variants_by_features_validation_error(
    vdescs: list[VariantDescription],
):
    vfeat = VariantFeature(namespace="namespace", feature="feature")

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_features(
                vdescs=vdescs,
                allowed_features="not a list",  # type: ignore[arg-type]
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_features(
                vdescs=vdescs,
                allowed_features=["not a `VariantFeature`"],  # type: ignore[list-item]
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_features(
                vdescs=vdescs,
                allowed_features=[VariantProperty("not", "a", "feature")],  # type: ignore[list-item]
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_features(
                vdescs="not a list",  # type: ignore[arg-type]
                allowed_features=[vfeat],
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_features(
                vdescs=["not a `VariantDescription`"],  # type: ignore[list-item]
                allowed_features=[vfeat],
            ),
            maxlen=0,
        )


# ====================== `filter_variants_by_property` ====================== #


def test_filter_variants_by_property(
    vdescs: list[VariantDescription],
    vprops: list[VariantProperty],
):
    assert len(vprops) == 2
    prop1, prop2 = vprops

    vdesc1, vdesc2, _ = vdescs

    # No property allowed - should return empty list
    assert (
        list(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[],
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
            )
        )
        == []
    )

    # Only `prop1` allowed - should return `vdesc1`
    assert list(
        filter_variants_by_property(
            vdescs=vdescs,
            allowed_properties=[prop1],
        )
    ) == [vdesc1]

    # Only `prop2` allowed - should return `vdesc2`
    assert list(
        filter_variants_by_property(
            vdescs=vdescs,
            allowed_properties=[prop2],
        )
    ) == [vdesc2]

    # Both of vfeats - should return all `vdescs`
    # Note: Order should not matter
    assert (
        list(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[prop1, prop2],
            )
        )
        == vdescs
    )

    assert (
        list(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[prop2, prop1],
            )
        )
        == vdescs
    )


def test_filter_variants_by_property_validation_error(
    vdescs: list[VariantDescription],
):
    vprop = VariantProperty(namespace="namespace", feature="feature", value="value")

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties="not a list",  # type: ignore[arg-type]
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=["not a `VariantProperty`"],  # type: ignore[list-item]
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_property(
                vdescs=vdescs,
                allowed_properties=[VariantFeature("not_a", "property")],  # type: ignore[list-item]
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_property(
                vdescs="not a list",  # type: ignore[arg-type]
                allowed_properties=[vprop],
            ),
            maxlen=0,
        )

    with pytest.raises(ValidationError):
        deque(
            filter_variants_by_property(
                vdescs=["not a `VariantDescription`"],  # type: ignore[list-item]
                allowed_properties=[vprop],
            ),
            maxlen=0,
        )

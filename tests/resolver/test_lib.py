from __future__ import annotations

import pytest

from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.resolver.filtering import filter_variants_by_features
from variantlib.resolver.filtering import filter_variants_by_namespaces
from variantlib.resolver.filtering import remove_duplicates
from variantlib.resolver.lib import filter_variants
from variantlib.resolver.lib import sort_and_filter_supported_variants


@pytest.fixture(scope="session")
def vprops() -> list[VariantProperty]:
    """Fixture to create a list of VariantProperty objects."""

    return [
        VariantProperty(namespace="OmniCorp", feature="access_key", value="value1"),
        VariantProperty(
            namespace="TyrellCorporation", feature="client_id", value="value2"
        ),
        VariantProperty(
            namespace="TyrellCorporation", feature="client_pass", value="abcde"
        ),
        VariantProperty(
            namespace="TyrellCorporation", feature="client_pass", value="efghij"
        ),
    ]


@pytest.fixture(scope="session")
def vdescs(vprops: list[VariantProperty]) -> list[VariantDescription]:
    """Fixture to create a list of VariantDescription objects."""

    assert len(vprops) == 4
    prop1, prop2, prop3, prop4 = vprops

    return [
        # prop3 and prop4 are mutually exclusive
        VariantDescription([prop1, prop2, prop3]),
        VariantDescription([prop1, prop3, prop2]),
        VariantDescription([prop2, prop3, prop1]),
        VariantDescription([prop2, prop1, prop3]),
        VariantDescription([prop3, prop2, prop1]),
        VariantDescription([prop3, prop1, prop2]),
        VariantDescription([prop1, prop2, prop4]),  # duplicate with prop4
        VariantDescription([prop1, prop4, prop2]),  # duplicate with prop4
        VariantDescription([prop2, prop4, prop1]),  # duplicate with prop4
        VariantDescription([prop2, prop1, prop4]),  # duplicate with prop4
        VariantDescription([prop4, prop2, prop1]),  # duplicate with prop4
        VariantDescription([prop4, prop1, prop2]),  # duplicate with prop4
        VariantDescription([prop1, prop2]),
        VariantDescription([prop2, prop1]),
        VariantDescription([prop1, prop3]),
        VariantDescription([prop3, prop1]),
        VariantDescription([prop2, prop3]),
        VariantDescription([prop3, prop2]),
        VariantDescription([prop1, prop4]),  # duplicate with prop4
        VariantDescription([prop4, prop1]),  # duplicate with prop4
        VariantDescription([prop2, prop4]),  # duplicate with prop4
        VariantDescription([prop4, prop2]),  # duplicate with prop4
        VariantDescription([prop1]),
        VariantDescription([prop2]),
        VariantDescription([prop3]),
        VariantDescription([prop4]),
    ]


# =========================== `filter_variants` =========================== #


def test_filter_variants(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 4
    _, _, prop3, _ = vprops

    expected_vdescs = [
        # VariantDescription([prop1, prop2, prop3]),  # not allowed `namespace`
        # VariantDescription([prop1, prop3, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop3, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop1, prop3]),  # duplicate - order doesn't matter
        # VariantDescription([prop3, prop2, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop3, prop1, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop1, prop2, prop4]),  # not allowed property
        # VariantDescription([prop1, prop4, prop2]),  # not allowed property
        # VariantDescription([prop2, prop4, prop1]),  # not allowed property
        # VariantDescription([prop2, prop1, prop4]),  # not allowed property
        # VariantDescription([prop4, prop2, prop1]),  # not allowed property
        # VariantDescription([prop4, prop1, prop2]),  # not allowed property
        # VariantDescription([prop1, prop2]),  # not allowed `namespace`
        # VariantDescription([prop2, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop1, prop3]),  # not allowed `namespace`
        # VariantDescription([prop3, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop3]),  # not allowed `feature`
        # VariantDescription([prop3, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop1, prop4]),  # not allowed property
        # VariantDescription([prop4, prop1]),  # not allowed property
        # VariantDescription([prop2, prop4]),  # not allowed property
        # VariantDescription([prop4, prop2]),  # not allowed property
        # VariantDescription([prop1]),  # not allowed `namespace`
        # VariantDescription([prop2]),  # not allowed `feature`
        VariantDescription([prop3]),  # ================= > the only valid variant
        # VariantDescription([prop3]),  # not allowed property
    ]

    assert (
        list(
            filter_variants(
                vdescs=vdescs,
                allowed_namespaces=["TyrellCorporation"],
                allowed_features=[
                    VariantFeature(namespace="TyrellCorporation", feature="client_pass")
                ],
                allowed_properties=[prop3],
            )
        )
        == expected_vdescs
    )


def test_filter_variants_only_remove_duplicates(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 4
    prop1, prop2, prop3, prop4 = vprops

    expected_vdescs = [
        VariantDescription([prop1, prop2, prop3]),
        # VariantDescription([prop1, prop3, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop3, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop1, prop3]),  # duplicate - order doesn't matter
        # VariantDescription([prop3, prop2, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop3, prop1, prop2]),  # duplicate - order doesn't matter
        VariantDescription([prop1, prop2, prop4]),  # duplicate with prop4
        # VariantDescription([prop1, prop4, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop4, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop1, prop4]),  # duplicate - order doesn't matter
        # VariantDescription([prop4, prop2, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop4, prop1, prop2]),  # duplicate - order doesn't matter
        VariantDescription([prop1, prop2]),
        # VariantDescription([prop2, prop1]),  # duplicate - order doesn't matter
        VariantDescription([prop1, prop3]),
        # VariantDescription([prop3, prop1]),  # duplicate - order doesn't matter
        VariantDescription([prop2, prop3]),
        # VariantDescription([prop3, prop2]),  # duplicate - order doesn't matter
        VariantDescription([prop1, prop4]),
        # VariantDescription([prop4, prop1]),  # duplicate - order doesn't matter
        VariantDescription([prop2, prop4]),
        # VariantDescription([prop4, prop2]),  # duplicate - order doesn't matter
        VariantDescription([prop1]),
        VariantDescription([prop2]),
        VariantDescription([prop3]),
        VariantDescription([prop4]),
    ]

    assert (
        list(
            filter_variants(
                vdescs=vdescs,
            )
        )
        == expected_vdescs
    )

    assert list(remove_duplicates(vdescs=vdescs)) == expected_vdescs


def test_filter_variants_remove_duplicates_and_namespaces(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 4
    _, prop2, prop3, prop4 = vprops

    expected_vdescs = [
        # VariantDescription([prop1, prop2, prop3]),  # not allowed `namespace`
        # VariantDescription([prop1, prop3, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop3, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop1, prop3]),  # duplicate - order doesn't matter
        # VariantDescription([prop3, prop2, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop3, prop1, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop1, prop2, prop4]),  # not allowed `namespace`
        # VariantDescription([prop1, prop4, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop4, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop1, prop4]),  # duplicate - order doesn't matter
        # VariantDescription([prop4, prop2, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop4, prop1, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop1, prop2]),  # not allowed `namespace`
        # VariantDescription([prop2, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop1, prop3]),  # not allowed `namespace`
        # VariantDescription([prop3, prop1]),  # duplicate - order doesn't matter
        VariantDescription([prop2, prop3]),
        # VariantDescription([prop3, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop1, prop4]),  # not allowed `namespace`
        # VariantDescription([prop4, prop1]),  # duplicate - order doesn't matter
        VariantDescription([prop2, prop4]),
        # VariantDescription([prop4, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop1]),  # not allowed `namespace`
        VariantDescription([prop2]),
        VariantDescription([prop3]),
        VariantDescription([prop4]),
    ]

    allowed_namespaces = ["TyrellCorporation"]

    assert (
        list(
            filter_variants(
                vdescs=vdescs,
                allowed_namespaces=allowed_namespaces,
            )
        )
        == expected_vdescs
    )

    assert (
        list(
            filter_variants_by_namespaces(
                remove_duplicates(vdescs=vdescs),
                allowed_namespaces=allowed_namespaces,
            )
        )
        == expected_vdescs
    )


def test_filter_variants_remove_duplicates_and_features(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 4
    prop1, prop2, _, _ = vprops

    expected_vdescs = [
        # VariantDescription([prop1, prop2, prop3]),  # not allowed `feature`
        # VariantDescription([prop1, prop3, prop2]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop3, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop1, prop3]),  # duplicate - order doesn't matter
        # VariantDescription([prop3, prop2, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop3, prop1, prop2]),  # duplicate - order doesn't matter
        VariantDescription([prop1, prop2]),
        # VariantDescription([prop2, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop1, prop3]),    # not allowed `feature`
        # VariantDescription([prop3, prop1]),  # duplicate - order doesn't matter
        # VariantDescription([prop2, prop3]),  # not allowed `feature`
        # VariantDescription([prop3, prop2]),  # duplicate - order doesn't matter
        VariantDescription([prop1]),
        VariantDescription([prop2]),
        # VariantDescription([prop3]),  # not allowed `feature`
    ]

    allowed_features = [
        VariantFeature(namespace="OmniCorp", feature="access_key"),
        VariantFeature(namespace="TyrellCorporation", feature="client_id"),
    ]

    assert (
        list(
            filter_variants(
                vdescs=vdescs,
                allowed_features=allowed_features,
            )
        )
        == expected_vdescs
    )

    assert (
        list(
            filter_variants_by_features(
                remove_duplicates(vdescs=vdescs),
                allowed_features=allowed_features,
            )
        )
        == expected_vdescs
    )


# =================== `sort_and_filter_supported_variants` ================== #


def test_sort_and_filter_supported_variants(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    # vprops = [
    #     VariantProperty(namespace="OmniCorp", feature="access_key", value="value1"),
    #     VariantProperty(
    #         namespace="TyrellCorporation", feature="client_id", value="value2"
    #     ),
    #     VariantProperty(
    #         namespace="TyrellCorporation", feature="client_pass", value="abcde"
    #     ),
    #     VariantProperty(
    #         namespace="TyrellCorporation", feature="client_pass", value="efghij"
    #     ),
    # ]

    # vdescs = [
    #     # prop3 and prop4 are mutually exclusive
    #     [00] VariantDescription([prop1, prop2, prop3]),  # Rank 0
    #     [01] VariantDescription([prop1, prop3, prop2]),  # duplicate
    #     [02] VariantDescription([prop2, prop3, prop1]),  # duplicate
    #     [03] VariantDescription([prop2, prop1, prop3]),  # duplicate
    #     [04] VariantDescription([prop3, prop2, prop1]),  # duplicate
    #     [05] VariantDescription([prop3, prop1, prop2]),  # duplicate
    #     [06] VariantDescription([prop1, prop2, prop4]),  # rank 2
    #     [07] VariantDescription([prop1, prop4, prop2]),  # duplicate
    #     [08] VariantDescription([prop2, prop4, prop1]),  # duplicate
    #     [09] VariantDescription([prop2, prop1, prop4]),  # duplicate
    #     [10] VariantDescription([prop4, prop2, prop1]),  # duplicate
    #     [11] VariantDescription([prop4, prop1, prop2]),  # duplicate
    #     [12] VariantDescription([prop1, prop2]),         # Rank 4
    #     [13] VariantDescription([prop2, prop1]),         # duplicate
    #     [14] VariantDescription([prop1, prop3]),         # Rank 6
    #     [15] VariantDescription([prop3, prop1]),         # duplicate
    #     [16] VariantDescription([prop2, prop3]),         # Rank 1
    #     [17] VariantDescription([prop3, prop2]),         # duplicate
    #     [18] VariantDescription([prop1, prop4]),         # Rank 8
    #     [19] VariantDescription([prop4, prop1]),         # duplicate
    #     [20] VariantDescription([prop2, prop4]),         # Rank 3
    #     [21] VariantDescription([prop4, prop2]),         # duplicate
    #     [22] VariantDescription([prop1]),                # Rank 10
    #     [23] VariantDescription([prop2]),                # Rank 5
    #     [24] VariantDescription([prop3]),                # Rank 7
    #     [25] VariantDescription([prop4]),                # Rank 9
    # ]
    vprop1 = VariantProperty(
        namespace="TyrellCorporation", feature="client_id", value="value2"
    )
    vfeat1 = VariantFeature(namespace="TyrellCorporation", feature="client_pass")

    assert sort_and_filter_supported_variants(
        vdescs=vdescs,
        supported_vprops=vprops,
        property_priorities=[vprop1],
        feature_priorities=[vfeat1],
        namespace_priorities=["OmniCorp", "TyrellCorporation"],
    ) == [
        # everything that contains `vprop2` with vfeat1 important and OmniCorp first
        vdescs[0],  # 0
        vdescs[16],  # 1
        vdescs[6],  # 2
        vdescs[20],  # 3
        vdescs[12],  # 4
        vdescs[23],  # 5
        # everything that contains `vfeat1`
        vdescs[14],  # 6
        vdescs[24],  # 7
        vdescs[18],  # 8
        vdescs[25],  # 9
        # lastly prop1 alone - ranked by namespace alone
        vdescs[22],  # 10
    ]


def test_sort_and_filter_supported_variants_validation_errors(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    with pytest.raises(ValidationError):
        sort_and_filter_supported_variants(
            vdescs="not a list",  # type: ignore [arg-type]
            supported_vprops=vprops,
        )

    with pytest.raises(ValidationError):
        sort_and_filter_supported_variants(
            vdescs=["not a VariantDescription"],  # type: ignore [list-item]
            supported_vprops=vprops,
        )

    with pytest.raises(ValidationError):
        sort_and_filter_supported_variants(
            vdescs=vdescs,
            supported_vprops="not a list",  # type: ignore [arg-type]
        )

    with pytest.raises(ValidationError):
        sort_and_filter_supported_variants(
            vdescs=vdescs,
            supported_vprops=["not a VariantProperty"],  # type: ignore [list-item]
        )

    # This one specifies no ordering/priority => can't sort
    with pytest.raises(ValidationError, match="has no priority"):
        sort_and_filter_supported_variants(
            vdescs=vdescs,
            supported_vprops=vprops,
        )

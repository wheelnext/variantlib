from __future__ import annotations

import contextlib
import random
from functools import cached_property

import pytest
from deepdiff import DeepDiff
from deepdiff.operator import BaseOperator

from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.resolver.filtering import filter_variants_by_features
from variantlib.resolver.filtering import filter_variants_by_namespaces
from variantlib.resolver.filtering import filter_variants_by_property
from variantlib.resolver.filtering import remove_duplicates
from variantlib.resolver.lib import filter_variants
from variantlib.resolver.lib import sort_and_filter_supported_variants


def deep_diff(
    a: list[VariantDescription], b: list[VariantDescription], ignore_ordering=False
) -> DeepDiff:
    """Helper function to compare two objects using DeepDiff."""
    assert isinstance(a, list)
    assert isinstance(b, list)
    assert all(isinstance(vdesc, VariantDescription) for vdesc in a)
    assert all(isinstance(vdesc, VariantDescription) for vdesc in b)

    class HexDigestOperator(BaseOperator):
        def normalize_value_for_hashing(self, parent, obj: VariantDescription) -> str:
            """Required for ignore_order=True compatibility"""
            if isinstance(obj, VariantDescription):
                return obj.hexdigest

            return obj

    return DeepDiff(
        a,
        b,
        ignore_order=ignore_ordering,
        custom_operators=[HexDigestOperator()],
        exclude_types=[property, cached_property],
        exclude_regex_paths=[
            r"root\[\d+\].properties\[\d+\].feature_hash",
            r"root\[\d+\].properties\[\d+\].property_hash",
            r"root\[\d+\].properties\[\d+\].feature_object",
        ],
    )


def shuffle_vdescs_with_duplicates(
    vdescs: list[VariantDescription],
) -> list[VariantDescription]:
    inputs_vdescs = [vdesc for vdesc in vdescs for _ in range(5)]
    assert len(inputs_vdescs) == len(vdescs) * 5
    random.shuffle(inputs_vdescs)
    return inputs_vdescs


@pytest.fixture(scope="session")
def vprops() -> list[VariantProperty]:
    """Fixture to create a list of VariantProperty objects."""
    # This list assume sorting by feature and properties coming from the plugins
    # Does not assume filtering per namespace. Only features & properties.

    return [
        # -------------------------- Plugin `OmniCorp` -------------------------- #
        # Feature 1: `OmniCorp :: featA`
        VariantProperty(namespace="OmniCorp", feature="featA", value="value"),
        # Feature 2: `OmniCorp :: featB`
        VariantProperty(namespace="OmniCorp", feature="featB", value="value"),
        # ------------------------- Plugin `TyrellCorp` ------------------------- #
        # Feature 1: `TyrellCorp :: featA`
        VariantProperty(namespace="TyrellCorp", feature="featA", value="value"),
        # Feature 2: `TyrellCorp :: featB`
        # Property 2.1: `TyrellCorp :: featB :: abcde`
        VariantProperty(namespace="TyrellCorp", feature="featB", value="abcde"),
        # Property 2.2: `TyrellCorp :: featB :: efghij`
        VariantProperty(namespace="TyrellCorp", feature="featB", value="efghij"),
        # Feature 3: `TyrellCorp :: featC`
        VariantProperty(namespace="TyrellCorp", feature="featC", value="value"),
    ]


@pytest.fixture(scope="session")
def vdescs(vprops: list[VariantProperty]) -> list[VariantDescription]:
    """Fixture to create a list of VariantDescription objects."""

    assert len(vprops) == 6
    vprop1, vprop2, vprop3, vprop4, vprop5, vprop6 = vprops

    # fmt: off
    # Important: vprop4 and vprop5 are mutually exclusive
    return [
        # variants with 5 properties
        VariantDescription([vprop1, vprop2, vprop3, vprop4, vprop6]),
        VariantDescription([vprop1, vprop2, vprop3, vprop5, vprop6]),

        # variants with 4 properties
        VariantDescription([vprop1, vprop2, vprop3, vprop4]),  # - vprop6
        VariantDescription([vprop1, vprop2, vprop3, vprop5]),  # - vprop6

        VariantDescription([vprop1, vprop2, vprop3, vprop6]),  # - vprop4/5

        VariantDescription([vprop1, vprop2, vprop4, vprop6]),  # - vprop3
        VariantDescription([vprop1, vprop2, vprop5, vprop6]),  # - vprop3

        VariantDescription([vprop1, vprop3, vprop4, vprop6]),  # - vprop2
        VariantDescription([vprop1, vprop3, vprop5, vprop6]),  # - vprop2

        VariantDescription([vprop2, vprop3, vprop5, vprop6]),  # - vprop1
        VariantDescription([vprop2, vprop3, vprop5, vprop6]),  # - vprop1

        # variants with 3 properties
        # --- vprop1 --- #
        VariantDescription([vprop1, vprop2, vprop3]),
        VariantDescription([vprop1, vprop2, vprop4]),
        VariantDescription([vprop1, vprop2, vprop5]),
        VariantDescription([vprop1, vprop2, vprop6]),

        VariantDescription([vprop1, vprop3, vprop4]),
        VariantDescription([vprop1, vprop3, vprop5]),
        VariantDescription([vprop1, vprop3, vprop6]),

        VariantDescription([vprop1, vprop4, vprop6]),
        VariantDescription([vprop1, vprop5, vprop6]),

        # --- vprop2 --- #
        VariantDescription([vprop2, vprop3, vprop4]),
        VariantDescription([vprop2, vprop3, vprop5]),
        VariantDescription([vprop2, vprop3, vprop6]),

        VariantDescription([vprop2, vprop4, vprop6]),
        VariantDescription([vprop2, vprop5, vprop6]),

        # --- vprop3 --- #
        VariantDescription([vprop3, vprop4, vprop6]),
        VariantDescription([vprop3, vprop5, vprop6]),

        # variants with 2 properties
        # --- vprop1 --- #
        VariantDescription([vprop1, vprop2]),
        VariantDescription([vprop1, vprop3]),
        VariantDescription([vprop1, vprop4]),
        VariantDescription([vprop1, vprop5]),
        VariantDescription([vprop1, vprop6]),

        # --- vprop2 --- #
        VariantDescription([vprop2, vprop3]),
        VariantDescription([vprop2, vprop4]),
        VariantDescription([vprop2, vprop5]),
        VariantDescription([vprop2, vprop6]),

        # --- vprop3 --- #
        VariantDescription([vprop3, vprop4]),
        VariantDescription([vprop3, vprop5]),
        VariantDescription([vprop3, vprop6]),

        # --- vprop4 --- #
        VariantDescription([vprop4, vprop6]),

        # --- vprop5 --- #
        VariantDescription([vprop5, vprop6]),

        # variants with 1 property
        VariantDescription([vprop1]),
        VariantDescription([vprop2]),
        VariantDescription([vprop3]),
        VariantDescription([vprop4]),
        VariantDescription([vprop5]),
        VariantDescription([vprop6]),
    ]
    # fmt: on


# =========================== `filter_variants` =========================== #


def test_filter_variants_only_one_prop_allowed(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 6
    _, _, _, vprop4, _, _ = vprops

    inputs_vdescs = shuffle_vdescs_with_duplicates(vdescs=vdescs)

    assert (
        list(
            filter_variants(
                vdescs=inputs_vdescs,
                allowed_properties=[],
            )
        )
        == []
    )

    assert list(
        filter_variants(
            vdescs=inputs_vdescs,
            allowed_properties=[vprop4],
        )
    ) == [VariantDescription([vprop4])]

    assert (
        list(
            filter_variants(
                vdescs=inputs_vdescs,
                allowed_properties=[vprop4],
                forbidden_namespaces=[vprop4.namespace],
            )
        )
        == []
    )

    assert (
        list(
            filter_variants(
                vdescs=inputs_vdescs,
                allowed_properties=[vprop4],
                forbidden_features=[vprop4.feature_object],
            )
        )
        == []
    )

    assert (
        list(
            filter_variants(
                vdescs=inputs_vdescs,
                allowed_properties=[vprop4],
                forbidden_properties=[vprop4],
            )
        )
        == []
    )


def test_filter_variants_forbidden_feature_allowed_prop(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 6
    _, vprop2, _, vprop4, _, _ = vprops

    inputs_vdescs = shuffle_vdescs_with_duplicates(vdescs=vdescs)

    assert list(
        filter_variants(
            vdescs=inputs_vdescs,
            allowed_properties=[vprop4],
            forbidden_features=[vprop2.feature_object],
        )
    ) == [VariantDescription([vprop4])]


def test_filter_variants_forbidden_namespace_allowed_prop(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 6
    vprop1, _, _, vprop4, _, _ = vprops

    inputs_vdescs = shuffle_vdescs_with_duplicates(vdescs=vdescs)

    assert list(
        filter_variants(
            vdescs=inputs_vdescs,
            allowed_properties=[vprop4],
            forbidden_namespaces=["NotExisting"],
        )
    ) == [VariantDescription([vprop4])]

    assert list(
        filter_variants(
            vdescs=inputs_vdescs,
            allowed_properties=[vprop4],
            forbidden_namespaces=[vprop1.namespace],
        )
    ) == [VariantDescription([vprop4])]


def test_filter_variants_only_remove_duplicates(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 6

    inputs_vdescs = shuffle_vdescs_with_duplicates(vdescs=vdescs)

    ddiff = deep_diff(
        list(filter_variants(vdescs=inputs_vdescs, allowed_properties=vprops)),
        vdescs,
        ignore_ordering=True,
    )
    assert ddiff == {}, ddiff

    ddiff = deep_diff(
        list(remove_duplicates(vdescs=inputs_vdescs)), vdescs, ignore_ordering=True
    )
    assert ddiff == {}, ddiff


def test_filter_variants_remove_duplicates_and_namespaces(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 6
    _, _, vprop3, vprop4, vprop5, vprop6 = vprops

    inputs_vdescs = shuffle_vdescs_with_duplicates(vdescs=vdescs)

    expected_vdescs = [
        # --- vprop3 --- #
        VariantDescription([vprop3, vprop4, vprop6]),
        VariantDescription([vprop3, vprop5, vprop6]),
        # variants with 2 properties
        # --- vprop3 --- #
        VariantDescription([vprop3, vprop4]),
        VariantDescription([vprop3, vprop5]),
        VariantDescription([vprop3, vprop6]),
        # --- vprop4 --- #
        VariantDescription([vprop4, vprop6]),
        # --- vprop5 --- #
        VariantDescription([vprop5, vprop6]),
        # variants with 1 property
        VariantDescription([vprop3]),
        VariantDescription([vprop4]),
        VariantDescription([vprop5]),
        VariantDescription([vprop6]),
    ]

    ddiff = deep_diff(
        list(
            filter_variants(
                vdescs=inputs_vdescs,
                allowed_properties=vprops,
                forbidden_namespaces=["OmniCorp"],
            )
        ),
        expected_vdescs,
        ignore_ordering=True,
    )
    assert ddiff == {}, ddiff

    ddiff = deep_diff(
        list(
            filter_variants_by_namespaces(
                remove_duplicates(vdescs=inputs_vdescs),
                forbidden_namespaces=["OmniCorp"],
            )
        ),
        expected_vdescs,
        ignore_ordering=True,
    )
    assert ddiff == {}, ddiff


def test_filter_variants_remove_duplicates_and_features(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 6
    vprop1, vprop2, vprop3, vprop4, vprop5, vprop6 = vprops

    inputs_vdescs = shuffle_vdescs_with_duplicates(vdescs=vdescs)

    expected_vdescs = [
        # variants with 2 properties
        # --- vprop1 --- #
        VariantDescription([vprop1, vprop4]),
        VariantDescription([vprop1, vprop5]),
        # variants with 1 property
        VariantDescription([vprop1]),
        VariantDescription([vprop4]),
        VariantDescription([vprop5]),
    ]

    forbidden_features = [
        vprop2.feature_object,
        vprop3.feature_object,
        vprop6.feature_object,
    ]

    ddiff = deep_diff(
        list(
            filter_variants(
                vdescs=inputs_vdescs,
                allowed_properties=vprops,
                forbidden_features=forbidden_features,
            )
        ),
        expected_vdescs,
        ignore_ordering=True,
    )
    assert ddiff == {}, ddiff

    ddiff = deep_diff(
        list(
            filter_variants_by_features(
                remove_duplicates(vdescs=inputs_vdescs),
                forbidden_features=forbidden_features,
            )
        ),
        expected_vdescs,
        ignore_ordering=True,
    )
    assert ddiff == {}, ddiff


def test_filter_variants_remove_duplicates_and_properties(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 6
    vprop1, vprop2, _, vprop4, vprop5, _ = vprops

    inputs_vdescs = shuffle_vdescs_with_duplicates(vdescs=vdescs)

    expected_vdescs = [
        # variants with 2 properties
        # --- vprop1 --- #
        VariantDescription([vprop1, vprop4]),
        VariantDescription([vprop1, vprop5]),
        # variants with 1 property
        VariantDescription([vprop1]),
        VariantDescription([vprop4]),
        VariantDescription([vprop5]),
    ]

    allowed_properties = [vprop1, vprop2, vprop4, vprop5]

    ddiff = deep_diff(
        list(
            filter_variants(
                vdescs=inputs_vdescs,
                allowed_properties=allowed_properties,
                forbidden_properties=[vprop2],
            )
        ),
        expected_vdescs,
        ignore_ordering=True,
    )
    assert ddiff == {}, ddiff

    ddiff = deep_diff(
        list(
            filter_variants_by_property(
                remove_duplicates(vdescs=inputs_vdescs),
                allowed_properties=allowed_properties,
                forbidden_properties=[vprop2],
            )
        ),
        expected_vdescs,
        ignore_ordering=True,
    )
    assert ddiff == {}, ddiff


# =================== `sort_and_filter_supported_variants` ================== #


def test_sort_and_filter_supported_variants(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    assert len(vprops) == 6

    # Let's remove vprop2 [not supported]
    vprop1, _, vprop3, vprop4, vprop5, vprop6 = vprops

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ SORTING PARAMETERS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

    # Top Priority: Anything that contains `vprop3`
    prio_vprops: list[VariantProperty] = [vprop3]

    # Second Priority: Vprop4 and Vprop5 are prioritized priority (same feature)
    #                  With vprop4 > vprop5 given that vprop4 is first in the list
    prio_vfeats: list[VariantFeature] = [vprop4.feature_object]

    # Third Priority: namespaces
    #                 vprop3, vprop4, vprop5, vprop6 [TyrellCorp] > vprop1, vprop2 ["OmniCorp"]  # noqa: E501
    prio_namespaces = ["NotExistingNamespace", "TyrellCorp", "OmniCorp"]

    # Default Ordering: properties are assumed pre-sorted in features/properties
    #                   vprop1 > vprop2 > vprop3 > vprop4 > vprop5 > vprop6
    #                   Note: Namespace is already accounted for in 3)

    # Last Preferential Order: More features are preferred over less features

    # ----------------------------------------------------------------------------- #

    # fmt: off
    expected_vdescs = [
        # ============ A - Everything with vprop3 ============ #
        # ============ A.1 - Everything with vprop3 & vprop4 ============ #
        VariantDescription([vprop1, vprop3, vprop4, vprop6]),
        VariantDescription([vprop3, vprop4, vprop6]),  # TyrellCorp > OmniCorp
        VariantDescription([vprop1, vprop3, vprop4]),  # TyrellCorp > OmniCorp
        VariantDescription([vprop3, vprop4]),
        # ============ A.2 - Everything with vprop3 & vprop5 ============ #
        VariantDescription([vprop1, vprop3, vprop5, vprop6]),
        VariantDescription([vprop3, vprop5, vprop6]),  # TyrellCorp > OmniCorp
        VariantDescription([vprop1, vprop3, vprop5]),  # TyrellCorp > OmniCorp
        VariantDescription([vprop3, vprop5]),
        # =========== A.4 - Everything with vprop3 & without vprop5/vprop6 =========== #
        VariantDescription([vprop1, vprop3, vprop6]),
        VariantDescription([vprop3, vprop6]),  # TyrellCorp > OmniCorp
        VariantDescription([vprop1, vprop3]),  # TyrellCorp > OmniCorp
        # =========== A.5 - vprop3 alone =========== #
        VariantDescription([vprop3]),

        # ============ B - Everything without vprop3 ============ #
        # ============ B.1 - Everything without vprop3 & with vprop4 ============ #
        VariantDescription([vprop1, vprop4, vprop6]),
        VariantDescription([vprop4, vprop6]),  # TyrellCorp > OmniCorp
        VariantDescription([vprop1, vprop4]),  # TyrellCorp > OmniCorp
        VariantDescription([vprop4]),

        # ============ B.2 - Everything without vprop3 & with vprop5 ============ #
        VariantDescription([vprop1, vprop5, vprop6]),
        VariantDescription([vprop5, vprop6]),  # TyrellCorp > OmniCorp
        VariantDescription([vprop1, vprop5]),  # TyrellCorp > OmniCorp
        VariantDescription([vprop5]),

        # == C - Everything without vprop3/vprop4/vprop5 and TyrellCorp > OmniCorp == #
        VariantDescription([vprop1, vprop6]),
        VariantDescription([vprop6]),
        VariantDescription([vprop1]),
    ]
    # fmt: on

    inputs_vdescs = shuffle_vdescs_with_duplicates(vdescs=vdescs)

    ddiff = deep_diff(
        sort_and_filter_supported_variants(
            vdescs=inputs_vdescs,
            supported_vprops=[vprop1, vprop3, vprop4, vprop5, vprop6],
            property_priorities=prio_vprops,
            feature_priorities=prio_vfeats,
            namespace_priorities=prio_namespaces,
        ),
        expected_vdescs,
    )
    assert ddiff == {}, ddiff


# # =================== `Validation Testing` ================== #


@pytest.mark.parametrize(
    ("vdescs", "vprops"),
    [
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            "not a list",
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            [VariantFeature("not_a", "VariantProperty")],
        ),
        ("not a list", VariantProperty("a", "b", "c")),
        (["not a `VariantDescription`"], VariantProperty("a", "b", "c")),
    ],
)
def test_sort_and_filter_supported_variants_validation_errors(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    feature_priorities = []
    with contextlib.suppress(TypeError, AttributeError):
        feature_priorities = list({vprop.feature_object for vprop in vprops})

    with pytest.raises(ValidationError):
        sort_and_filter_supported_variants(
            vdescs=vdescs,
            supported_vprops=vprops,
            feature_priorities=feature_priorities,
        )


def test_sort_and_filter_supported_variants_validation_errors_with_no_priority(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
):
    # This one specifies no ordering/priority => can't sort
    with pytest.raises(ValidationError, match="has no priority"):
        sort_and_filter_supported_variants(
            vdescs=vdescs,
            supported_vprops=vprops,
        )

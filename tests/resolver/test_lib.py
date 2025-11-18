from __future__ import annotations

import random
from functools import cached_property
from typing import Any

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
from variantlib.resolver.sorting import sort_variant_properties


def deep_diff(
    a: list[VariantDescription],
    b: list[VariantDescription],
    ignore_ordering: bool = False,
) -> DeepDiff:
    """Helper function to compare two objects using DeepDiff."""
    assert isinstance(a, list)
    assert isinstance(b, list)
    assert all(isinstance(vdesc, VariantDescription) for vdesc in a)
    assert all(isinstance(vdesc, VariantDescription) for vdesc in b)

    class HexDigestOperator(BaseOperator):
        def normalize_value_for_hashing(
            self, parent: Any, obj: VariantDescription
        ) -> str:
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
        # -------------------------- Plugin `omnicorp` -------------------------- #
        # 1. Feature 1: `omnicorp :: feat_a`
        VariantProperty(namespace="omnicorp", feature="feat_a", value="value"),
        # 2. Feature 2: `omnicorp :: feat_b`
        VariantProperty(namespace="omnicorp", feature="feat_b", value="value"),
        # ------------------------- Plugin `tyrell_corp` ------------------------- #
        # 3. Feature 1: `tyrell_corp :: feat_a`
        VariantProperty(namespace="tyrell_corp", feature="feat_a", value="value"),
        # Feature 2: `tyrell_corp :: feat_b`
        # 4. Property 2.1: `tyrell_corp :: feat_b :: abcde`
        VariantProperty(namespace="tyrell_corp", feature="feat_b", value="abcde"),
        # 5. Property 2.2: `tyrell_corp :: feat_b :: efghij`
        VariantProperty(namespace="tyrell_corp", feature="feat_b", value="efghij"),
        # 6. Feature 3: `tyrell_corp :: feat_c`
        VariantProperty(namespace="tyrell_corp", feature="feat_c", value="value"),
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
) -> None:
    assert len(vprops) == 6
    _, _, _, vprop4, _, _ = vprops

    # Shuffling the list & creating duplicates
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
) -> None:
    assert len(vprops) == 6
    _, vprop2, _, vprop4, _, _ = vprops

    # Shuffling the list & creating duplicates
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
) -> None:
    assert len(vprops) == 6
    vprop1, _, _, vprop4, _, _ = vprops

    # Shuffling the list & creating duplicates
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
) -> None:
    assert len(vprops) == 6

    # Shuffling the list & creating duplicates
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
) -> None:
    assert len(vprops) == 6
    _, _, vprop3, vprop4, vprop5, vprop6 = vprops

    # Adding the `null-Variant` and shuffling the list & creating duplicates
    vdescs = [*vdescs, VariantDescription()]
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
        # Null-Variant is never removed and last
        VariantDescription(),
    ]

    ddiff = deep_diff(
        list(
            filter_variants(
                vdescs=inputs_vdescs,
                allowed_properties=vprops,
                forbidden_namespaces=["omnicorp"],
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
                forbidden_namespaces=["omnicorp"],
            )
        ),
        expected_vdescs,
        ignore_ordering=True,
    )
    assert ddiff == {}, ddiff


def test_filter_variants_remove_duplicates_and_features(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
) -> None:
    assert len(vprops) == 6
    vprop1, vprop2, vprop3, vprop4, vprop5, vprop6 = vprops

    # Adding the `null-Variant` and shuffling the list & creating duplicates
    vdescs = [*vdescs, VariantDescription()]
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
        # Null-Variant is never removed and last
        VariantDescription(),
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
) -> None:
    assert len(vprops) == 6
    vprop1, vprop2, _, vprop4, vprop5, _ = vprops

    # Adding the `null-Variant` and shuffling the list & creating duplicates
    vdescs = [*vdescs, VariantDescription()]
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
        # Null-Variant is never removed and last
        VariantDescription(),
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
) -> None:
    assert len(vprops) == 6

    vprop1, vprop2, vprop3, vprop4, vprop5, vprop6 = vprops

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ SORTING PARAMETERS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

    prio_vprops = {"tyrell_corp": {"feat_b": ["efghij"]}}

    prio_vfeats = {"tyrell_corp": ["feat_c"]}

    prio_namespaces = ["NotExistingNamespace", "tyrell_corp", "omnicorp"]

    # Sanity check variant ordering:
    # 1. vprop6. tyrell_corp :: feat_c
    # 2. vprop3. tyrell_corp :: feat_a
    # 3. vprop5. tyrell_corp :: feat_b :: efghij
    # 4. vprop4. tyrell_corp :: feat_b :: abcde
    # 5. vprop1. omnicorp :: feat_a
    # 6. vprop2. omnicorp :: feat_b

    assert sort_variant_properties(
        vprops=vprops,
        namespace_priorities=prio_namespaces,
        feature_priorities=prio_vfeats,
        property_priorities=prio_vprops,
    ) == [vprop6, vprop3, vprop5, vprop4, vprop1, vprop2]

    # Default Ordering: properties are assumed pre-sorted in features/properties
    #                   vprop1 > vprop2 > vprop3 > vprop4 > vprop5 > vprop6
    #                   Note: Namespace is already accounted for in 3)

    # Last Preferential Order: More features are preferred over less features

    # ----------------------------------------------------------------------------- #

    # fmt: off
    expected_vdescs = [
        # Effective vdesc order:
        # 1. Everything with vprop6
        # 1.1. + vprop3
        # 1.1.1. + vprop5
        VariantDescription([vprop1, vprop3, vprop5, vprop6]),
        VariantDescription([vprop3, vprop5, vprop6]),
        # 1.1.2. + vprop4
        VariantDescription([vprop1, vprop3, vprop4, vprop6]),
        VariantDescription([vprop3, vprop4, vprop6]),
        # 1.1.3. + vprop1
        VariantDescription([vprop1, vprop3, vprop6]),
        # 1.1.4. vprop6 + vprop3
        VariantDescription([vprop3, vprop6]),
        # 1.2. + vprop5
        VariantDescription([vprop1, vprop5, vprop6]),
        VariantDescription([vprop5, vprop6]),
        # 1.3. + vprop4
        VariantDescription([vprop1, vprop4, vprop6]),
        VariantDescription([vprop4, vprop6]),
        # 1.4. + vprop1
        VariantDescription([vprop1, vprop6]),
        # 1. sole vprop6
        VariantDescription([vprop6]),

        # 2. Everything with vprop3
        # 2.1. + vprop5
        VariantDescription([vprop1, vprop3, vprop5]),
        VariantDescription([vprop3, vprop5]),
        # 2.2. + vprop4
        VariantDescription([vprop1, vprop3, vprop4]),
        VariantDescription([vprop3, vprop4]),
        # 2.3. + vprop1
        VariantDescription([vprop1, vprop3]),
        # 2. sole vprop3
        VariantDescription([vprop3]),

        # 3. vprop5
        VariantDescription([vprop1, vprop5]),
        VariantDescription([vprop5]),

        # 4. vprop4
        VariantDescription([vprop1, vprop4]),
        VariantDescription([vprop4]),

        # 5. sole vprop1
        VariantDescription([vprop1]),

        # Null-Variant is never removed and last - Implicitly added
        VariantDescription(),
    ]
    # fmt: on

    # Shuffling the list & creating duplicates
    inputs_vdescs = shuffle_vdescs_with_duplicates(vdescs=vdescs)

    assert (
        sort_and_filter_supported_variants(
            vdescs=inputs_vdescs,
            supported_vprops=[vprop1, vprop3, vprop4, vprop5, vprop6],
            property_priorities=prio_vprops,
            feature_priorities=prio_vfeats,
            namespace_priorities=prio_namespaces,
        )
        == expected_vdescs
    )


# # =================== `Validation Testing` ================== #


@pytest.mark.parametrize(
    ("vdescs", "feature_priorities"),
    [
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            "not a list",
        ),
        (
            [VariantDescription([VariantProperty("a", "b", "c")])],
            {"a": [VariantFeature("not_a", "variantproperty")]},
        ),
        ("not a list", {"a": ["a"]}),
        (["not a `VariantDescription`"], {"a": ["a"]}),
    ],
)
def test_sort_and_filter_supported_variants_validation_errors(
    vdescs: list[VariantDescription], feature_priorities: Any
) -> None:
    with pytest.raises(ValidationError):
        sort_and_filter_supported_variants(
            vdescs=vdescs,
            supported_vprops=vprops,  # type: ignore[arg-type]
            namespace_priorities=["a"],
            feature_priorities=feature_priorities,
        )


def test_sort_and_filter_supported_variants_validation_errors_with_no_priority(
    vdescs: list[VariantDescription], vprops: list[VariantProperty]
) -> None:
    # This one specifies no ordering/priority => can't sort
    with pytest.raises(
        ValidationError,
        match=r"Missing namespace_priorities for namespaces \{'omnicorp', "
        r"'tyrell_corp'\}",
    ):
        sort_and_filter_supported_variants(
            vdescs=vdescs,
            supported_vprops=vprops,
            namespace_priorities=[],
        )

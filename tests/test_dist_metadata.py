from __future__ import annotations

import itertools
from email import message_from_string

import pytest

from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER
from variantlib.constants import METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_HASH_HEADER
from variantlib.constants import METADATA_VARIANT_PROPERTY_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_ENABLE_IF_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER
from variantlib.constants import METADATA_VARIANT_PROVIDER_REQUIRES_HEADER
from variantlib.dist_metadata import DistMetadata
from variantlib.models.metadata import ProviderInfo
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.pyproject_toml import VariantPyProjectToml
from variantlib.validators import ValidationError
from variantlib.variants_json import VariantsJson

TEST_METADATA = """\
Metadata-Version: 2.1
Name: test-package
Version: 1.2.3
Variant-property: ns1 :: f1 :: p1
Variant-property: ns1 :: f2 :: p2
Variant-property: ns2 :: f1 :: p1
Variant-hash: 67fcaf38
Variant-requires: ns1: ns1-provider >= 1.2.3
Variant-enable-if: ns1: python_version >= '3.12'
Variant-plugin-api: ns1: ns1_provider.plugin:NS1Plugin
Variant-requires: ns2: ns2_provider; python_version >= '3.11'
Variant-requires: ns2: old_ns2_provider; python_version < '3.11'
Variant-plugin-api: ns2: ns2_provider:Plugin
Variant-default-namespace-priorities: ns1, ns2
Variant-default-feature-priorities: ns2 :: f1, ns1 :: f2
Variant-default-property-priorities: ns1 :: f2 :: p1, ns2 :: f1 :: p2

long description
of a package
"""


def test_dist_metadata():
    metadata = DistMetadata(message_from_string(TEST_METADATA))
    assert metadata.variant_hash == "67fcaf38"
    assert metadata.variant_desc == VariantDescription(
        [
            VariantProperty("ns1", "f1", "p1"),
            VariantProperty("ns1", "f2", "p2"),
            VariantProperty("ns2", "f1", "p1"),
        ]
    )
    assert metadata.namespace_priorities == ["ns1", "ns2"]
    assert metadata.feature_priorities == [
        VariantFeature("ns2", "f1"),
        VariantFeature("ns1", "f2"),
    ]
    assert metadata.property_priorities == [
        VariantProperty("ns1", "f2", "p1"),
        VariantProperty("ns2", "f1", "p2"),
    ]
    assert metadata.providers == {
        "ns1": ProviderInfo(
            requires=["ns1-provider >= 1.2.3"],
            enable_if="python_version >= '3.12'",
            plugin_api="ns1_provider.plugin:NS1Plugin",
        ),
        "ns2": ProviderInfo(
            requires=[
                "ns2_provider; python_version >= '3.11'",
                "old_ns2_provider; python_version < '3.11'",
            ],
            plugin_api="ns2_provider:Plugin",
        ),
    }


def test_missing_variant_hash():
    mangled = "\n".join(
        [x for x in TEST_METADATA.splitlines() if not x.startswith("Variant-hash")]
    )
    with pytest.raises(
        ValidationError,
        match=rf"{METADATA_VARIANT_HASH_HEADER}: found 0 instances of header that "
        r"is expected to occur exactly once",
    ):
        DistMetadata(message_from_string(mangled))


def test_incorrect_variant_hash():
    mangled = "\n".join(
        [x for x in TEST_METADATA.splitlines() if not x.startswith("Variant-property")]
    )
    with pytest.raises(
        ValidationError,
        match=rf"{METADATA_VARIANT_HASH_HEADER} specifies incorrect hash: '67fcaf38'; "
        r"expected: '00000000'",
    ):
        DistMetadata(message_from_string(mangled))


def test_incorrect_property():
    mangled = TEST_METADATA.replace(" :: ", "/")
    with pytest.raises(
        ValidationError,
        match=rf"{METADATA_VARIANT_PROPERTY_HEADER}\[0\]: Value `ns1/f1/p1` must match "
        r"regex",
    ):
        DistMetadata(message_from_string(mangled))


def test_missing_plugin_api():
    mangled = "\n".join(
        [
            x
            for x in TEST_METADATA.splitlines()
            if not x.startswith("Variant-plugin-api")
        ]
    )
    with pytest.raises(
        ValidationError,
        match=rf"{METADATA_VARIANT_PROVIDER_REQUIRES_HEADER} and "
        rf"{METADATA_VARIANT_PROVIDER_ENABLE_IF_HEADER} include namespaces "
        r"that are not included in Variant-plugin-api",
    ):
        DistMetadata(message_from_string(mangled))


@pytest.mark.parametrize(
    "header",
    [
        METADATA_VARIANT_HASH_HEADER,
        METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER,
        METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER,
        METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER,
    ],
)
def test_duplicate_value(header: str):
    mangled = "\n".join(
        itertools.chain.from_iterable(
            [x, x] if x.startswith(header) else [x] for x in TEST_METADATA.splitlines()
        )
    )
    with pytest.raises(
        ValidationError,
        match=rf"{header}: found 2 instances of header that is expected",
    ):
        DistMetadata(message_from_string(mangled))


@pytest.mark.parametrize(
    "header",
    [
        METADATA_VARIANT_PROVIDER_ENABLE_IF_HEADER,
        METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER,
    ],
)
def test_duplicate_provider_value(header: str):
    mangled = "\n".join(
        itertools.chain.from_iterable(
            [x, x] if x.startswith(header) else [x] for x in TEST_METADATA.splitlines()
        )
    )
    with pytest.raises(
        ValidationError,
        match=rf"{header}: duplicate value for namespace ns1",
    ):
        DistMetadata(message_from_string(mangled))


@pytest.mark.parametrize("new_value", ["ns1", "ns3", "ns1, ns2, ns3"])
def test_default_namespace_mismatch(new_value: str):
    mangled = TEST_METADATA.replace("ns1, ns2", new_value)
    with pytest.raises(
        ValidationError,
        match=rf"{METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER} must specify "
        rf"the same namespaces as {METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER} key",
    ):
        DistMetadata(message_from_string(mangled))


@pytest.mark.parametrize("cls", [DistMetadata, VariantPyProjectToml, VariantsJson])
def test_conversion(cls: type[DistMetadata | VariantPyProjectToml | VariantsJson]):
    metadata = DistMetadata(message_from_string(TEST_METADATA))
    converted = cls(metadata)

    # Mangle the original to ensure everything was copied
    metadata.namespace_priorities.append("ns4")
    metadata.feature_priorities.append(VariantFeature("ns4", "foo"))
    metadata.property_priorities.append(VariantProperty("ns4", "foo", "bar"))
    metadata.providers["ns4"] = ProviderInfo(plugin_api="foo:bar")
    metadata.providers["ns1"].enable_if = None
    metadata.providers["ns2"].requires.append("frobnicate")

    assert converted.namespace_priorities == ["ns1", "ns2"]
    assert converted.feature_priorities == [
        VariantFeature("ns2", "f1"),
        VariantFeature("ns1", "f2"),
    ]
    assert converted.property_priorities == [
        VariantProperty("ns1", "f2", "p1"),
        VariantProperty("ns2", "f1", "p2"),
    ]
    assert converted.providers == {
        "ns1": ProviderInfo(
            requires=["ns1-provider >= 1.2.3"],
            enable_if="python_version >= '3.12'",
            plugin_api="ns1_provider.plugin:NS1Plugin",
        ),
        "ns2": ProviderInfo(
            requires=[
                "ns2_provider; python_version >= '3.11'",
                "old_ns2_provider; python_version < '3.11'",
            ],
            plugin_api="ns2_provider:Plugin",
        ),
    }

    # Non-common fields should be reset to defaults
    if isinstance(converted, DistMetadata):
        assert converted.variant_hash == "00000000"
        assert converted.variant_desc == VariantDescription()
    if isinstance(converted, VariantsJson):
        assert converted.variants == {}

from __future__ import annotations

from email import message_from_string

from variantlib.dist_metadata import DistMetadata
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantFeature
from variantlib.models.variant import VariantProperty
from variantlib.pyproject_toml import ProviderInfo

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

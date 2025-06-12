from __future__ import annotations

import re
from pathlib import Path

import pytest

from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.errors import ValidationError
from variantlib.models.metadata import ProviderInfo
from variantlib.models.metadata import VariantMetadata
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.wheel_metadata import VariantDistInfo

VARIANT_JSON = """
{
    "default-priorities": {
        "namespace": [
            "ns"
        ],
        "feature": {},
        "property": {}
    },
    "providers": {
        "ns": {
            "requires": [
                "ns-pkg"
            ]
        }
    },
    "variants": {
        "bdbc6ca0": {
            "ns": {
                "f": "v"
            }
        }
    }
}
"""


@pytest.mark.parametrize("json_type", [str, bytes])
@pytest.mark.parametrize("expected_hash", [None, "bdbc6ca0"])
def test_wheel_metadata(json_type: type, expected_hash: str | None) -> None:
    VARIANT_JSON if json_type is str else VARIANT_JSON.encode()
    metadata = VariantDistInfo(VARIANT_JSON, expected_hash=expected_hash)
    assert metadata.namespace_priorities == ["ns"]
    assert metadata.feature_priorities == {}
    assert metadata.property_priorities == {}
    assert metadata.providers == {"ns": ProviderInfo(requires=["ns-pkg"])}
    vdesc = VariantDescription([VariantProperty("ns", "f", "v")])
    assert metadata.variants == {vdesc.hexdigest: vdesc}
    assert metadata.variant_desc == vdesc
    assert metadata.variant_hash == vdesc.hexdigest


def test_wheel_metadata_wrong_hash() -> None:
    with pytest.raises(
        ValidationError,
        match=re.escape(
            f"{VARIANT_DIST_INFO_FILENAME} specifies hash bdbc6ca0, expected 00000000"
        ),
    ):
        VariantDistInfo(VARIANT_JSON, expected_hash="00000000")


def test_wheel_metadata_multiple_variants() -> None:
    json_file = Path("tests/artifacts/variants.json")
    assert json_file.exists(), "Expected JSON file does not exist"

    with pytest.raises(
        ValidationError,
        match=re.escape(
            f"{VARIANT_DIST_INFO_FILENAME} specifies 6 variants, expected exactly one"
        ),
    ):
        VariantDistInfo(json_file.read_text())


def test_new_wheel_metadata() -> None:
    vmeta = VariantMetadata(
        namespace_priorities=["ns"], providers={"ns": ProviderInfo(requires=["ns-pkg"])}
    )
    metadata = VariantDistInfo(vmeta)
    vdesc = VariantDescription([VariantProperty("ns", "f", "v")])
    metadata.variant_desc = vdesc
    assert metadata.namespace_priorities == vmeta.namespace_priorities
    assert metadata.providers == vmeta.providers
    assert metadata.variant_hash == vdesc.hexdigest
    assert metadata.variant_desc == vdesc

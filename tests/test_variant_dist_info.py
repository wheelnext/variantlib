from __future__ import annotations

import re
from pathlib import Path

import pytest

from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.models.variant_info import ProviderInfo
from variantlib.models.variant_info import VariantInfo
from variantlib.variant_dist_info import VariantDistInfo

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
def test_variant_dist_info(json_type: type, expected_hash: str | None) -> None:
    VARIANT_JSON if json_type is str else VARIANT_JSON.encode()
    variant_dist_info = VariantDistInfo(VARIANT_JSON, expected_hash=expected_hash)
    assert variant_dist_info.namespace_priorities == ["ns"]
    assert variant_dist_info.feature_priorities == {}
    assert variant_dist_info.property_priorities == {}
    assert variant_dist_info.providers == {"ns": ProviderInfo(requires=["ns-pkg"])}
    vdesc = VariantDescription([VariantProperty("ns", "f", "v")])
    assert variant_dist_info.variants == {vdesc.hexdigest: vdesc}
    assert variant_dist_info.variant_desc == vdesc
    assert variant_dist_info.variant_hash == vdesc.hexdigest


def test_variant_dist_info_wrong_hash() -> None:
    with pytest.raises(
        ValidationError,
        match=re.escape(
            f"{VARIANT_DIST_INFO_FILENAME} specifies hash bdbc6ca0, expected 00000000"
        ),
    ):
        VariantDistInfo(VARIANT_JSON, expected_hash="00000000")


def test_variant_dist_info_multiple_variants() -> None:
    json_file = Path("tests/artifacts/variants.json")
    assert json_file.exists(), "Expected JSON file does not exist"

    with pytest.raises(
        ValidationError,
        match=re.escape(
            f"{VARIANT_DIST_INFO_FILENAME} specifies 6 variants, expected exactly one"
        ),
    ):
        VariantDistInfo(json_file.read_text())


def test_new_variant_dist_info() -> None:
    variant_info = VariantInfo(
        namespace_priorities=["ns"], providers={"ns": ProviderInfo(requires=["ns-pkg"])}
    )
    variant_dist_info = VariantDistInfo(variant_info)
    vdesc = VariantDescription([VariantProperty("ns", "f", "v")])
    variant_dist_info.variant_desc = vdesc
    assert variant_dist_info.namespace_priorities == variant_info.namespace_priorities
    assert variant_dist_info.providers == variant_info.providers
    assert variant_dist_info.variant_hash == vdesc.hexdigest
    assert variant_dist_info.variant_desc == vdesc

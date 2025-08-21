from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.constants import VARIANT_INFO_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_INFO_NAMESPACE_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY
from variantlib.errors import ValidationError
from variantlib.models.variant import VariantDescription
from variantlib.models.variant import VariantProperty
from variantlib.models.variant_info import ProviderInfo
from variantlib.models.variant_info import VariantInfo
from variantlib.variant_dist_info import VariantDistInfo

if TYPE_CHECKING:
    from pathlib import Path

VARIANT_JSON = {
    VARIANT_INFO_DEFAULT_PRIO_KEY: {VARIANT_INFO_NAMESPACE_KEY: ["ns"]},
    VARIANT_INFO_PROVIDER_DATA_KEY: {
        "ns": {VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["ns-pkg"]}
    },
    VARIANTS_JSON_VARIANT_DATA_KEY: {"bdbc6ca0e0adb070": {"ns": {"f": ["v"]}}},
}


@pytest.mark.parametrize("json_type", [str, bytes])
@pytest.mark.parametrize("expected_label", [None, "bdbc6ca0e0adb070"])
def test_variant_dist_info(json_type: type, expected_label: str | None) -> None:
    vjson_str = (
        json.dumps(VARIANT_JSON)
        if json_type is str
        else json.dumps(VARIANT_JSON).encode()
    )
    variant_dist_info = VariantDistInfo(vjson_str, expected_label=expected_label)
    assert variant_dist_info.namespace_priorities == ["ns"]
    assert variant_dist_info.feature_priorities == {}
    assert variant_dist_info.property_priorities == {}
    assert variant_dist_info.providers == {"ns": ProviderInfo(requires=["ns-pkg"])}
    vdesc = VariantDescription([VariantProperty("ns", "f", "v")])
    assert variant_dist_info.variants == {vdesc.hexdigest: vdesc}
    assert variant_dist_info.variant_desc == vdesc
    assert variant_dist_info.variant_label == vdesc.hexdigest


@pytest.mark.parametrize("expected_label", [None, "fancy1"])
def test_variant_dist_info_custom_label(expected_label: str | None) -> None:
    vjson_str = json.dumps(VARIANT_JSON).replace("bdbc6ca0e0adb070", "fancy1")
    variant_dist_info = VariantDistInfo(vjson_str, expected_label=expected_label)
    assert variant_dist_info.namespace_priorities == ["ns"]
    assert variant_dist_info.feature_priorities == {}
    assert variant_dist_info.property_priorities == {}
    assert variant_dist_info.providers == {"ns": ProviderInfo(requires=["ns-pkg"])}
    vdesc = VariantDescription([VariantProperty("ns", "f", "v")])
    assert variant_dist_info.variants == {"fancy1": vdesc}
    assert variant_dist_info.variant_desc == vdesc
    assert variant_dist_info.variant_label == "fancy1"


def test_variant_dist_info_multiple_variants(test_artifact_path: Path) -> None:
    json_file = (
        test_artifact_path / "variant_json_files/dummy_project-1.0.0-variants.json"
    )

    if not json_file.exists() or not json_file.is_file():
        raise FileNotFoundError(f"Expected JSON file does not exist: {json_file}")

    with pytest.raises(
        ValidationError,
        match=re.escape(
            f"{VARIANT_DIST_INFO_FILENAME} specifies 10 variants, expected exactly one"
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
    assert variant_dist_info.variant_label == vdesc.hexdigest
    assert variant_dist_info.variant_desc == vdesc

    # changing vdesc should update the label
    vdesc2 = VariantDescription([VariantProperty("ns2", "f2", "v2")])
    variant_dist_info.variant_desc = vdesc2
    assert variant_dist_info.variant_label == vdesc2.hexdigest
    assert variant_dist_info.variant_desc == vdesc2

    # set a custom label
    variant_dist_info.variant_label = "fancy2"
    assert variant_dist_info.variant_label == "fancy2"
    assert variant_dist_info.variant_desc == vdesc2

    # changing vdesc should reset the label
    variant_dist_info.variant_desc = vdesc2
    assert variant_dist_info.variant_label == vdesc2.hexdigest
    assert variant_dist_info.variant_desc == vdesc2

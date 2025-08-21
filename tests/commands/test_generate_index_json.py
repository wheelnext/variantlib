from __future__ import annotations

import json
from pathlib import Path
from shutil import copy
from typing import TYPE_CHECKING

from variantlib.commands.main import main
from variantlib.constants import NULL_VARIANT_LABEL
from variantlib.constants import VARIANT_INFO_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_INFO_NAMESPACE_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_OPTIONAL_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_URL
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY

if TYPE_CHECKING:
    import pytest


def test_generate_index_json(
    tmp_path: Path,
) -> None:
    filenames = [
        "test_package-0-py3-none-any.whl",
        f"test_package-0-py3-none-any-{NULL_VARIANT_LABEL}.whl",
        "test_package-0-py3-none-any-5d8be4b9857b08d4.whl",
    ]
    artifact_dir = Path("tests/artifacts/test-package/dist")
    for filename in filenames:
        copy(artifact_dir / filename, tmp_path / filename)

    main(["generate-index-json", "-d", str(tmp_path)])
    assert json.loads((tmp_path / "test_package-0-variants.json").read_text()) == {
        VARIANTS_JSON_SCHEMA_KEY: VARIANTS_JSON_SCHEMA_URL,
        VARIANT_INFO_DEFAULT_PRIO_KEY: {
            VARIANT_INFO_NAMESPACE_KEY: [
                "installable_plugin",
                "non_existing_plugin",
            ]
        },
        VARIANT_INFO_PROVIDER_DATA_KEY: {
            "installable_plugin": {
                VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["test-plugin-package"],
            },
            "non_existing_plugin": {
                VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["do-not-install-me"],
                VARIANT_INFO_PROVIDER_OPTIONAL_KEY: True,
            },
        },
        VARIANTS_JSON_VARIANT_DATA_KEY: {
            NULL_VARIANT_LABEL: {},
            "5d8be4b9857b08d4": {
                "installable_plugin": {
                    "feat1": ["val1c"],
                    "feat2": ["val2b"],
                },
            },
        },
    }


def test_duplicate_descriptions(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    filenames = [
        "test_package-0-py3-none-any-60567bd9089307ec.whl",
        "test_package-0-py3-none-any-foo.whl",
    ]
    artifact_dir = Path("tests/artifacts/test-package/dist")
    for filename in filenames:
        copy(artifact_dir / filename, tmp_path / filename)

    main(["generate-index-json", "-d", str(tmp_path)])
    assert (
        "Multiple `test_package-0` wheels share the same variant properties: "
        "all of ['60567bd9089307ec', 'foo'] correspond to variant hash "
        "`60567bd9089307ec`"
    ) in caplog.text

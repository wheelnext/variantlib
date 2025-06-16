from __future__ import annotations

import json
from pathlib import Path
from shutil import copy

from variantlib.commands.main import main
from variantlib.constants import VARIANT_INFO_DEFAULT_PRIO_KEY
from variantlib.constants import VARIANT_INFO_NAMESPACE_KEY
from variantlib.constants import VARIANT_INFO_OPTIONAL_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_DATA_KEY
from variantlib.constants import VARIANT_INFO_PROVIDER_REQUIRES_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_KEY
from variantlib.constants import VARIANTS_JSON_SCHEMA_URL
from variantlib.constants import VARIANTS_JSON_VARIANT_DATA_KEY


def test_generate_index_json(
    tmp_path: Path,
) -> None:
    filenames = [
        "test_package-0-py3-none-any.whl",
        "test_package-0-py3-none-any-00000000.whl",
        "test_package-0-py3-none-any-5d8be4b9.whl",
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
        },
        VARIANT_INFO_OPTIONAL_PROVIDER_DATA_KEY: {
            "non_existing_plugin": {
                VARIANT_INFO_PROVIDER_REQUIRES_KEY: ["this-one-is-not-installed"],
            },
        },
        VARIANTS_JSON_VARIANT_DATA_KEY: {
            "00000000": {},
            "5d8be4b9": {
                "installable_plugin": {
                    "feat1": ["val1c"],
                    "feat2": ["val2b"],
                },
            },
        },
    }

from __future__ import annotations

import json
from pathlib import Path
from shutil import copy

from variantlib.commands.main import main


def test_generate_index_json(
    tmp_path: Path,
) -> None:
    filenames = [
        "test_package-0-py3-none-any.whl",
        "test_package-0-py3-none-any-00000000.whl",
        "test_package-0-py3-none-any-5d8be4b9.whl",
    ]
    artifact_dir = Path("tests/artifacts")
    for filename in filenames:
        copy(artifact_dir / filename, tmp_path / filename)

    main(["generate-index-json", "-d", str(tmp_path)])
    assert json.loads((tmp_path / "test_package-0-variants.json").read_text()) == {
        "$schema": "https://variants-schema.wheelnext.dev/",
        "default-priorities": {
            "feature": {},
            "namespace": [
                "installable_plugin",
            ],
            "property": {},
        },
        "providers": {
            "installable_plugin": {
                "plugin-api": "test_plugin_package",
                "requires": ["test-plugin-package @ file:///dev/null"],
            },
        },
        "variants": {
            "00000000": {},
            "5d8be4b9": {
                "installable_plugin": {
                    "feat1": "val1c",
                    "feat2": "val2b",
                },
            },
        },
    }

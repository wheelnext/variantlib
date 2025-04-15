from __future__ import annotations

import re

VARIANT_HASH_LEN = 8
CONFIG_FILENAME = "wheelvariant.toml"

VALIDATION_NAMESPACE_REGEX = r"^[A-Za-z0-9_]+$"
VALIDATION_FEATURE_REGEX = r"^[A-Za-z0-9_]+$"
VALIDATION_VALUE_REGEX = r"^[A-Za-z0-9_.]+$"

METADATA_VARIANT_HASH_HEADER = "Variant-hash"
METADATA_VARIANT_PROPERTY_HEADER = "Variant"

WHEEL_NAME_VALIDATION_REGEX = re.compile(
    rf"""^(?P<namever>(?P<name>[^\s-]+?)-(?P<ver>[^\s-]*?))
        ((-(?P<build>\d[^-]*?))?-(?P<pyver>[^\s-]+?)-(?P<abi>[^\s-]+?)-(?P<plat>[^\s-]+?)
        (-(?P<variant_hash>[0-9a-f]{{{VARIANT_HASH_LEN}}}))?
        \.whl|\.dist-info)$""",
    re.VERBOSE,
)

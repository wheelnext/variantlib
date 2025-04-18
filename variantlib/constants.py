from __future__ import annotations

import re

VARIANT_HASH_LEN = 8
CONFIG_FILENAME = "variants.toml"

VARIANTS_JSON_PROVIDER_DATA_KEY = "providers"
VARIANTS_JSON_VARIANT_DATA_KEY = "variants"

VALIDATION_NAMESPACE_REGEX = r"^[A-Za-z0-9_]+$"
VALIDATION_FEATURE_REGEX = r"^[A-Za-z0-9_]+$"
VALIDATION_VALUE_REGEX = r"^[A-Za-z0-9_.]+$"

METADATA_VARIANT_HASH_HEADER = "Variant-hash"
METADATA_VARIANT_PROPERTY_HEADER = "Variant"
METADATA_VARIANT_PROVIDER_HEADER = "Variant-provider"

WHEEL_NAME_VALIDATION_REGEX = re.compile(
    r"^                                   "
    r"(?P<base_wheel_name>                "  # <base_wheel_name> group (without variant)
    r"  (?P<namever>                      "  # "namever" group contains <name>-<ver>
    r"    (?P<name>[^\s-]+?)              "  # <name>
    r"    - (?P<ver>[^\s-]*?)             "  # "-" <ver>
    r"  )                                 "  # close "namever" group
    r"  ( - (?P<build>\d[^-]*?) )?        "  # optional "-" <build>
    r"  - (?P<pyver>[^\s-]+?)             "  # "-" <pyver> tag
    r"  - (?P<abi>[^\s-]+?)               "  # "-" <abi> tag
    r"  - (?P<plat>[^\s-]+?)              "  # "-" <plat> tag
    r")                                   "  # end of <base_wheel_name> group
    r"( - (?P<variant_hash>               "  # optional <variant_hash>
    rf"    [0-9a-f]{{{VARIANT_HASH_LEN}}} "
    r"    )                               "
    r")?                                  "
    r"\.whl                               "  # ".whl" suffix
    r"$                                   ",
    re.VERBOSE,
)

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
    r"^                                       "
    r"(?P<namever>                            "  # "namever" group contains <name>-<ver>
    r"  (?P<name>[^\s-]+?) - (?P<ver>[^\s-]*?)"  # <name> "-" <ver>
    r")                                       "  # close "namever" group
    r"( - (?P<build>\d[^-]*?) )?              "  # optional "-" <build>
    r"- (?P<pyver>[^\s-]+?)                   "  # "-" <pyver> tag
    r"- (?P<abi>[^\s-]+?)                     "  # "-" <abi> tag
    r"- (?P<plat>[^\s-]+?)                    "  # "-" <plat> tag
    r"( - (?P<variant_hash>                   "  # optional <variant_hash>
    rf"    [0-9a-f]{{{VARIANT_HASH_LEN}}}     "
    r"    )                                   "
    r")?                                      "
    r"\.whl                                   "  # ".whl" suffix
    r"$                                       ",
    re.VERBOSE,
)

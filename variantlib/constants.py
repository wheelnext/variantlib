from __future__ import annotations

import re
from typing import TypedDict

VARIANT_HASH_LEN = 8
CONFIG_FILENAME = "variants.toml"
VARIANT_DIST_INFO_FILENAME = "variant.json"

# Common metadata keys (used in pyproject.toml and variants.json)
VARIANT_METADATA_DEFAULT_PRIO_KEY = "default-priorities"
VARIANT_METADATA_FEATURE_KEY = "feature"
VARIANT_METADATA_NAMESPACE_KEY = "namespace"
VARIANT_METADATA_PROPERTY_KEY = "property"
VARIANT_METADATA_PROVIDER_DATA_KEY = "providers"
VARIANT_METADATA_PROVIDER_ENABLE_IF_KEY = "enable-if"
VARIANT_METADATA_PROVIDER_PLUGIN_API_KEY = "plugin-api"
VARIANT_METADATA_PROVIDER_REQUIRES_KEY = "requires"

PYPROJECT_TOML_TOP_KEY = "variant"

VARIANTS_JSON_SCHEMA_KEY = "$schema"
VARIANTS_JSON_SCHEMA_URL = "https://variants-schema.wheelnext.dev/"
VARIANTS_JSON_VARIANT_DATA_KEY = "variants"

VALIDATION_VARIANT_HASH_REGEX = re.compile(rf"[0-9a-f]{{{VARIANT_HASH_LEN}}}")
VALIDATION_NAMESPACE_REGEX = re.compile(r"[a-z0-9_]+")
VALIDATION_FEATURE_NAME_REGEX = re.compile(r"[a-z0-9_]+")
VALIDATION_VALUE_REGEX = re.compile(r"[a-z0-9_.]+")

VALIDATION_FEATURE_REGEX = re.compile(
    rf"""
    (?P<namespace>{VALIDATION_NAMESPACE_REGEX.pattern})
    \s* :: \s*
    (?P<feature>{VALIDATION_FEATURE_NAME_REGEX.pattern})
""",
    re.VERBOSE,
)

VALIDATION_PROPERTY_REGEX = re.compile(
    rf"""
    (?P<namespace>{VALIDATION_NAMESPACE_REGEX.pattern})
    \s* :: \s*
    (?P<feature>{VALIDATION_FEATURE_NAME_REGEX.pattern})
    \s* :: \s*
    (?P<value>{VALIDATION_VALUE_REGEX.pattern})
""",
    re.VERBOSE,
)

VALIDATION_PROVIDER_ENABLE_IF_REGEX = re.compile(r"[\S ]+")
VALIDATION_PROVIDER_PLUGIN_API_REGEX = re.compile(
    r"""
    (?P<module> [\w.]+)
    \s* : \s*
    (?P<attr> [\w.]+)
    """,
    re.VERBOSE,
)
VALIDATION_PROVIDER_REQUIRES_REGEX = re.compile(r"[\S ]+")

VALIDATION_METADATA_PROVIDER_ENABLE_IF_REGEX = re.compile(
    rf"""
    (?P<namespace>{VALIDATION_NAMESPACE_REGEX.pattern})
    \s* : \s*
    (?P<enable_if>{VALIDATION_PROVIDER_ENABLE_IF_REGEX.pattern})
""",
    re.VERBOSE,
)
VALIDATION_METADATA_PROVIDER_PLUGIN_API_REGEX = re.compile(
    rf"""
    (?P<namespace>{VALIDATION_NAMESPACE_REGEX.pattern})
    \s* : \s*
    (?P<plugin_api>{VALIDATION_PROVIDER_PLUGIN_API_REGEX.pattern})
""",
    re.VERBOSE,
)
VALIDATION_METADATA_PROVIDER_REQUIRES_REGEX = re.compile(
    rf"""
    (?P<namespace>{VALIDATION_NAMESPACE_REGEX.pattern})
    \s* : \s*
    (?P<requirement_str>{VALIDATION_PROVIDER_REQUIRES_REGEX.pattern})
""",
    re.VERBOSE,
)

# VALIDATION_PYTHON_PACKAGE_NAME_REGEX = re.compile(r"[^\s-]+?")
# Per PEP 508: https://peps.python.org/pep-0508/#names
VALIDATION_PYTHON_PACKAGE_NAME_REGEX = re.compile(
    r"[A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9]", re.IGNORECASE
)
VALIDATION_WHEEL_NAME_REGEX = re.compile(
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
    r"                                    ",
    re.VERBOSE,
)


# ======================== Json TypedDict for the JSON format ======================== #

# NOTE: Unfortunately, it is not possible as of today to use variables in the definition
#       of TypedDict. Similarly also impossible to use the normal "class format" if a
#       key uses the characted `-`.
#
#       For all these reasons and easier future maintenance - these classes have been
#       added to this file instead of a more "format definition" file.


class PriorityJsonDict(TypedDict, total=False):
    namespace: list[str]
    feature: dict[str, list[str]]
    property: dict[str, dict[str, list[str]]]


ProviderPluginJsonDict = TypedDict(
    "ProviderPluginJsonDict",
    {
        "plugin-api": str,
        "requires": list[str],
        "enable-if": str,
    },
    total=False,
)

VariantInfoJsonDict = dict[str, dict[str, str]]


VariantsJsonDict = TypedDict(
    "VariantsJsonDict",
    {
        "$schema": str,
        "default-priorities": PriorityJsonDict,
        "providers": dict[str, ProviderPluginJsonDict],
        "variants": dict[str, VariantInfoJsonDict],
    },
    total=False,
)

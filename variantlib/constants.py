from __future__ import annotations

import re

VARIANT_HASH_LEN = 8
CONFIG_FILENAME = "variants.toml"

PYPROJECT_TOML_DEFAULT_PRIO_KEY = "default-priorities"
PYPROJECT_TOML_FEATURE_KEY = "feature"
PYPROJECT_TOML_NAMESPACE_KEY = "namespace"
PYPROJECT_TOML_PROPERTY_KEY = "property"
PYPROJECT_TOML_PROVIDER_DATA_KEY = "providers"
PYPROJECT_TOML_PROVIDER_PLUGIN_API_KEY = "plugin-api"
PYPROJECT_TOML_TOP_KEY = "variant"
PYPROJECT_TOML_PROVIDER_REQUIRES_KEY = "requires"

VARIANTS_JSON_DEFAULT_PRIO_KEY = PYPROJECT_TOML_DEFAULT_PRIO_KEY
VARIANTS_JSON_FEATURE_KEY = PYPROJECT_TOML_FEATURE_KEY
VARIANTS_JSON_NAMESPACE_KEY = PYPROJECT_TOML_NAMESPACE_KEY
VARIANTS_JSON_PROPERTY_KEY = PYPROJECT_TOML_PROPERTY_KEY
VARIANTS_JSON_PROVIDER_DATA_KEY = PYPROJECT_TOML_PROVIDER_DATA_KEY
VARIANTS_JSON_PROVIDER_PLUGIN_API_KEY = PYPROJECT_TOML_PROVIDER_PLUGIN_API_KEY
VARIANTS_JSON_PROVIDER_REQUIRES_KEY = PYPROJECT_TOML_PROVIDER_REQUIRES_KEY
VARIANTS_JSON_VARIANT_DATA_KEY = "variants"

# fmt: off
METADATA_VARIANT_HASH_HEADER = "Variant-hash"
METADATA_VARIANT_PROPERTY_HEADER = "Variant-property"
METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER = f"Variant-default-{PYPROJECT_TOML_FEATURE_KEY}-priorities"  # noqa: E501
METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER = f"Variant-default-{PYPROJECT_TOML_NAMESPACE_KEY}-priorities"  # noqa: E501
METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER = f"Variant-default-{PYPROJECT_TOML_PROPERTY_KEY}-priorities"  # noqa: E501
METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER = f"Variant-{PYPROJECT_TOML_PROVIDER_PLUGIN_API_KEY}"  # noqa: E501
METADATA_VARIANT_PROVIDER_REQUIRES_HEADER = f"Variant-{PYPROJECT_TOML_PROVIDER_REQUIRES_KEY}"  # noqa: E501
# fmt: on

METADATA_ALL_HEADERS = (
    METADATA_VARIANT_HASH_HEADER,
    METADATA_VARIANT_PROPERTY_HEADER,
    METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER,
    METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER,
    METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER,
    METADATA_VARIANT_PROVIDER_PLUGIN_API_HEADER,
    METADATA_VARIANT_PROVIDER_REQUIRES_HEADER,
)

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

VALIDATION_PROVIDER_PLUGIN_API_REGEX = re.compile(
    r"""
    (?P<module> [\w.]+)
    \s* : \s*
    (?P<attr> [\w.]+)
    """,
    re.VERBOSE,
)
VALIDATION_PROVIDER_REQUIRES_REGEX = re.compile(r"[\S ]+")

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

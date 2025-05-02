from __future__ import annotations

import re

VARIANT_HASH_LEN = 8
CONFIG_FILENAME = "variants.toml"

PYPROJECT_TOML_PROVIDER_KEY = "variant-providers"
PYPROJECT_TOML_DEFAULT_PRIO_NAMESPACE_KEY = "default-namespace-priorities"
PYPROJECT_TOML_DEFAULT_PRIO_FEATURE_KEY = "default-feature-priorities"
PYPROJECT_TOML_DEFAULT_PRIO_PROPERTY_KEY = "default-property-priorities"
PYPROJECT_TOML_PROVIDER_REQUIRES_KEY = "requires"
PYPROJECT_TOML_PROVIDER_ENTRY_POINT_KEY = "entry-point"

VARIANTS_JSON_PROVIDER_DATA_KEY = "providers"
VARIANTS_JSON_VARIANT_DATA_KEY = "variants"
VARIANTS_JSON_DEFAULT_PRIO_NAMESPACE_KEY = PYPROJECT_TOML_DEFAULT_PRIO_NAMESPACE_KEY
VARIANTS_JSON_DEFAULT_PRIO_FEATURE_KEY = PYPROJECT_TOML_DEFAULT_PRIO_FEATURE_KEY
VARIANTS_JSON_DEFAULT_PRIO_PROPERTY_KEY = PYPROJECT_TOML_DEFAULT_PRIO_PROPERTY_KEY
VARIANTS_JSON_PROVIDER_REQUIRES_KEY = PYPROJECT_TOML_PROVIDER_REQUIRES_KEY
VARIANTS_JSON_PROVIDER_ENTRY_POINT_KEY = PYPROJECT_TOML_PROVIDER_ENTRY_POINT_KEY

# fmt: off
METADATA_VARIANT_HASH_HEADER = "Variant-hash"
METADATA_VARIANT_PROPERTY_HEADER = "Variant"
METADATA_VARIANT_PROVIDER_REQUIRES_HEADER = f"Variant-{PYPROJECT_TOML_PROVIDER_REQUIRES_KEY}"  # noqa: E501
METADATA_VARIANT_PROVIDER_ENTRYPOINT_HEADER = f"Variant-{PYPROJECT_TOML_PROVIDER_ENTRY_POINT_KEY}"  # noqa: E501
METADATA_VARIANT_DEFAULT_PRIO_NAMESPACE_HEADER = f"Variant-{PYPROJECT_TOML_DEFAULT_PRIO_NAMESPACE_KEY}"  # noqa: E501
METADATA_VARIANT_DEFAULT_PRIO_FEATURE_HEADER = f"Variant-{PYPROJECT_TOML_DEFAULT_PRIO_FEATURE_KEY}"  # noqa: E501
METADATA_VARIANT_DEFAULT_PRIO_PROPERTY_HEADER = f"Variant-{PYPROJECT_TOML_DEFAULT_PRIO_PROPERTY_KEY}"  # noqa: E501
# fmt: on

VALIDATION_VARIANT_HASH_REGEX = re.compile(rf"[0-9a-f]{{{VARIANT_HASH_LEN}}}")
VALIDATION_NAMESPACE_REGEX = re.compile(r"[A-Za-z0-9_]+")
VALIDATION_FEATURE_REGEX = re.compile(r"[A-Za-z0-9_]+")
VALIDATION_VALUE_REGEX = re.compile(r"[A-Za-z0-9_.]+")

VALIDATION_PROVIDER_ENTRYPOINT_REGEX = re.compile(
    r"(?P<namespace>[\S]+)\: ?(?P<entrypoint>[a-zA-Z0-9_.]+\:[a-zA-Z0-9_]+)"
)
VALIDATION_PROVIDER_REQUIRES_REGEX = re.compile(
    r"(?P<namespace>[\S]+)\: ?(?P<requirement_str>[\S ]+)"
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

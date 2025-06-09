from dataclasses import dataclass


@dataclass
class FeatConfig:
    name: str
    values: list[str]


namespace = "installable_plugin"


def get_all_configs() -> list[FeatConfig]:
    return [
        FeatConfig("feat1", ["val1a", "val1b", "val1c"]),
        FeatConfig("feat2", ["val2a", "val2b"]),
    ]


def get_supported_configs() -> list[FeatConfig]:
    return [
        FeatConfig("feat1", ["val1c", "val1b"]),
    ]

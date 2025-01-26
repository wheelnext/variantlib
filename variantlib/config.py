import attr
from attr import validators


@attr.s(frozen=True, repr=False)
class KeyConfig:
    key: str = attr.ib(validator=validators.instance_of(str))
    # Acceptable values in priority order
    values: list[str] = attr.ib(validator=validators.instance_of(list))

    def __repr__(self):
        return f"KeyConfig(key='{self.key}', values={self.values})"

    # Custom validation method to ensure that no key has duplicate values
    def __attrs_post_init__(self):
        self._validate_values()

    def _validate_values(self):
        assert len(self.values) > 0
        assert all(isinstance(value, str) for value in self.values)

        seen = set()
        for value in self.values:
            if value in seen:
                raise ValueError(f"Duplicate value found: '{value}' in `values`.")
            seen.add(value)


@attr.s(frozen=True, repr=False)
class ProviderConfig:
    provider: str = attr.ib(validator=validators.instance_of(str))
    # `KeyConfigs` in priority order
    configs: list[KeyConfig] = attr.ib(validator=validators.instance_of(list))

    # Custom validation method to ensure that no key has duplicate values
    def __attrs_post_init__(self):
        self._validate_configs()

    def _validate_configs(self):
        assert len(self.configs) > 0
        assert all(isinstance(config, KeyConfig) for config in self.configs)

        # Check that no KeyConfig has duplicate keys
        seen = set()
        for config in self.configs:
            key = config.key
            if key in seen:
                raise ValueError(f"Duplicate `KeyConfig` for {key=} found.")
            seen.add(key)

    def __repr__(self):
        return f"ProviderConfig(provider='{self.provider}', configs={self.configs})"

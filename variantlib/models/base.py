from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BaseModel:
    def __post_init__(self) -> None:
        # Execute the validator
        for field_name, field_def in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            if (validator := field_def.metadata.get("validator", None)) is not None:
                validator(value)

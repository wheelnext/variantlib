from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataclasses import Field


@dataclass(frozen=True)
class BaseModel:
    def __post_init__(self) -> None:
        # Execute the validator
        field_def: Field
        for field_name, field_def in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            if (validator := field_def.metadata.get("validator", None)) is not None:
                validator(value)

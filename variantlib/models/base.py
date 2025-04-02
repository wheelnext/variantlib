import hashlib
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from variantlib.constants import VARIANT_HASH_LEN

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


@dataclass(frozen=True)
class BaseHashableModel(ABC, BaseModel):
    @abstractmethod
    def _data_to_hash(self) -> list[bytes]:
        """
        Convert the object to a list of bytes that will be used for hashing.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @property
    def hexdigest(self) -> str:
        return self._compute_hash(self._data_to_hash())

    def _compute_hash(self, data: list[bytes]) -> str:
        """
        Compute the hash of the object.
        """
        hash_object = hashlib.shake_128()
        for item in data:
            hash_object.update(item)

        # Like digest() except the digest is returned as a string object of double
        # length, containing only hexadecimal digits. This may be used to exchange the
        # value safely in email or other non-binary environments.
        # Source: https://docs.python.org/3/library/hashlib.html#hashlib.hash.hexdigest
        return hash_object.hexdigest(int(VARIANT_HASH_LEN / 2))

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.errors import ValidationError
from variantlib.models.metadata import VariantMetadata
from variantlib.variants_json import VariantsJson

if TYPE_CHECKING:
    from variantlib.models.variant import VariantDescription


@dataclass(init=False)
class WheelMetadata(VariantsJson):
    def __init__(
        self,
        metadata_file: bytes | str | VariantMetadata,
        expected_hash: str | None = None,
    ) -> None:
        """Init from pre-read metadata file"""

        if isinstance(metadata_file, VariantMetadata):
            # Convert from another related class.
            super().__init__(metadata_file)
            return

        self._process(json.loads(metadata_file))

        if len(self.variants) != 1:
            raise ValidationError(
                f"{VARIANT_DIST_INFO_FILENAME} specifies "
                f"{len(self.variants)} variants, expected exactly one"
            )
        if expected_hash not in (None, self.variant_hash):
            raise ValidationError(
                f"{VARIANT_DIST_INFO_FILENAME} specifies hash "
                f"{self.variant_hash}, expected {expected_hash}"
            )

    @property
    def variant_hash(self) -> str:
        assert len(self.variants) == 1
        return next(iter(self.variants.keys()))

    @property
    def variant_desc(self) -> VariantDescription:
        assert len(self.variants) == 1
        return next(iter(self.variants.values()))

    @variant_desc.setter
    def variant_desc(self, new_desc: VariantDescription) -> None:
        self.variants = {new_desc.hexdigest: new_desc}

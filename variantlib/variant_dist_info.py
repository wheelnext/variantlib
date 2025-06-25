from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from variantlib.constants import VARIANT_DIST_INFO_FILENAME
from variantlib.errors import ValidationError
from variantlib.models.variant_info import VariantInfo
from variantlib.variants_json import VariantsJson

if TYPE_CHECKING:
    from variantlib.models.variant import VariantDescription


@dataclass(init=False)
class VariantDistInfo(VariantsJson):
    def __init__(
        self,
        dist_info_file: bytes | str | VariantInfo,
        expected_label: str | None = None,
    ) -> None:
        """Init from pre-read dist-info file"""

        if isinstance(dist_info_file, VariantInfo):
            # Convert from another related class.
            super().__init__(dist_info_file)
            return

        self._process(json.loads(dist_info_file))

        if len(self.variants) != 1:
            raise ValidationError(
                f"{VARIANT_DIST_INFO_FILENAME} specifies "
                f"{len(self.variants)} variants, expected exactly one"
            )
        if expected_label not in (None, self.variant_label):
            raise ValidationError(
                f"{VARIANT_DIST_INFO_FILENAME} specifies label "
                f"{self.variant_label}, expected {expected_label}"
            )

    @property
    def variant_label(self) -> str:
        assert len(self.variants) == 1
        return next(iter(self.variants.keys()))

    @variant_label.setter
    def variant_label(self, new_label: str) -> None:
        self.variants = {new_label: self.variant_desc}

    @property
    def variant_desc(self) -> VariantDescription:
        assert len(self.variants) == 1
        return next(iter(self.variants.values()))

    @variant_desc.setter
    def variant_desc(self, new_desc: VariantDescription) -> None:
        self.variants = {new_desc.hexdigest: new_desc}

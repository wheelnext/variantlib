import hashlib

import attr
from attr import validators

from variantlib import VARIANT_HASH_LEN


@attr.s(frozen=True, hash=False, repr=False)
class VariantMeta:
    provider: str = attr.ib(validator=validators.instance_of(str))
    key: str = attr.ib(validator=validators.instance_of(str))
    value: str = attr.ib(validator=validators.instance_of(str))

    def __repr__(self):
        return f"<VariantMeta: `{self.data}`>"

    def __hash__(self):
        # Variant Metas are unique in provider & key and ignore the value.
        return hash((self.provider, self.key))

    @property
    def data(self):
        # Variant: <provider> :: <key> :: <val>
        return f"{self.provider} :: {self.key} :: {self.value}"


class VariantDescription:
    """
    A `Variant` is being described by a N >= 1 `VariantMeta` metadata.
    Each informing the packaging toolkit about a unique `provider-key-value`
    combination.

    All together they identify the package producing a "variant hash", unique
    to the exact combination of `VariantMeta` provided for a given package.
    """

    __slots__ = ("_data",)

    def __init__(self, data: list[VariantMeta]):
        assert isinstance(data, (list, tuple))
        assert all(isinstance(inst, VariantMeta) for inst in data)

        # Detect multiple `VariantMeta` with identical provider/key
        # Ignores the attribute `value` of `VariantMeta`.
        # Uses `__hash__` for collision detection.
        #
        # Note: Can not use `data = set(data)` in order to raise
        #       an exception when there is a collision instead of
        #       a silent behavior.
        seen = set()
        for vmeta in data:
            vmeta_hash = hash(vmeta)
            if vmeta_hash in seen:
                raise ValueError(
                    "Duplicate value for:\n"
                    f"\t- `provider`: {vmeta.provider}\n"
                    f"\t- `key`: {vmeta.key}"
                )
            seen.add(vmeta_hash)

        # We sort the data so that they always get displayed/hashed
        # in a consistent manner.
        self._data = sorted(data, key=lambda x: (x.provider, x.key))

    def __repr__(self):
        return f"<VariantDescription: {list(self)}>"

    def __iter__(self):
        yield from self.data

    @property
    def data(self) -> frozenset[VariantMeta]:
        return self._data

    @property
    def hexdigest(self):
        hash_object = hashlib.shake_128()
        for vdata in self:
            hash_object.update(vdata.data.encode("utf-8"))

        return hash_object.hexdigest(int(VARIANT_HASH_LEN / 2))

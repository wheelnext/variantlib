from __future__ import annotations

from itertools import chain

import pytest

from variantlib.commands.main import main
from variantlib.constants import METADATA_VARIANT_HASH_HEADER


@pytest.mark.parametrize(
    ("properties", "expected"),
    [
        ([], "00000000"),
        (["a::b::c"], "01a9783a"),
        (["d::e::f"], "41665eee"),
        (["a::b::c", "d::e::f"], "eb9a66a7"),
        (["d::e::f", "a::b::c"], "eb9a66a7"),
        (["a::b::c", "d::e::f", "a::c::b"], "1e9328d5"),
    ],
)
def test_get_variant_hash(
    properties: list[str], expected: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["get-variant-hash", *chain.from_iterable(("-p", x) for x in properties)])
    assert capsys.readouterr().out == f"{METADATA_VARIANT_HASH_HEADER}: {expected}\n"

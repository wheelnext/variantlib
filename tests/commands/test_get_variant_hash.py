from __future__ import annotations

import hashlib
from itertools import chain

import pytest

from variantlib.commands.main import main
from variantlib.constants import VARIANT_LABEL_LENGTH


@pytest.mark.parametrize(
    ("properties", "expected"),
    [
        ([], hashlib.sha256(b"").hexdigest()[:VARIANT_LABEL_LENGTH]),
        (["a::b::c"], "01a9783a675c61b7"),
        (["d::e::f"], "41665eeed4205577"),
        (["a::b::c", "d::e::f"], "eb9a66a78027e823"),
        (["d::e::f", "a::b::c"], "eb9a66a78027e823"),
        (["a::b::c", "d::e::f", "a::c::b"], "1e9328d51fa75de2"),
    ],
)
def test_get_variant_hash(
    properties: list[str], expected: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["get-variant-hash", *chain.from_iterable(("-p", x) for x in properties)])
    assert capsys.readouterr().out == f"{expected}\n"

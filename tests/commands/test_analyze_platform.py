from __future__ import annotations

from typing import TYPE_CHECKING

from variantlib.commands.main import main

if TYPE_CHECKING:
    import pytest


def test_analyze_platform(
    capsys: pytest.CaptureFixture[str],
    mocked_entry_points: None,
) -> None:
    main(["analyze-platform"])
    assert (
        capsys.readouterr().out
        == """
#################### Provider Config: `test_namespace` ####################
\t- Variant Config [001]: name1 :: ['val1a', 'val1b']
\t- Variant Config [002]: name2 :: ['val2a', 'val2b', 'val2c']
###########################################################################

#################### Provider Config: `second_namespace` ####################
\t- Variant Config [001]: name3 :: ['val3a']
#############################################################################
"""
    )

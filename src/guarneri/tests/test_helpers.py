"""Test parts of the helpers.py file."""

import pytest

from ..helpers import dynamic_import


@pytest.mark.parametrize(
    "specified, expected, error",
    [
        ["guarneri.helpers.dynamic_import", dynamic_import, None],
    ],
)
def test_dynamic_import(specified, expected, error):
    if error is None:
        obj = dynamic_import(specified)
        assert obj == expected, f"{specified=!r}  {obj=}  {expected=}"
    else:
        with pytest.raises(error):
            obj = dynamic_import(specified)

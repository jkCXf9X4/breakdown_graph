from __future__ import annotations

import pytest

from bd_tree.loader import (
    FilenameError,
    node_path,
    parse_filename,
    parse_ref,
    ref_of,
)


def test_parse_refs_and_filenames():
    assert parse_ref("5") == (5, 0)
    assert parse_ref("5-1") == (5, 1)
    assert parse_ref(12) == (12, 0)
    assert ref_of(5) == "5"
    assert ref_of(5, 2) == "5-2"
    assert parse_filename("12.md") == (12, 0)
    assert parse_filename("12-3.md") == (12, 3)
    assert node_path("/r", 5, 2).name == "5-2.md"


@pytest.mark.parametrize("bad", ["0", "01", "5-0", "5-", "-1", "5-a", "a5", ""])
def test_invalid_refs(bad):
    with pytest.raises(ValueError):
        parse_ref(bad)


@pytest.mark.parametrize("bad", ["0.md", "01.md", "5-0.md", "5-.md", "x.md", "5.txt"])
def test_invalid_filenames(bad):
    with pytest.raises(FilenameError):
        parse_filename(bad)

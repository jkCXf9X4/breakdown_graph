from __future__ import annotations

import pytest

from bdg.loader import (
    FilenameError,
    is_bare_ref,
    is_full_ref,
    node_path,
    parse_filename,
    parse_ref,
    parse_selector,
    ref_of,
)


def test_full_refs_and_versioned_filenames():
    assert parse_ref("5-1") == (5, 1)
    assert parse_ref("12-3") == (12, 3)
    assert ref_of(5, 2) == "5-2"
    assert parse_filename("12-3.md") == (12, 3)
    assert node_path("/r", 5, 2).name == "5-2.md"


def test_bare_ids_are_cli_selectors_not_refs():
    assert parse_selector("5") == (5, None)
    assert parse_selector(12) == (12, None)
    assert parse_selector("5-2") == (5, 2)
    assert is_bare_ref("5") is True
    assert is_full_ref("5") is False
    assert is_full_ref("5-1") is True
    with pytest.raises(ValueError):
        parse_ref("5")
    with pytest.raises(ValueError):
        parse_ref(12)


def test_ref_of_requires_a_positive_version():
    with pytest.raises(ValueError):
        ref_of(5, 0)
    with pytest.raises(ValueError):
        ref_of(0, 1)


@pytest.mark.parametrize(
    "bad", ["0", "01", "5-0", "5-", "-1", "5-a", "a5", "", "5-1-1"]
)
def test_invalid_refs(bad):
    with pytest.raises(ValueError):
        parse_ref(bad)


@pytest.mark.parametrize(
    "bad", ["0.md", "01.md", "5-0.md", "5-.md", "x.md", "5.txt", "5.md"]
)
def test_invalid_filenames_reject_bare_and_version_zero(bad):
    with pytest.raises(FilenameError):
        parse_filename(bad)

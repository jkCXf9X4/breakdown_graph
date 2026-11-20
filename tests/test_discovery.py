"""Store discovery: project roots, hidden stores, and classic stores."""

from __future__ import annotations

import pytest

from bd_tree.api import load, load_view
from bd_tree.cli import _find_root, main
from bd_tree.errors import BreakdownError


def test_load_accepts_project_root_and_store_root(write, tmp_path):
    write(tmp_path / ".bd_tree" / "nodes", 1, contains=[])
    project = load(tmp_path)
    store = load(tmp_path / ".bd_tree")
    assert project.root == (tmp_path / ".bd_tree").resolve()
    assert project.root == store.root
    assert set(project.nodes) == {"1-1"}
    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1"}


def test_discovery_walks_up_to_the_hidden_store(write, tmp_path, monkeypatch):
    write(tmp_path / ".bd_tree" / "nodes", 1, contains=[])
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert _find_root(None) == (tmp_path / ".bd_tree").resolve()
    monkeypatch.chdir(nested)
    assert _find_root(None) == (tmp_path / ".bd_tree").resolve()


def test_root_option_and_env_accept_the_project_root(
    write, tmp_path, monkeypatch, capsys
):
    write(tmp_path / ".bd_tree" / "nodes", 1, contains=[])
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert main(["check", "--root", str(tmp_path)]) == 0
    assert "0 errors" in capsys.readouterr().out

    monkeypatch.setenv("BD_ROOT", str(tmp_path))
    assert _find_root(None) == (tmp_path / ".bd_tree").resolve()
    assert main(["tree", "1-1"]) == 0
    assert "1-1" in capsys.readouterr().out


def test_classic_nodes_wins_over_a_hidden_store(write, tmp_path, monkeypatch):
    write(tmp_path / "nodes", 1, contains=[])
    write(tmp_path / ".bd_tree" / "nodes", 2, contains=[])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    store = load(tmp_path)
    assert store.root == tmp_path.resolve()
    assert store.project_root == tmp_path.resolve()
    assert set(store.nodes) == {"1-1"}
    assert _find_root(None) == tmp_path.resolve()


def test_empty_directory_reports_both_layouts(tmp_path):
    store = load(tmp_path)
    issue = next(issue for issue in store.issues if issue.code == "missing-nodes-dir")
    assert "nodes/" in issue.message
    assert ".bd_tree/nodes" in issue.message


def test_single_store_below_cwd_is_found_and_used(write, tmp_path, monkeypatch, capsys):
    write(tmp_path / "proj" / ".bd_tree" / "nodes", 1, contains=[])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)

    assert _find_root(None) == (tmp_path / "proj" / ".bd_tree").resolve()
    assert main(["views"]) == 0
    captured = capsys.readouterr()
    assert "1-1" in captured.out
    assert "store has no containment roots" not in captured.out + captured.err
    assert "found below" in captured.err


def test_single_classic_store_below_cwd_is_normalized(write, tmp_path, monkeypatch):
    write(tmp_path / "classic" / "nodes", 1, contains=[])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert _find_root(None) == (tmp_path / "classic").resolve()


def test_multiple_stores_below_cwd_are_listed_sorted(write, tmp_path, monkeypatch, capsys):
    write(tmp_path / "alpha" / ".bd_tree" / "nodes", 1, contains=[])
    write(tmp_path / "beta" / "nodes", 1, contains=[])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)

    with pytest.raises(BreakdownError) as caught:
        _find_root(None)
    message = str(caught.value)
    alpha = str((tmp_path / "alpha" / ".bd_tree").resolve())
    beta = str((tmp_path / "beta").resolve())
    assert alpha in message and beta in message
    assert message.index(alpha) < message.index(beta)
    assert "--root" in message and "BD_ROOT=" in message

    capsys.readouterr()
    assert main(["views"]) == 2
    err = capsys.readouterr().err
    assert alpha in err and beta in err
    assert "store has no containment roots" not in err


def test_no_store_is_an_explicit_error(write, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)

    with pytest.raises(BreakdownError) as caught:
        _find_root(None)
    message = str(caught.value)
    assert str(tmp_path) in message
    assert "no store found" in message
    assert "walked up" in message and "downward" in message and "depth 3" in message
    assert "--root" in message and "BD_ROOT=" in message

    capsys.readouterr()
    assert main(["views"]) == 2
    err = capsys.readouterr().err
    assert "store has no containment roots" not in err

    assert main(["find", "anything"]) == 2
    err = capsys.readouterr().err
    assert "store has no nodes" not in err


def test_root_and_env_take_precedence(write, tmp_path, monkeypatch):
    write(tmp_path / "below" / ".bd_tree" / "nodes", 1, contains=[])
    write(tmp_path / "explicit" / "nodes", 1, contains=[])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)

    explicit = (tmp_path / "explicit").resolve()
    assert _find_root(str(tmp_path / "explicit")) == explicit
    monkeypatch.setenv("BD_ROOT", str(tmp_path / "explicit"))
    assert _find_root(None) == explicit


def test_upward_match_beats_a_downward_store(write, tmp_path, monkeypatch):
    write(tmp_path / ".bd_tree" / "nodes", 1, contains=[])
    write(tmp_path / "child" / ".bd_tree" / "nodes", 2, contains=[])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert _find_root(None) == (tmp_path / ".bd_tree").resolve()


def test_downward_scan_is_bounded_at_depth_three(write, tmp_path, monkeypatch):
    write(tmp_path / "a" / "b" / "c" / ".bd_tree" / "nodes", 1, contains=[])
    write(tmp_path / "a" / "b" / "c" / "d" / ".bd_tree" / "nodes", 2, contains=[])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert _find_root(None) == (tmp_path / "a" / "b" / "c" / ".bd_tree").resolve()


def test_depth_four_store_is_not_auto_found(write, tmp_path, monkeypatch):
    write(tmp_path / "a" / "b" / "c" / "d" / ".bd_tree" / "nodes", 1, contains=[])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    with pytest.raises(BreakdownError, match="no store found"):
        _find_root(None)


def test_check_without_a_store_keeps_its_diagnostic(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert main(["check"]) == 1
    captured = capsys.readouterr()
    assert "missing node store" in captured.out
    assert captured.err == ""


def _point(folder, target):
    (folder / ".bd_root").write_text(f"{target}\n", encoding="utf-8")


def test_pointer_disambiguates_two_stores_below_cwd(write, tmp_path, monkeypatch):
    write(tmp_path / "alpha" / ".bd_tree" / "nodes", 1, contains=[])
    write(tmp_path / "beta" / ".bd_tree" / "nodes", 2, contains=[])
    _point(tmp_path, "alpha")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert _find_root(None) == (tmp_path / "alpha" / ".bd_tree").resolve()


def test_pointer_works_from_a_nested_subdirectory(write, tmp_path, monkeypatch):
    write(tmp_path / "alpha" / ".bd_tree" / "nodes", 1, contains=[])
    write(tmp_path / "beta" / ".bd_tree" / "nodes", 2, contains=[])
    _point(tmp_path, "alpha")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert _find_root(None) == (tmp_path / "alpha" / ".bd_tree").resolve()


def test_pointer_accepts_relative_and_absolute_paths(write, tmp_path, monkeypatch):
    write(tmp_path / "alpha" / ".bd_tree" / "nodes", 1, contains=[])
    write(tmp_path / "beta" / ".bd_tree" / "nodes", 2, contains=[])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    expected = (tmp_path / "alpha" / ".bd_tree").resolve()

    _point(tmp_path, "alpha")
    assert _find_root(None) == expected

    _point(tmp_path, (tmp_path / "alpha" / ".bd_tree").resolve())
    assert _find_root(None) == expected


def test_store_in_the_same_directory_beats_a_pointer(write, tmp_path, monkeypatch):
    write(tmp_path / "nodes", 1, contains=[])
    write(tmp_path / "other" / ".bd_tree" / "nodes", 2, contains=[])
    _point(tmp_path, "other")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert _find_root(None) == tmp_path.resolve()


def test_root_and_env_beat_a_pointer(write, tmp_path, monkeypatch):
    write(tmp_path / "alpha" / ".bd_tree" / "nodes", 1, contains=[])
    write(tmp_path / "beta" / ".bd_tree" / "nodes", 2, contains=[])
    _point(tmp_path, "alpha")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    expected = (tmp_path / "beta" / ".bd_tree").resolve()

    assert _find_root(str(tmp_path / "beta")) == expected
    monkeypatch.setenv("BD_ROOT", str(tmp_path / "beta"))
    assert _find_root(None) == expected


@pytest.mark.parametrize(
    "content",
    ["", "alpha\nbeta\n", "missing\n"],
)
def test_invalid_pointer_is_a_structural_refusal(
    write, tmp_path, monkeypatch, capsys, content
):
    write(tmp_path / "alpha" / ".bd_tree" / "nodes", 1, contains=[])
    write(tmp_path / "beta" / ".bd_tree" / "nodes", 2, contains=[])
    (tmp_path / ".bd_root").write_text(content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)

    with pytest.raises(BreakdownError, match="invalid-bd-root"):
        _find_root(None)
    capsys.readouterr()
    assert main(["views"]) == 2
    err = capsys.readouterr().err
    assert "invalid-bd-root" in err
    assert ".bd_root" in err
    if content.strip() == "missing":
        assert "missing" in err


def test_check_without_store_or_pointer_falls_back_to_cwd(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert _find_root(None, allow_missing=True) == tmp_path
    assert main(["check"]) == 1
    assert "missing node store" in capsys.readouterr().out

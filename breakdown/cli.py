"""Command-line interface for the numeric node store.

Front-matter fields are arbitrary user metadata.  Only ``id``, ``legacy``,
``contains``, ``links`` and ``home`` have built-in meaning; display choices are
given on the command line.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import api
from .errors import BreakdownError
from .navigate import (
    NavigationError,
    main_root,
    parse_ref_depth,
    parse_where,
    render_find,
    render_ls,
    render_path,
    render_show,
    render_tree,
)


def _find_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("BD_ROOT")
    if env:
        return Path(env).resolve()
    current = Path.cwd()
    for candidate in [current, *current.parents]:
        if (candidate / "nodes").is_dir():
            return candidate
    return current


def _add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        default=None,
        help="store root (default: $BD_ROOT or nearest parent with nodes/)",
    )


def _add_display(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--path-template",
        default=None,
        help="output path template: {ref} {id} {version} {home} or any field "
        "(default: {home} when every node has one, else {ref}.md)",
    )
    parser.add_argument(
        "--title-field",
        default="title",
        help="front-matter field used as the title (default: title, else ref)",
    )
    parser.add_argument(
        "--summary-field",
        default="summary",
        help="front-matter field used as the summary (default: summary)",
    )


def _display_opts(args: argparse.Namespace) -> dict[str, object]:
    return {
        "path_template": args.path_template,
        "title_field": args.title_field,
        "summary_field": args.summary_field,
    }


def _cmd_view(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    result = api.export_view(
        "tree",
        root,
        args.ref,
        Path(args.out),
        clean=args.clean,
        force=args.force,
        **_display_opts(args),
    )
    print(f"tree -> {result.out}")
    print(f"{result.nodes} nodes, {len(result.files)} files (view {args.ref})")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    opts: dict[str, object] = {}
    if args.view_name in ("tree", "context"):
        opts.update(force=args.force, clean=args.clean, **_display_opts(args))
    elif args.view_name == "dot":
        opts.update(color_by=args.color_by, shape_by=args.shape_by)
    result = api.export_view(
        args.view_name, _find_root(args.root), args.view, Path(args.out), **opts
    )
    print(f"{result.name} -> {result.out}")
    print(f"{result.nodes} nodes, {len(result.files)} files (view {args.view})")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    result = api.check(
        _find_root(args.root),
        args.view,
        root_ref=args.root_ref,
        require=args.require,
        max_lines=args.max_lines,
        max_chars=args.max_chars,
    )
    for issue in result.issues:
        print(issue.format())
    print(
        f"{result.nodes_scanned} nodes, {len(result.errors)} errors, "
        f"{len(result.warnings)} warnings (view {result.view})"
    )
    return 0 if result.ok else 1


def _cmd_versions(args: argparse.Namespace) -> int:
    rows = api.versions(_find_root(args.root), args.id)
    if not rows:
        raise BreakdownError(f"id {args.id} has no node files")
    width = max(len(node.ref) for node in rows)
    print(f"{'ref':<{width}}  {'version':>7}  path")
    for node in rows:
        print(f"{node.ref:<{width}}  {node.version:>7}  {node.path}")
    return 0


def _cmd_fork(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    path = api.fork(root, args.id, args.version)
    print(f"created {path.relative_to(root)}")
    return 0


def _cmd_promote(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    path = api.promote(root, args.ref, keep=args.keep)
    print(f"promoted {args.ref} -> {path.relative_to(root)}")
    return 0


def _cmd_retire_version(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    path = api.retire_version(root, args.ref)
    print(f"deleted {path.relative_to(root)}")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    for entry in api.diff(root, args.left, args.right):
        print(f"{entry.id}: {entry.state}")
    return 0


def _cmd_stale(args: argparse.Namespace) -> int:
    edges = api.stale(_find_root(args.root), args.view)
    for edge in edges:
        print(edge.format())
    print(f"{len(edges)} stale/untracked propagating edges (view {args.view})")
    return 0


def _cmd_reconcile(args: argparse.Namespace) -> int:
    if not args.all and not args.refs:
        raise BreakdownError("give one or more refs or --all")
    if args.all and args.refs:
        raise BreakdownError("use either explicit refs or --all, not both")
    changes = api.reconcile(
        _find_root(args.root), refs=args.refs, view=args.view, all_nodes=args.all
    )
    for change in changes:
        print(change.format())
    print(f"{len(changes)} pins rewritten")
    return 0


def _parse_fields(items: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key.strip():
            raise BreakdownError(f"invalid --field {item!r} (expected key=value)")
        fields[key.strip()] = value
    return fields


def _cmd_new(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    path = api.new_node(
        root,
        parent=args.parent,
        fields=_parse_fields(args.field),
        body=args.body or "",
    )
    print(f"created {path.relative_to(root)}")
    return 0


def _field_list(text: str | None) -> list[str] | None:
    if text is None:
        return None
    fields = [item.strip() for item in text.split(",") if item.strip()]
    if not fields:
        raise NavigationError("--fields needs at least one field name")
    return fields


def _cmd_show(args: argparse.Namespace) -> int:
    store = api.load(_find_root(args.root))
    parsed = parse_ref_depth(args.ref, args.depth)
    depth = 0 if parsed.depth is None else parsed.depth
    print(
        render_show(
            store,
            parsed.ref,
            depth=depth,
            fields=_field_list(args.fields),
            no_body=args.no_body,
            max_chars=args.max_chars,
            show_path=args.path,
        )
    )
    return 0


def _cmd_tree(args: argparse.Namespace) -> int:
    store = api.load(_find_root(args.root))
    parsed = parse_ref_depth(args.ref or main_root(store), args.depth)
    depth = 2 if parsed.depth is None else parsed.depth
    print(
        render_tree(
            store,
            parsed.ref,
            depth=depth,
            summary=args.summary,
            fields=_field_list(args.fields),
        )
    )
    return 0


def _cmd_ls(args: argparse.Namespace) -> int:
    store = api.load(_find_root(args.root))
    parsed = parse_ref_depth(args.ref or main_root(store), args.depth)
    depth = 1 if parsed.depth is None else parsed.depth
    print(
        render_ls(
            store,
            parsed.ref,
            depth=depth,
            columns=_field_list(args.columns),
            max_chars=args.max_chars,
        )
    )
    return 0


def _cmd_find(args: argparse.Namespace) -> int:
    if args.limit < 0:
        raise NavigationError("--limit must be non-negative")
    store = api.load(_find_root(args.root))
    output = render_find(
        store,
        args.query,
        field=args.field,
        regex=args.regex,
        where=parse_where(args.where),
        limit=args.limit,
    )
    if output:
        print(output)
    return 0


def _cmd_grep(args: argparse.Namespace) -> int:
    if args.limit < 0:
        raise NavigationError("--limit must be non-negative")
    store = api.load(_find_root(args.root))
    output = render_find(
        store,
        args.query,
        field=args.field,
        regex=True,
        where=parse_where(args.where),
        limit=args.limit,
    )
    if output:
        print(output)
    return 0


def _cmd_path(args: argparse.Namespace) -> int:
    store = api.load(_find_root(args.root))
    parsed = parse_ref_depth(args.ref)
    print(render_path(store, parsed.ref))
    return 0



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bd",
        description="Numeric markdown information graph with containment views. "
        "Front-matter fields are arbitrary; only id, legacy, contains, links "
        "and home have built-in meaning.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    view = sub.add_parser("view", help="export the tree of one containment view")
    _add_root(view)
    view.add_argument("ref", help="view root ref (e.g. 1 or 5-1)")
    view.add_argument("--out", required=True)
    view.add_argument("--clean", action="store_true", help="remove the output first")
    view.add_argument("--force", action="store_true", help="write into a non-empty dir")
    _add_display(view)
    view.set_defaults(func=_cmd_view)

    export = sub.add_parser("export", help="write a derived view")
    export_sub = export.add_subparsers(dest="view_name", required=True)
    for name, help_text in (
        ("tree", "nodes at templated paths plus one generated INDEX.md"),
        ("context", "fresh nodes only, plus STALE.md and AGENTS.md"),
        ("dot", "Graphviz dot graph"),
    ):
        child = export_sub.add_parser(name, help=help_text)
        _add_root(child)
        child.add_argument("--view", required=True, help="view root ref")
        child.add_argument("--out", required=True)
        if name in ("tree", "context"):
            child.add_argument("--force", action="store_true")
            child.add_argument("--clean", action="store_true")
            _add_display(child)
        else:
            child.add_argument(
                "--color-by",
                default=None,
                help="front-matter field mapped to a stable colour "
                "(default: layer when present, else no colour)",
            )
            child.add_argument(
                "--shape-by",
                default=None,
                help="front-matter field mapped to a stable shape (default: box)",
            )
        child.set_defaults(func=_cmd_export)

    check = sub.add_parser("check", help="validate the store and its views")
    _add_root(check)
    check.add_argument(
        "--view", default=None, help="view root ref to report (default: --root-ref)"
    )
    check.add_argument(
        "--root-ref",
        default=None,
        help="global root ref (default: lowest main ref, normally 1)",
    )
    check.add_argument(
        "--require",
        action="append",
        default=[],
        metavar="FIELD",
        help="require a non-empty front-matter field (repeatable)",
    )
    check.add_argument("--max-lines", type=int, default=None)
    check.add_argument("--max-chars", type=int, default=None)
    check.set_defaults(func=_cmd_check)

    versions = sub.add_parser("versions", help="list main and version files of an id")
    _add_root(versions)
    versions.add_argument("id")
    versions.set_defaults(func=_cmd_versions)

    fork = sub.add_parser("fork", help="copy a main node to the next free version")
    _add_root(fork)
    fork.add_argument("id")
    fork.add_argument("--version", type=int, default=None)
    fork.set_defaults(func=_cmd_fork)

    promote = sub.add_parser("promote", help="copy a version onto the main file")
    _add_root(promote)
    promote.add_argument("ref")
    promote.add_argument("--keep", action="store_true", help="keep the version file")
    promote.set_defaults(func=_cmd_promote)

    retire_version = sub.add_parser("retire-version", help="delete a non-main version")
    _add_root(retire_version)
    retire_version.add_argument("ref")
    retire_version.set_defaults(func=_cmd_retire_version)

    diff = sub.add_parser("diff", help="compare two containment views id by id")
    _add_root(diff)
    diff.add_argument("left")
    diff.add_argument("right")
    diff.set_defaults(func=_cmd_diff)

    stale = sub.add_parser("stale", help="list stale/untracked propagating edges")
    _add_root(stale)
    stale.add_argument("--view", default="1")
    stale.set_defaults(func=_cmd_stale)

    reconcile = sub.add_parser("reconcile", help="rewrite pins for propagating edges")
    _add_root(reconcile)
    reconcile.add_argument("refs", nargs="*", metavar="REF")
    reconcile.add_argument("--all", action="store_true")
    reconcile.add_argument("--view", default="1")
    reconcile.set_defaults(func=_cmd_reconcile)

    new = sub.add_parser(
        "new", help="create the next global id under a parent (fields are arbitrary)"
    )
    _add_root(new)
    new.add_argument("--parent", required=True, help="parent ref (e.g. 1 or 5-1)")
    new.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="arbitrary front-matter field (repeatable)",
    )
    new.add_argument("--body", default="", help="markdown body after the front matter")
    new.set_defaults(func=_cmd_new)

    show = sub.add_parser("show", help="print a node and its descendants")
    _add_root(show)
    show.add_argument("ref", help="ref, optionally with +DEPTH (e.g. 5-1+2)")
    show.add_argument(
        "--depth", type=int, default=None, help="descendant levels (default 0)"
    )
    show.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="truncate each body at N chars (default 0: full)",
    )
    show.add_argument("--no-body", action="store_true", help="headings only")
    show.add_argument(
        "--fields",
        default=None,
        metavar="F,F",
        help="header fields to print (default: all non-reserved fields)",
    )
    show.add_argument("--path", action="store_true", help="prepend the breadcrumb")
    show.set_defaults(func=_cmd_show)

    tree = sub.add_parser("tree", help="print the containment outline")
    _add_root(tree)
    tree.add_argument("ref", nargs="?", default=None, help="root ref (default: main root)")
    tree.add_argument(
        "--depth", type=int, default=None, help="levels (default 2, 0: unlimited)"
    )
    tree.add_argument("--summary", action="store_true", help="append node summaries")
    tree.add_argument(
        "--fields", default=None, metavar="F,F", help="append selected field values"
    )
    tree.set_defaults(func=_cmd_tree)

    ls = sub.add_parser("ls", help="list descendants in columns")
    _add_root(ls)
    ls.add_argument("ref", nargs="?", default=None, help="root ref (default: main root)")
    ls.add_argument(
        "--depth", type=int, default=None, help="levels (default 1)"
    )
    ls.add_argument(
        "--columns",
        default=None,
        metavar="F,F",
        help="columns to print (default ref,title,summary)",
    )
    ls.add_argument(
        "--max-chars",
        type=int,
        default=100,
        help="truncate each cell at N chars (default 100)",
    )
    ls.set_defaults(func=_cmd_ls)

    find = sub.add_parser("find", help="search titles, summaries, bodies and fields")
    _add_root(find)
    find.add_argument("query")
    find.add_argument("--field", default=None, help="restrict to one field (body is body)")
    find.add_argument("--regex", action="store_true", help="use Python regular expressions")
    find.add_argument(
        "--where",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="exact field filter (repeatable)",
    )
    find.add_argument("--limit", type=int, default=20, help="maximum nodes (default 20)")
    find.set_defaults(func=_cmd_find)

    grep = sub.add_parser("grep", help="find with regular expressions on by default")
    _add_root(grep)
    grep.add_argument("query")
    grep.add_argument("--field", default=None, help="restrict to one field (body is body)")
    grep.add_argument(
        "--where",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="exact field filter (repeatable)",
    )
    grep.add_argument("--limit", type=int, default=20, help="maximum nodes (default 20)")
    grep.set_defaults(func=_cmd_grep)

    path = sub.add_parser("path", help="print the ancestry of a ref")
    _add_root(path)
    path.add_argument("ref")
    path.set_defaults(func=_cmd_path)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except NavigationError as exc:
        print(f"bd: {exc}", file=sys.stderr)
        return 1
    except BreakdownError as exc:
        print(f"bd: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

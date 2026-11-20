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
from .loader import resolve_store_root
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
        return resolve_store_root(Path(explicit))
    env = os.environ.get("BD_ROOT")
    if env:
        return resolve_store_root(Path(env))
    current = Path.cwd()
    for candidate in [current, *current.parents]:
        if (candidate / "nodes").is_dir():
            return candidate.resolve()
        if (candidate / ".bd_tree" / "nodes").is_dir():
            return (candidate / ".bd_tree").resolve()
    return current


def _add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        default=None,
        help="store or project root (default: $BD_ROOT or nearest parent "
        "with nodes/ or .bd_tree/nodes)",
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


def _cmd_init(args: argparse.Namespace) -> int:
    root = api.init_store(args.dir)
    print(f"store initialized at {root}")
    print("next:")
    print(f"  cd {root}")
    print('  bd new --parent 1 --field title="First claim" --field layer=claims')
    print("  bd tree 1")
    print("  bd work 1")
    return 0


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


def _cmd_work(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    ref = args.ref or main_root(api.load(root))
    result = api.work(
        root,
        ref,
        Path(args.out) if args.out else None,
        force=args.force,
        clean=args.clean,
        status=args.status,
        writeback=args.writeback,
        **_display_opts(args),
    )
    if args.print_path:
        print(result.out)
        return 0
    if args.status or args.writeback:
        for entry in result.entries:
            if entry.status == "ok":
                continue
            where = f" ({entry.ref})" if entry.ref else ""
            print(f"{entry.status}: {entry.path}{where}")
        for path in result.invalid:
            print(f"invalid: {path} (missing or mismatched front matter)")
        if args.writeback:
            print(f"{result.written} files written back and re-linked")
        ok = sum(1 for entry in result.entries if entry.status == "ok")
        print(
            f"{ok} ok, {len(result.entries) - ok} not ok "
            f"-> {result.out} (view {result.ref})"
        )
        return 0 if result.ok else 1
    print(f"work -> {result.out}")
    print(
        f"{result.nodes} nodes, {result.symlinks} symlinks, "
        f"{len(result.files)} generated files (view {result.ref})"
    )
    if result.git is not None:
        print(f"branch {result.git.branch}")
    return 0


def _cmd_solution_new(args: argparse.Namespace) -> int:
    result = api.solution_new(
        _find_root(args.root),
        args.name,
        path=args.path,
        from_ref=args.from_ref,
    )
    print(f"worktree {result.path}")
    print(f"branch {result.branch}")
    print(f"store {result.store}")
    print(f"cd {result.path}")
    print(f"BD_ROOT={result.store} bd work 1")
    return 0


def _cmd_solution_list(args: argparse.Namespace) -> int:
    entries = api.solution_list(_find_root(args.root))
    path_width = max(len(str(entry.path)) for entry in entries)
    branch_width = max(len(entry.label) for entry in entries)
    print(f"{'path':<{path_width}}  {'branch':<{branch_width}}  head     notes")
    for entry in entries:
        markers = []
        if entry.primary:
            markers.append("main")
        if entry.store:
            markers.append("store")
        line = (
            f"{entry.path!s:<{path_width}}  {entry.label:<{branch_width}}  "
            f"{entry.head[:7]:<7}  {' '.join(markers)}"
        )
        print(line.rstrip())
    return 0


def _cmd_solution_remove(args: argparse.Namespace) -> int:
    entry = api.solution_remove(
        _find_root(args.root), args.target, force=args.force
    )
    print(f"removed {entry.path} (branch {entry.label})")
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


def _cmd_root(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    if args.clear:
        removed = api.clear_root(root)
        print(f"removed {removed.name}" if removed else "no ROOT file")
        return 0
    if args.ref is not None:
        api.set_root(root, args.ref)
    store = api.load(root)
    if store.root_ref is None:
        raise BreakdownError("store has no nodes")
    source = "ROOT" if store.declared_root else "lowest main"
    print(f"{store.root_ref}  ({source})")
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
    root = _find_root(args.root)
    view = args.view or api.load(root).root_ref
    if view is None:
        raise BreakdownError("store has no root ref")
    edges = api.stale(root, view)
    for edge in edges:
        print(edge.format())
    print(f"{len(edges)} stale/untracked propagating edges (view {view})")
    return 0


def _cmd_reconcile(args: argparse.Namespace) -> int:
    if not args.all and not args.refs:
        raise BreakdownError("give one or more refs or --all")
    if args.all and args.refs:
        raise BreakdownError("use either explicit refs or --all, not both")
    root = _find_root(args.root)
    view = args.view or api.load(root).root_ref
    if view is None:
        raise BreakdownError("store has no root ref")
    changes = api.reconcile(root, refs=args.refs, view=view, all_nodes=args.all)
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


def _cmd_contain(args: argparse.Namespace) -> int:
    api.contain(
        _find_root(args.root),
        args.parent,
        args.child,
        before=args.before,
        after=args.after,
    )
    print(f"contained {args.child} in {args.parent}")
    return 0


def _cmd_uncontain(args: argparse.Namespace) -> int:
    api.uncontain(_find_root(args.root), args.parent, args.child)
    print(f"removed {args.child} from {args.parent}")
    return 0


def _cmd_link(args: argparse.Namespace) -> int:
    api.link(
        _find_root(args.root),
        args.source,
        args.target,
        link_type=args.type,
        propagates=args.propagates,
    )
    print(f"linked {args.source} -> {args.target} ({args.type})")
    return 0


def _cmd_unlink(args: argparse.Namespace) -> int:
    api.unlink(
        _find_root(args.root),
        args.source,
        args.target,
        link_type=args.type,
    )
    suffix = f" ({args.type})" if args.type else ""
    print(f"unlinked {args.source} -> {args.target}{suffix}")
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
        epilog="Start with `bd work`: it builds a writable symlink tree over the "
        "store and is the primary editing interface.\n"
        "Edit through the symlinks; every .md file there is the node itself.\n"
        "`bd view` and `bd export` are read-only projections of the same nodes.\n"
        "Solutions are git worktrees (`bd solution`); layouts inside one are `bd work`.\n"
        "Repair a work tree with `bd work REF --status` or `--writeback`.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser(
        "init", help="create a store with one root node in an empty directory"
    )
    init.add_argument("dir", nargs="?", default=".", help="store directory (default: .)")
    init.set_defaults(func=_cmd_init)

    view = sub.add_parser("view", help="read-only copy of one view")
    _add_root(view)
    view.add_argument("ref", help="view root ref (e.g. 1 or 5-1)")
    view.add_argument("--out", required=True)
    view.add_argument("--clean", action="store_true", help="remove the output first")
    view.add_argument("--force", action="store_true", help="write into a non-empty dir")
    _add_display(view)
    view.set_defaults(func=_cmd_view)

    work = sub.add_parser(
        "work",
        help="primary interface: writable symlink tree over the store",
        description="Build the single writable work area for one view. "
        "A different REF replaces its contents.",
    )
    _add_root(work)
    work.add_argument(
        "ref",
        nargs="?",
        default=None,
        help="view root ref (default: ROOT file, else lowest main ref)",
    )
    work.add_argument(
        "--out",
        default=None,
        help="single work area (default: <project>/bd_work); a different REF "
        "replaces its contents",
    )
    _add_display(work)
    work.add_argument("--force", action="store_true", help="overwrite detached files")
    work.add_argument("--clean", action="store_true", help="remove the output first")
    work_mode = work.add_mutually_exclusive_group()
    work_mode.add_argument(
        "--status", action="store_true", help="report the state of the work tree"
    )
    work_mode.add_argument(
        "--writeback",
        action="store_true",
        help="copy detached files back into the store and re-link them",
    )
    work_mode.add_argument(
        "--print",
        dest="print_path",
        action="store_true",
        help='print only the resolved work directory (for cd "$(bd work 1 --print)")',
    )
    work.set_defaults(func=_cmd_work)

    solution = sub.add_parser(
        "solution",
        help="manage solution worktrees (the git boundary)",
        description="A solution is a git worktree. A layout inside one is `bd work`.",
    )
    solution_sub = solution.add_subparsers(dest="solution_command", required=True)

    solution_new = solution_sub.add_parser(
        "new", help="create a worktree for a solution branch"
    )
    _add_root(solution_new)
    solution_new.add_argument("name", help="solution name, also the branch name")
    solution_new.add_argument(
        "--path",
        default=None,
        help="worktree path (default: sibling of the repository root)",
    )
    solution_new.add_argument(
        "--from",
        dest="from_ref",
        default=None,
        metavar="REF",
        help="commit to start a new branch at (default: HEAD)",
    )
    solution_new.set_defaults(func=_cmd_solution_new)

    solution_list = solution_sub.add_parser(
        "list", help="list worktrees and which checkouts contain this store"
    )
    _add_root(solution_list)
    solution_list.set_defaults(func=_cmd_solution_list)

    solution_remove = solution_sub.add_parser(
        "remove", help="remove a worktree, keeping its branch"
    )
    _add_root(solution_remove)
    solution_remove.add_argument("target", metavar="NAME|PATH")
    solution_remove.add_argument(
        "--force", action="store_true", help="remove even with modifications"
    )
    solution_remove.set_defaults(func=_cmd_solution_remove)

    export = sub.add_parser("export", help="read-only derived artifacts")
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
        help="global root ref (default: ROOT file, else lowest main ref)",
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

    root_cmd = sub.add_parser(
        "root", help="show or switch the store root (one-ref ROOT file)"
    )
    _add_root(root_cmd)
    root_cmd.add_argument(
        "ref", nargs="?", default=None, help="ref to declare as root (e.g. 1-4)"
    )
    root_cmd.add_argument(
        "--clear",
        action="store_true",
        help="remove ROOT; fall back to the lowest main ref",
    )
    root_cmd.set_defaults(func=_cmd_root)

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
    stale.add_argument("--view", default=None, help="view ref (default: store root)")
    stale.set_defaults(func=_cmd_stale)

    reconcile = sub.add_parser("reconcile", help="rewrite pins for propagating edges")
    _add_root(reconcile)
    reconcile.add_argument("refs", nargs="*", metavar="REF")
    reconcile.add_argument("--all", action="store_true")
    reconcile.add_argument("--view", default=None, help="view ref (default: store root)")
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

    contain = sub.add_parser("contain", help="add a child to a parent's tree")
    _add_root(contain)
    contain.add_argument("parent", metavar="PARENT")
    contain.add_argument("child", metavar="CHILD")
    placement = contain.add_mutually_exclusive_group()
    placement.add_argument(
        "--before", default=None, metavar="REF", help="insert before this sibling"
    )
    placement.add_argument(
        "--after", default=None, metavar="REF", help="insert after this sibling"
    )
    contain.set_defaults(func=_cmd_contain)

    uncontain = sub.add_parser("uncontain", help="remove a child from a parent's tree")
    _add_root(uncontain)
    uncontain.add_argument("parent", metavar="PARENT")
    uncontain.add_argument("child", metavar="CHILD")
    uncontain.set_defaults(func=_cmd_uncontain)

    link = sub.add_parser("link", help="append a typed link edge")
    _add_root(link)
    link.add_argument("source", metavar="FROM")
    link.add_argument("target", metavar="TO")
    link.add_argument("--type", required=True, help="arbitrary edge label")
    link.add_argument(
        "--propagates",
        action="store_true",
        help="make the edge participate in freshness, pinned to the target now",
    )
    link.set_defaults(func=_cmd_link)

    unlink = sub.add_parser("unlink", help="remove link edges to a target")
    _add_root(unlink)
    unlink.add_argument("source", metavar="FROM")
    unlink.add_argument("target", metavar="TO")
    unlink.add_argument(
        "--type", default=None, help="only remove edges with this label"
    )
    unlink.set_defaults(func=_cmd_unlink)

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

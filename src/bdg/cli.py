"""Command-line interface for the typed-link node store.

Front-matter fields are arbitrary user metadata.  Reserved meaning is
``id``, ``legacy`` and ``freshness`` in front matter, and the reserved
``(TITLE)[[REF,TYPE]]`` link tokens in node bodies; display choices are
given on the command line.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import api
from .errors import BreakdownError
from .graph import (
    build_graph,
    graph_view,
    render_dot,
    render_graph,
    render_in,
    render_out,
    render_svg,
)
from .loader import (
    DISCOVERY_DEPTH,
    resolve_store_root,
    root_pointer_at,
    store_root_at,
    stores_below,
)
from .navigate import (
    NavigationError,
    default_root,
    parse_ref_depth,
    parse_where,
    render_find,
    render_path,
    render_show,
    resolve_ref,
)


def _find_root(explicit: str | None, *, allow_missing: bool = False) -> Path:
    if explicit:
        return resolve_store_root(Path(explicit))
    env = os.environ.get("BDG_ROOT")
    if env:
        return resolve_store_root(Path(env))
    current = Path.cwd()
    for candidate in [current, *current.parents]:
        root = store_root_at(candidate)
        if root is not None:
            return root
        pointer = root_pointer_at(candidate)
        if pointer is not None:
            return pointer

    below = stores_below(current)
    if len(below) > 1:
        listed = ", ".join(str(store) for store in below)
        raise BreakdownError(
            f"multiple stores found below {current}: {listed}; "
            "choose one with --root PATH, BDG_ROOT=PATH, or a .bdg_root pointer"
        )
    if below:
        print(
            f"bdg: using store {below[0]} found below {current}",
            file=sys.stderr,
        )
        return below[0]
    if allow_missing:
        return current
    raise BreakdownError(
        f"no store found from {current}: walked up to the filesystem root and "
        f"scanned downward to depth {DISCOVERY_DEPTH}, but found no nodes/, "
        "bdg_graph/nodes, or .bdg_root pointer; use --root PATH or BDG_ROOT=PATH"
    )


def _add_root(
    parser: argparse.ArgumentParser, *, default: object = argparse.SUPPRESS
) -> None:
    parser.add_argument(
        "--root",
        default=default,
        help="store or project root (default: $BDG_ROOT, nearest parent with "
        "nodes/ or bdg_graph/nodes or a .bdg_root pointer, else a unique store "
        "below cwd)",
    )


def _add_display(
    parser: argparse.ArgumentParser, *, work_layout: bool = False
) -> None:
    if work_layout:
        template_help = (
            "output path template: {ref} {id} {version} {distance} {slug} "
            "{title} or any field (default: {distance}/{ref}_{title}.md ring "
            "folders; a layout already recorded in REFS.md is reused)"
        )
    else:
        template_help = (
            "output path template: {ref} {id} {version} {distance} {slug} "
            "{title} or any field (default: the store file basename)"
        )
    parser.add_argument(
        "--path-template",
        default=None,
        help=template_help,
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
    print('  bdg new --parent 1-1 --field title="First claim"')
    print("  bdg graph 1-1")
    print("  bdg work 1-1")
    return 0


def _print_work_status(result: api.WorkResult) -> int:
    for entry in result.entries:
        if entry.status == "ok":
            continue
        where = f" ({entry.ref})" if entry.ref else ""
        print(f"{entry.status}: {entry.path}{where}")
    for path in result.invalid:
        print(f"invalid: {path} (missing or mismatched front matter)")
    ok = sum(1 for entry in result.entries if entry.status == "ok")
    print(
        f"{ok} ok, {len(result.entries) - ok} not ok "
        f"-> {result.out} (view {result.view_ref})"
    )
    return 0 if result.ok else 1


def _cmd_current(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    if args.status:
        return _print_work_status(
            api.work(root, None, status=True, **_display_opts(args))
        )
    info = api.area(root)
    if info.ref is None:
        raise BreakdownError(
            f"no work area at {info.out}; run `bdg work REF` first"
        )
    if args.path_only:
        print(info.out)
    elif args.view_only:
        print(info.view_ref)
    else:
        print(f"{info.out} (view {info.view_ref})")
    return 0


def _work_anchor(root: Path) -> str | None:
    """The active work-area anchor, read lazily so plain views never need work."""
    try:
        from .work import area as work_area

        return work_area(root).ref
    except Exception:
        return None


def _cmd_views(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    store = api.load(root)
    components = store.components()
    if not components:
        raise BreakdownError("store has no components")
    anchor = _work_anchor(root)
    width = max(len(members[0]) for members in components)
    for members in components:
        representative = store.nodes[members[0]]
        marks = []
        if store.root_ref is not None and store.root_ref in members:
            marks.append("*")
        if anchor is not None and anchor in members:
            marks.append(f"anchor {anchor}")
        suffix = f"  {' '.join(marks)}" if marks else ""
        print(
            f"{representative.ref:<{width}}  {len(members):>4} nodes  "
            f"{representative.title}{suffix}"
        )
    return 0


def _cmd_edit(args: argparse.Namespace) -> int:
    print(api.edit_path(_find_root(args.root), args.ref))
    return 0


def _cmd_work(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    store = api.load(root)
    ref = args.ref
    depth = args.depth
    try:
        if ref is not None:
            parsed = parse_ref_depth(ref, args.depth)
        elif not args.repair:
            parsed = parse_ref_depth(default_root(store), args.depth)
        else:
            parsed = None
    except NavigationError as exc:
        # Malformed ref/depth syntax is a usage error (exit 2), not a miss.
        raise BreakdownError(str(exc)) from exc
    if parsed is not None:
        # A graph anchor resolves against the whole link graph, not only the
        # default closure; api.work dispatches that resolution.
        ref, depth = parsed.ref, parsed.depth
    result = api.work(
        root,
        ref,
        depth=depth,
        force=args.force,
        clean=args.clean,
        writeback=args.repair,
        flat=args.flat,
        **_display_opts(args),
    )
    if args.repair:
        code = _print_work_status(result)
        print(f"{result.written} files written back and re-linked")
        return code
    print(f"work -> {result.out}")
    print(
        f"{result.nodes} nodes, {result.symlinks} symlinks, "
        f"{len(result.files)} generated files (view {result.view_ref})"
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
    print(f"project {result.project}")
    project_dir = result.path / result.project
    print(f"cd {project_dir}")
    print(f"bdg work {result.view}")
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


def _cmd_pack(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    result = api.pack(
        root,
        args.view,
        Path(args.out),
        fresh=args.fresh,
        force=args.force,
        clean=args.clean,
        **_display_opts(args),
    )
    label = "fresh" if args.fresh else "full"
    print(f"pack ({label}) -> {result.out}")
    print(f"{result.nodes} nodes, {len(result.files)} files (view {args.view})")
    return 0


def _parse_rings(text: str | None) -> tuple[int, int] | None:
    if text is None:
        return None
    left, sep, right = text.partition(":")
    if not sep:
        raise BreakdownError(f"invalid --rings {text!r} (expected A:B)")
    try:
        low, high = int(left), int(right)
    except ValueError as exc:
        raise BreakdownError(
            f"invalid --rings {text!r} (expected integers A:B)"
        ) from exc
    if low > high:
        raise BreakdownError(f"invalid --rings {text!r} (A must be <= B)")
    return low, high


def _cmd_graph(args: argparse.Namespace) -> int:
    graph = build_graph(api.load(_find_root(args.root)))
    distances = _parse_rings(args.rings)
    refs = graph_view(
        graph,
        args.ref,
        depth=args.depth,
        distance=distances,
        types=args.type,
    )
    if args.format == "svg":
        text = render_svg(
            graph, refs, color_by=args.color_by, shape_by=args.shape_by
        )
    elif args.format == "dot":
        text = render_dot(
            graph, refs, color_by=args.color_by, shape_by=args.shape_by
        )
    else:
        text = render_graph(graph, refs)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8", newline="")
        print(f"{args.format} -> {args.out}")
    else:
        print(text)
    return 0


def _cmd_out(args: argparse.Namespace) -> int:
    graph = build_graph(api.load(_find_root(args.root)))
    print(render_out(graph, args.ref))
    return 0


def _cmd_in(args: argparse.Namespace) -> int:
    graph = build_graph(api.load(_find_root(args.root)))
    print(render_in(graph, args.ref))
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    root = _find_root(args.root, allow_missing=True)
    view = args.view
    if view is not None:
        try:
            store = api.load(root)
        except BreakdownError:
            store = None
        if store is not None:
            view = resolve_ref(store, view)
    result = api.check(
        root,
        view,
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
    source = "ROOT" if store.declared_root else "lowest node"
    print(f"{store.root_ref}  ({source})")
    return 0


def _cmd_replace(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    old_ref, parent, new_ref = api.replace(root, args.old, args.new)
    if parent == "ROOT":
        print(f"ROOT: {old_ref} -> {new_ref}")
    else:
        print(f"replaced {old_ref} with {new_ref} in {parent}")
    return 0


def _cmd_clone(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    pairs = api.clone(
        root,
        args.ref,
        args.version,
        subtree=args.subtree,
        depth=args.depth,
    )
    for old, new in pairs:
        print(f"{old} -> {new}")
    return 0


def _cmd_delete(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    path = api.delete(root, args.ref, force=args.force)
    print(f"deleted {path.relative_to(root)}")
    return 0


def _cmd_migrate(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    result = api.migrate(
        root,
        dry_run=args.dry_run,
        link_type=args.type,
    )
    for old, new in result.renames:
        print(f"rename {old} -> {new}")
    for line in result.rewrites:
        print(f"rewrite {line}")
    label = "dry run" if args.dry_run else "migrated"
    print(
        f"{label}: {len(result.renames)} renames, "
        f"{len(result.rewrites)} rewrites"
    )
    return 0


def _cmd_retitle(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    view = args.ref
    result = api.retitle(root, view=view, dry_run=args.dry_run)
    verb = "would retitle" if args.dry_run else "retitled"
    print(f"{verb} {result.changed} tokens in {len(result.nodes)} nodes")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    for entry in api.diff(root, args.left, args.right):
        print(f"{entry.id}: {entry.state}")
    return 0


def _cmd_stale(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    store = api.load(root)
    view = args.view if args.view is not None else default_root(store)
    view = resolve_ref(store, view)
    if args.fix:
        if not args.all and not args.refs:
            raise BreakdownError("give one or more REFs or --all with --fix")
        if args.all and args.refs:
            raise BreakdownError("use either explicit refs or --all, not both")
        changes = api.reconcile(root, refs=args.refs, view=view, all_nodes=args.all)
        for change in changes:
            print(change.format())
        print(f"{len(changes)} pins rewritten")
        return 0
    if args.refs or args.all:
        raise BreakdownError("REFs and --all require --fix")
    edges = api.stale(root, view)
    for edge in edges:
        print(edge.format())
    print(f"{len(edges)} stale/untracked propagating edges (view {view})")
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
        link_type=args.type,
    )
    print(f"created {path.relative_to(root)}")
    return 0


def _cmd_link(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    store = api.load(root)
    source = resolve_ref(store, args.source)
    target = resolve_ref(store, args.target)
    api.link(
        root,
        source,
        target,
        link_type=args.type,
        propagates=args.propagates,
    )
    print(f"linked {source} -> {target} ({args.type})")
    return 0


def _cmd_unlink(args: argparse.Namespace) -> int:
    root = _find_root(args.root)
    store = api.load(root)
    source = resolve_ref(store, args.source)
    target = resolve_ref(store, args.target)
    api.unlink(
        root,
        source,
        target,
        link_type=args.type,
    )
    suffix = f" ({args.type})" if args.type else ""
    print(f"unlinked {source} -> {target}{suffix}")
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
    ref = resolve_ref(store, parsed.ref)
    depth = 0 if parsed.depth is None else parsed.depth
    print(
        render_show(
            store,
            ref,
            depth=depth,
            fields=_field_list(args.fields),
            no_body=args.no_body,
            max_chars=args.max_chars,
            links=args.links,
        )
    )
    return 0


def _cmd_find(args: argparse.Namespace) -> int:
    if args.limit < 0:
        raise NavigationError("--limit must be non-negative")
    store = api.load(_find_root(args.root))
    view = None if args.view is None else resolve_ref(store, args.view)
    output = render_find(
        store,
        args.query,
        field=args.field,
        regex=args.regex,
        where=parse_where(args.where),
        limit=args.limit,
        view=view,
        all_nodes=args.all_nodes,
    )
    if output:
        print(output)
    return 0


def _cmd_path(args: argparse.Namespace) -> int:
    store = api.load(_find_root(args.root))
    parsed = parse_ref_depth(args.ref)
    print(render_path(store, resolve_ref(store, parsed.ref)))
    return 0



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bdg",
        description="A numeric markdown graph: typed link tokens in node "
        "bodies projected as undirected distance rings. Front-matter fields "
        "are arbitrary; reserved meaning is id, legacy, freshness in front "
        "matter, and link tokens in bodies.",
        epilog="Start with `bdg work`: it builds a writable symlink tree over the "
        "store and is the primary editing interface.\n"
        "Edit through the symlinks; every node .md file there is the store file.\n"
        "Link tokens are written bare as [[REF,TYPE]] (legacy [[REF, TYPE]] is\n"
        "still accepted on input); cached titles are a tool-written\n"
        "prefix (TITLE)[[REF,TYPE]] that `bdg retitle` regenerates.\n"
        "`bdg pack` materializes a read-only projection of the same nodes.\n"
        "Solutions are git worktrees (`bdg solution`); layouts inside one are `bdg work`.\n"
        "Inspect a work tree with `bdg current --status`; repair it with `bdg work --repair`.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_root(parser, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser(
        "init",
        help="create a store with one root node in an empty directory",
        description="Create a hidden store with one root node and no links. "
        "Add nodes with bdg new --parent or edges with bdg link.",
    )
    init.add_argument("dir", nargs="?", default=".", help="store directory (default: .)")
    init.set_defaults(func=_cmd_init)

    work = sub.add_parser(
        "work",
        help="primary interface: writable symlink tree over the store",
        description="Build the single writable work area for one undirected "
        "view. A different REF replaces its contents; the default layout groups "
        "nodes into ring folders ({distance}/{ref}_{title}.md) with an INDEX.md in each, "
        "and --flat restores store basenames at the root.",
    )
    _add_root(work)
    work.add_argument(
        "ref",
        nargs="?",
        default=None,
        help="view root ref, optionally with +DEPTH (default: ROOT file, "
        "else lowest component representative); in a graph store this is a link anchor",
    )
    work.add_argument(
        "--depth",
        type=int,
        default=None,
        help="link hops to materialize (default: full closure; 0: root only)",
    )
    _add_display(work, work_layout=True)
    work.add_argument("--force", action="store_true", help="overwrite detached files")
    work.add_argument("--clean", action="store_true", help="remove the output first")
    work.add_argument(
        "--flat",
        action="store_true",
        help="restore store basenames at the root, discarding the ring-folder "
        "layout (default: {distance}/{ref}_{title}.md folders)",
    )
    work.add_argument(
        "--repair",
        action="store_true",
        help="copy detached files back into the store and re-link them",
    )
    work.set_defaults(func=_cmd_work)

    current = sub.add_parser(
        "current", help="show the active work area and its view (read-only)"
    )
    _add_root(current)
    _add_display(current)
    current_mode = current.add_mutually_exclusive_group()
    current_mode.add_argument(
        "--path", dest="path_only", action="store_true", help="print only the path"
    )
    current_mode.add_argument(
        "--view", dest="view_only", action="store_true", help="print only the view ref"
    )
    current_mode.add_argument(
        "--status", action="store_true", help="report the state of the work tree"
    )
    current.set_defaults(func=_cmd_current)

    views = sub.add_parser("views", help="list component representatives")
    _add_root(views)
    views.set_defaults(func=_cmd_views)

    edit = sub.add_parser(
        "edit", help="print the path of a ref in the active work area"
    )
    _add_root(edit)
    edit.add_argument("ref")
    edit.set_defaults(func=_cmd_edit)

    solution = sub.add_parser(
        "solution",
        help="manage solution worktrees (the git boundary)",
        description="A solution is a git worktree. A layout inside one is `bdg work`.",
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

    pack = sub.add_parser(
        "pack",
        help="write a view into a directory (read-only projection)",
        description="Default: every node plus INDEX.md. --fresh: only fresh "
        "nodes, plus AGENTS.md and STALE.md.",
    )
    _add_root(pack)
    pack.add_argument("view", help="view root ref")
    pack.add_argument("--out", required=True, help="output directory")
    pack.add_argument(
        "--fresh",
        action="store_true",
        help="fresh nodes only, plus AGENTS.md and STALE.md",
    )
    pack.add_argument("--force", action="store_true", help="write into a non-empty dir")
    pack.add_argument("--clean", action="store_true", help="remove the output first")
    _add_display(pack)
    pack.set_defaults(func=_cmd_pack)

    graph = sub.add_parser(
        "graph",
        help="render an undirected view as distance rings",
    )
    _add_root(graph)
    graph.add_argument(
        "ref",
        nargs="?",
        default=None,
        help="anchor ref or bare id (default: ROOT, else lowest root)",
    )
    graph.add_argument(
        "--depth", type=int, default=None, help="edge hops to follow (default: all)"
    )
    graph.add_argument(
        "--rings",
        default=None,
        metavar="A:B",
        help="inclusive ring range shown in the output (traversal continues)",
    )
    graph.add_argument(
        "--type",
        action="append",
        default=None,
        metavar="T",
        help="only follow this link type (repeatable)",
    )
    graph.add_argument(
        "--format",
        choices=("text", "dot", "svg"),
        default="text",
        help="output format (default: text)",
    )
    graph.add_argument(
        "--color-by",
        default="type",
        help="front-matter field mapped to a stable colour (default: link type)",
    )
    graph.add_argument(
        "--shape-by",
        default=None,
        help="front-matter field mapped to a stable shape (default: box)",
    )
    graph.add_argument(
        "--out", default=None, metavar="PATH", help="write the render to PATH"
    )
    graph.set_defaults(func=_cmd_graph)

    out = sub.add_parser("out", help="list a node's authored out-edges")
    _add_root(out)
    out.add_argument("ref")
    out.set_defaults(func=_cmd_out)

    incoming = sub.add_parser(
        "in", help="list a node's computed in-edges, marked derived"
    )
    _add_root(incoming)
    incoming.add_argument("ref")
    incoming.set_defaults(func=_cmd_in)

    check = sub.add_parser("check", help="validate the store and its views")
    _add_root(check)
    check.add_argument(
        "--view",
        default=None,
        help="view root ref to report (default: ROOT file, else lowest node)",
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

    versions = sub.add_parser(
        "versions", help="list the version files of a logical id"
    )
    _add_root(versions)
    versions.add_argument("id", help="logical id, either 5 or 5-1")
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
        help="remove ROOT; fall back to the lowest node",
    )
    root_cmd.set_defaults(func=_cmd_root)

    clone = sub.add_parser(
        "clone",
        help="copy a node or its subtree",
    )
    _add_root(clone)
    clone.add_argument("ref", help="source ref or bare selector")
    clone.add_argument(
        "--version", type=int, default=None, help="explicit target version"
    )
    clone.add_argument(
        "--subtree",
        action="store_true",
        help="clone the whole undirected component and rewire the copies",
    )
    clone.add_argument(
        "--depth",
        type=int,
        default=None,
        help="clone BFS rings 0..N of the component (implies subtree)",
    )
    clone.set_defaults(func=_cmd_clone)

    replace = sub.add_parser(
        "replace",
        help="repoint one ref to another",
    )
    _add_root(replace)
    replace.add_argument("old", help="ref currently in the default view")
    replace.add_argument("new", help="ref to put in its place")
    replace.set_defaults(func=_cmd_replace)

    delete = sub.add_parser(
        "delete", help="delete one node file (refuses bound refs)"
    )
    _add_root(delete)
    delete.add_argument("ref")
    delete.add_argument(
        "--force",
        action="store_true",
        help="delete even when the ref is the root or still referenced",
    )
    delete.set_defaults(func=_cmd_delete)

    migrate = sub.add_parser(
        "migrate",
        help="convert a legacy store to prefix-form body link tokens",
        description="Version bare filenames, then move every front-matter "
        "links and contains list into a trailing ## Links section of "
        "(TITLE)[[REF,TYPE]] token lines in each node body. Tokens in either "
        "component order are normalized to ref-first; retired suffix tokens "
        "[[TYPE, REF]](TITLE) and [[REF, TYPE]](TITLE) are rewritten to the "
        "prefix form, missing "
        "titles are filled from the target, and retired placement keys (band, "
        "subpath, layer, stage, order, band_layout, band_order) are stripped.",
    )
    _add_root(migrate)
    migrate.add_argument(
        "--type",
        default="breaks_down",
        help="link type for converted containment edges (default: breaks_down)",
    )
    migrate.add_argument(
        "--dry-run", action="store_true", help="print the plan without touching disk"
    )
    migrate.set_defaults(func=_cmd_migrate)

    diff = sub.add_parser("diff", help="compare two views id by id")
    _add_root(diff)
    diff.add_argument("left")
    diff.add_argument("right")
    diff.set_defaults(func=_cmd_diff)

    stale = sub.add_parser(
        "stale",
        help="list stale/untracked propagating edges; --fix rewrites their pins",
    )
    _add_root(stale)
    stale.add_argument("refs", nargs="*", metavar="REF")
    stale.add_argument("--all", action="store_true", help="fix every ref")
    stale.add_argument("--fix", action="store_true", help="rewrite the pins")
    stale.add_argument("--view", default=None, help="view ref (default: store root)")
    stale.set_defaults(func=_cmd_stale)

    retitle = sub.add_parser(
        "retitle",
        help="regenerate cached token titles from live target titles",
        description="Rewrite every cached title inside link tokens to its "
        "target's live title, in prose and in ## Links lines. The cached title "
        "is the prefix (TITLE)[[REF,TYPE]]. Tokens whose target is unresolved "
        "are left untouched.",
    )
    _add_root(retitle)
    retitle.add_argument(
        "ref", nargs="?", default=None, help="view ref (default: the whole store)"
    )
    retitle.add_argument(
        "--dry-run", action="store_true", help="print the plan without touching disk"
    )
    retitle.set_defaults(func=_cmd_retitle)

    new = sub.add_parser(
        "new",
        help="create the next global id and link it from a parent",
        description="Append the new ref as a typed edge token "
        "(TITLE)[[REF,TYPE]] of --parent, titled with the new node's live "
        "title. No authored placement is written. Without --parent the node "
        "starts its own component.",
    )
    _add_root(new)
    new.add_argument(
        "--parent",
        default=None,
        help="parent ref (e.g. 1-1 or 5); optional (omit for a new root)",
    )
    new.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="arbitrary front-matter field (repeatable)",
    )
    new.add_argument("--body", default="", help="markdown body after the front matter")
    new.add_argument(
        "--type",
        default="breaks_down",
        help="edge type from --parent (default: breaks_down)",
    )
    new.set_defaults(func=_cmd_new)

    link = sub.add_parser(
        "link",
        help="append a typed link edge token to the FROM node body",
        description="Append a typed edge token (TITLE)[[REF,TYPE]] in the "
        "FROM node's ## Links body section, titled with the target's live "
        "title. Back-edges, reciprocal edges and cycles are legal; a self-loop "
        "is refused.",
    )
    _add_root(link)
    link.add_argument("source", metavar="FROM")
    link.add_argument("target", metavar="TO")
    link.add_argument(
        "--type",
        required=True,
        help="edge type written in the FROM node body token",
    )
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

    show = sub.add_parser("show", help="print a node and its distance rings")
    _add_root(show)
    show.add_argument("ref", help="ref, optionally with +DEPTH (e.g. 5-1+2)")
    show.add_argument(
        "--depth", type=int, default=None, help="descendant levels (default 0)"
    )
    show.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="truncate each body at N chars (default: full at depth 0, "
        "4000 per node when depth > 0; 0 means full)",
    )
    show.add_argument("--no-body", action="store_true", help="headings only")
    show.add_argument(
        "--fields",
        default=None,
        metavar="F,F",
        help="header fields to print (default: all non-reserved fields)",
    )
    show.add_argument(
        "--links",
        action="store_true",
        help="list links (authored out and derived in)",
    )
    show.set_defaults(func=_cmd_show)

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
    find.add_argument(
        "--view", default=None, help="view ref (default: store root)"
    )
    find.add_argument(
        "--all", dest="all_nodes", action="store_true",
        help="search the whole store, including nodes outside the view",
    )
    find.set_defaults(func=_cmd_find)

    path = sub.add_parser("path", help="print the shortest undirected path to a ref")
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
        print(f"bdg: {exc}", file=sys.stderr)
        return 1
    except BreakdownError as exc:
        print(f"bdg: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

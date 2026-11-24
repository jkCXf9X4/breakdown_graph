from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from bd_tree import ops
from bd_tree.api import link, load, new_node
from bd_tree.fsutil import lock_path


def slow_loader(monkeypatch, delay: float = 0.05) -> None:
    """Widen the read-modify-write window a racy writer would lose in."""
    real_load = ops.load

    def slow_load(root):
        store = real_load(root)
        time.sleep(delay)
        return store

    monkeypatch.setattr(ops, "load", slow_load)


def test_parallel_new_takes_distinct_ids_and_keeps_every_child(
    write, tmp_path, monkeypatch
):
    write(tmp_path / "nodes", 1, band="root", order=0)
    slow_loader(monkeypatch, delay=0.15)

    workers = 8
    ready = threading.Barrier(workers)

    def create(index: int):
        ready.wait()
        return new_node(
            tmp_path,
            parent="1",
            fields={"title": f"w{index}"},
            band="children",
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(create, index) for index in range(workers)]
        paths = [future.result() for future in futures]

    assert sorted(path.name for path in paths) == [
        f"{node_id}-1.md" for node_id in range(2, workers + 2)
    ]
    store = load(tmp_path)
    assert len(store.nodes) == workers + 1
    assert store.children("1-1") == [
        f"{node_id}-1" for node_id in range(2, workers + 2)
    ]
    assert sorted(
        node.meta["title"] for node in store.nodes.values() if node.id != 1
    ) == sorted(f"w{index}" for index in range(workers))


def test_store_lock_lives_outside_the_store(tmp_path):
    assert tmp_path not in lock_path(tmp_path).parents
    assert not any(tmp_path.glob("*.lock"))


def test_parallel_link_keeps_every_edge(write, tmp_path, monkeypatch):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", order=0)
    for node_id in range(2, 10):
        write(nodes, node_id, band="children", order=node_id - 2)
    slow_loader(monkeypatch)

    workers = 8
    ready = threading.Barrier(workers)

    def attach(index: int):
        ready.wait()
        return link(tmp_path, "1-1", f"{index + 2}-1", link_type="supports")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(attach, index) for index in range(workers)]
        for future in futures:
            future.result()

    edges = {edge.to for edge in load(tmp_path).nodes["1-1"].links}
    assert edges == {f"{node_id}-1" for node_id in range(2, 10)}

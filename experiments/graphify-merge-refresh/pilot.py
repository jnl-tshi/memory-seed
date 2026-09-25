"""Small disposable probe of stock Graphify's deterministic Markdown rebuild."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from graphify.watch import _rebuild_code


def sources(graph_path: Path) -> set[str]:
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    return {str(node.get("source_file", "")) for node in data["nodes"]}


def references(graph_path: Path) -> set[tuple[str, str]]:
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    edges = data.get("links", data.get("edges", []))
    nodes = {str(node["id"]): str(node.get("source_file", "")) for node in data["nodes"]}
    return {
        (str(edge.get("source_file", "")), nodes.get(str(edge.get("target", "")), ""))
        for edge in edges
        if edge.get("relation") == "references"
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="graphify-md-pilot-") as temporary:
        root = Path(temporary)
        docs = root / "docs"
        docs.mkdir()
        alpha = docs / "alpha.md"
        beta = docs / "beta.md"
        alpha.write_text("# Alpha\n\n[Beta](./beta.md)\n", encoding="utf-8")
        beta.write_text("# Beta\n", encoding="utf-8")
        graph = root / "graphify-out" / "graph.json"

        assert _rebuild_code(root, no_cluster=True, block_on_lock=True)
        initial = references(graph)
        assert any("alpha.md" in source and "beta.md" in target for source, target in initial), initial

        alpha.write_text("# Alpha revised\n\n[Beta](./beta.md)\n", encoding="utf-8")
        assert _rebuild_code(root, changed_paths=[alpha], no_cluster=True, block_on_lock=True)
        edited = references(graph)
        assert any("alpha.md" in source and "beta.md" in target for source, target in edited), edited

        beta.rename(docs / "gamma.md")
        alpha.write_text("# Alpha revised\n\n[Gamma](./gamma.md)\n", encoding="utf-8")
        assert _rebuild_code(
            root,
            changed_paths=[alpha, beta, docs / "gamma.md"],
            no_cluster=True,
            block_on_lock=True,
        )
        renamed = sources(graph)
        assert not any("beta.md" in source for source in renamed), renamed
        assert any("gamma.md" in source for source in renamed), renamed

        alpha.unlink()
        assert _rebuild_code(root, changed_paths=[alpha], no_cluster=True, block_on_lock=True)
        deleted = sources(graph)
        assert not any("alpha.md" in source for source in deleted), deleted
        print("PASS: full, edit, link preservation, rename, and delete")


if __name__ == "__main__":
    main()

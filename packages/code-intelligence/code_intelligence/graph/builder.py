"""Repository graph data structures representing symbols, files, and dependencies."""

from collections import defaultdict
from typing import Any

from code_intelligence.models import FileDependency, Symbol, SymbolReference


class RepositoryGraph:
    """In-memory directed multigraph of repository code entities and relational edges."""

    def __init__(self, repository_id: str = "", commit_sha: str = ""):
        self.repository_id = repository_id
        self.commit_sha = commit_sha
        # node_id -> { "type": str, "name": str, "file_path": str, "metadata": dict }
        self.nodes: dict[str, dict[str, Any]] = {}
        # source_id -> list of (target_id, edge_type, metadata)
        self.outgoing_edges: dict[str, list[dict[str, Any]]] = defaultdict(list)
        # target_id -> list of (source_id, edge_type, metadata)
        self.incoming_edges: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def add_node(self, node_id: str, node_type: str, name: str, file_path: str, metadata: dict[str, Any] | None = None):
        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "name": name,
            "file_path": file_path,
            "metadata": metadata or {},
        }

    def add_edge(self, source_id: str, target_id: str, edge_type: str, metadata: dict[str, Any] | None = None):
        edge_data = {
            "source_id": source_id,
            "target_id": target_id,
            "type": edge_type,
            "metadata": metadata or {},
        }
        self.outgoing_edges[source_id].append(edge_data)
        self.incoming_edges[target_id].append(edge_data)

    def get_direct_callers(self, symbol_name: str, file_path: str | None = None) -> list[dict[str, Any]]:
        """Find symbols calling the specified target symbol."""
        callers: list[dict[str, Any]] = []
        target_suffix = symbol_name.split(".")[-1]

        for target_id, edges in self.incoming_edges.items():
            node = self.nodes.get(target_id)
            if not node:
                continue
            if node["name"] == symbol_name or node["name"].endswith("." + target_suffix) or target_id.endswith("::" + symbol_name):
                if file_path and node.get("file_path") != file_path:
                    continue
                for edge in edges:
                    if edge["type"] == "CALLS":
                        caller_node = self.nodes.get(edge["source_id"])
                        if caller_node:
                            callers.append(caller_node)
        return callers

    def get_file_dependencies(self, file_path: str) -> list[str]:
        """Return files that the specified file depends on (imports)."""
        deps: set[str] = set()
        file_node_id = f"file::{file_path}"
        for edge in self.outgoing_edges.get(file_node_id, []):
            if edge["type"] in ("IMPORTS", "REQUIRES"):
                target = edge["target_id"].replace("file::", "")
                deps.add(target)
        return sorted(deps)

    def get_file_dependents(self, file_path: str) -> list[str]:
        """Return files that depend on the specified file."""
        dependents: set[str] = set()
        file_node_id = f"file::{file_path}"
        for edge in self.incoming_edges.get(file_node_id, []):
            if edge["type"] in ("IMPORTS", "REQUIRES"):
                src = edge["source_id"].replace("file::", "")
                dependents.add(src)
        return sorted(dependents)

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph for diagnostics or debugging APIs."""
        return {
            "repository_id": self.repository_id,
            "commit_sha": self.commit_sha,
            "node_count": len(self.nodes),
            "edge_count": sum(len(edges) for edges in self.outgoing_edges.values()),
            "nodes": list(self.nodes.values()),
            "edges": [
                edge for edge_list in self.outgoing_edges.values() for edge in edge_list
            ],
        }


class RepositoryGraphBuilder:
    """Constructs RepositoryGraph from symbols, references, and dependencies."""

    @classmethod
    def build_graph(
        cls,
        repository_id: str,
        commit_sha: str,
        symbols: list[Symbol],
        references: list[SymbolReference],
        dependencies: list[FileDependency],
    ) -> RepositoryGraph:
        graph = RepositoryGraph(repository_id=repository_id, commit_sha=commit_sha)

        # 1. Add file nodes
        all_files = {s.file_path for s in symbols} | {d.source_file for d in dependencies}
        for f in all_files:
            graph.add_node(node_id=f"file::{f}", node_type="File", name=f, file_path=f)

        # 2. Add symbol nodes
        for sym in symbols:
            node_id = sym.symbol_id or f"{sym.file_path}::{sym.name}"
            graph.add_node(
                node_id=node_id,
                node_type=sym.kind.value,
                name=sym.name,
                file_path=sym.file_path,
                metadata={
                    "start_line": sym.start_line,
                    "end_line": sym.end_line,
                    "signature": sym.signature,
                    "parent_symbol": sym.parent_symbol,
                },
            )
            # Link file -> symbol (DEFINES)
            graph.add_edge(f"file::{sym.file_path}", node_id, "DEFINES")

        # 3. Add file dependency edges (IMPORTS)
        for dep in dependencies:
            src_node = f"file::{dep.source_file}"
            target_node = f"file::{dep.target_file}"
            if target_node not in graph.nodes:
                matched_target = next(
                    (
                        f
                        for f in all_files
                        if f == dep.target_file
                        or f.endswith("/" + dep.target_file)
                        or dep.target_file.endswith("/" + f)
                    ),
                    None,
                )
                if matched_target:
                    target_node = f"file::{matched_target}"
                else:
                    graph.add_node(target_node, "File", dep.target_file, dep.target_file)
            graph.add_edge(
                src_node,
                target_node,
                dep.dependency_type,
                {"imported_symbols": dep.imported_symbols},
            )

        # 4. Add symbol reference edges (CALLS, INHERITS, IMPLEMENTS)
        for ref in references:
            src_id = f"{ref.source_file}::{ref.source_symbol}"
            if src_id not in graph.nodes:
                matched_src = next(
                    (
                        nid
                        for nid in graph.nodes
                        if nid.startswith(f"{ref.source_file}::")
                        and nid.endswith((f".{ref.source_symbol}", f"::{ref.source_symbol}"))
                    ),
                    None,
                )
                src_id = matched_src or f"file::{ref.source_file}"

            target_file = ref.target_file or ref.source_file
            target_id = f"{target_file}::{ref.target_symbol}"
            if target_id not in graph.nodes:
                matched_target = next(
                    (
                        nid
                        for nid in graph.nodes
                        if nid.startswith(f"{target_file}::")
                        and nid.endswith((f".{ref.target_symbol}", f"::{ref.target_symbol}"))
                    ),
                    None,
                )
                target_id = matched_target or f"file::{target_file}"

            edge_type = (
                "CALLS"
                if ref.reference_type.value == "CALL"
                else (
                    "INHERITS"
                    if ref.reference_type.value == "INHERITANCE"
                    else (
                        "IMPLEMENTS"
                        if ref.reference_type.value == "IMPLEMENTATION"
                        else "REFERENCES"
                    )
                )
            )

            graph.add_edge(
                src_id,
                target_id,
                edge_type,
                {"line_number": ref.line_number, "resolved": ref.resolved},
            )

        return graph

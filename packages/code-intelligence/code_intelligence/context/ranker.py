"""Deterministic context ranking and budgeting engine."""


from code_intelligence.graph.builder import RepositoryGraph
from code_intelligence.models import (
    ASTChunk,
    RankedContextItem,
    RelevantContext,
    Symbol,
)


class ContextRanker:
    """
    Deterministic relevance ranking and budget manager for code context.
    Ranks code entities by graph distance and structural relationships without LLM calls.
    Enforces strict budgeting on max files, symbols, and character tokens.
    """

    # Deterministic priority weights
    WEIGHT_CHANGED_FILE = 1.0
    WEIGHT_DIRECT_CALLER = 0.85
    WEIGHT_DIRECT_DEPENDENCY = 0.80
    WEIGHT_INHERITANCE = 0.75
    WEIGHT_TWO_HOP = 0.50

    DEFAULT_MAX_FILES = 15
    DEFAULT_MAX_SYMBOLS = 30
    DEFAULT_MAX_CHARACTERS = 25000

    def rank_and_budget(
        self,
        candidate_items: list[RankedContextItem],
        max_files: int = DEFAULT_MAX_FILES,
        max_symbols: int = DEFAULT_MAX_SYMBOLS,
        max_characters: int = DEFAULT_MAX_CHARACTERS,
    ) -> list[RankedContextItem]:
        """
        Sort candidate context items by relevance score descending and truncate according
        to strict file, symbol, and character limits.
        """
        # Sort deterministically by relevance score descending, then by identifier ascending
        sorted_items = sorted(
            candidate_items,
            key=lambda item: (-item.relevance_score, item.identifier),
        )

        selected: list[RankedContextItem] = []
        seen_files: set[str] = set()
        symbol_count = 0
        total_chars = 0

        for item in sorted_items:
            # Check file limit
            is_new_file = item.file_path not in seen_files
            if is_new_file and len(seen_files) >= max_files:
                continue

            # Check symbol limit if this is a symbol or chunk item
            if item.entity_type in ("SYMBOL", "CHUNK") and symbol_count >= max_symbols:
                continue

            # Check character budget
            item_chars = item.char_count or (len(item.content) if item.content else 0)
            if total_chars + item_chars > max_characters and selected:
                # Exceeded character budget; stop adding items
                continue

            # Accept item
            selected.append(item)
            seen_files.add(item.file_path)
            if item.entity_type in ("SYMBOL", "CHUNK"):
                symbol_count += 1
            total_chars += item_chars

        return selected

    def build_relevant_context(
        self,
        repository_id: str,
        commit_sha: str,
        changed_file: str,
        changed_symbol: str | None = None,
        changed_chunk: ASTChunk | None = None,
        graph: RepositoryGraph | None = None,
        symbols: list[Symbol] | None = None,
        max_files: int = DEFAULT_MAX_FILES,
        max_symbols: int = DEFAULT_MAX_SYMBOLS,
        max_characters: int = DEFAULT_MAX_CHARACTERS,
    ) -> RelevantContext:
        """
        Retrieve and assemble semantically ranked context for a changed file and symbol.
        """
        symbols = symbols or []
        symbols_by_name: dict[str, Symbol] = {s.name: s for s in symbols}
        symbols_by_file: dict[str, list[Symbol]] = {}
        for s in symbols:
            symbols_by_file.setdefault(s.file_path, []).append(s)

        candidate_items: list[RankedContextItem] = []

        # 1. Highest Priority: Changed AST chunk and file
        if changed_chunk:
            candidate_items.append(
                RankedContextItem(
                    entity_type="CHUNK",
                    identifier=changed_chunk.symbol_name,
                    file_path=changed_file,
                    relevance_score=self.WEIGHT_CHANGED_FILE,
                    reason="Target changed AST chunk",
                    content=changed_chunk.source_code,
                    symbol_signature=changed_chunk.signature,
                    char_count=len(changed_chunk.source_code),
                )
            )

        # 2. Symbols in the changed file
        for sym in symbols_by_file.get(changed_file, []):
            if changed_chunk and sym.name == changed_chunk.symbol_name:
                continue
            content = sym.source_code or sym.signature or ""
            candidate_items.append(
                RankedContextItem(
                    entity_type="SYMBOL",
                    identifier=sym.name,
                    file_path=changed_file,
                    relevance_score=self.WEIGHT_CHANGED_FILE * 0.95,
                    reason="Sibling symbol in changed file",
                    content=content,
                    symbol_signature=sym.signature,
                    char_count=len(content),
                )
            )

        direct_callers: list[str] = []
        direct_dependencies: list[str] = []
        relevant_imports: list[str] = []
        relevant_types: list[str] = []
        related_files: set[str] = {changed_file}
        signatures: dict[str, str] = {}

        if changed_chunk and changed_chunk.signature:
            signatures[changed_chunk.symbol_name] = changed_chunk.signature

        # 3. Direct callers and direct dependencies from RepositoryGraph
        if graph:
            # Get direct callers of changed symbol
            target_sym = changed_symbol or (changed_chunk.symbol_name if changed_chunk else "")
            if target_sym:
                callers = graph.get_direct_callers(target_sym, file_path=changed_file)
                for caller in callers:
                    c_name = caller["name"]
                    c_file = caller.get("file_path", "")
                    direct_callers.append(f"{c_file}::{c_name}")
                    related_files.add(c_file)

                    sym_obj = symbols_by_name.get(c_name)
                    sig = sym_obj.signature if sym_obj else caller.get("metadata", {}).get("signature")
                    if sig:
                        signatures[c_name] = sig

                    candidate_items.append(
                        RankedContextItem(
                            entity_type="CALLER",
                            identifier=c_name,
                            file_path=c_file,
                            relevance_score=self.WEIGHT_DIRECT_CALLER,
                            reason=f"Direct caller of {target_sym}",
                            content=sym_obj.source_code if sym_obj else None,
                            symbol_signature=sig,
                            char_count=len(sym_obj.source_code) if (sym_obj and sym_obj.source_code) else 0,
                        )
                    )

            # Get direct file dependencies (imports)
            deps = graph.get_file_dependencies(changed_file)
            for dep_file in deps:
                direct_dependencies.append(dep_file)
                relevant_imports.append(dep_file)
                related_files.add(dep_file)

                # Add top symbols from dependency file
                dep_symbols = symbols_by_file.get(dep_file, [])
                for d_sym in dep_symbols[:3]:  # Top symbols from dependency
                    if d_sym.signature:
                        signatures[d_sym.name] = d_sym.signature
                    candidate_items.append(
                        RankedContextItem(
                            entity_type="DEPENDENCY",
                            identifier=d_sym.name,
                            file_path=dep_file,
                            relevance_score=self.WEIGHT_DIRECT_DEPENDENCY,
                            reason=f"Direct dependency from {changed_file}",
                            content=d_sym.source_code or d_sym.signature,
                            symbol_signature=d_sym.signature,
                            char_count=len(d_sym.source_code or d_sym.signature or ""),
                        )
                    )

                # 4. Two-hop dependencies
                two_hop_deps = graph.get_file_dependencies(dep_file)
                for hop2 in two_hop_deps:
                    if hop2 not in related_files:
                        related_files.add(hop2)
                        for hop_sym in symbols_by_file.get(hop2, [])[:2]:
                            candidate_items.append(
                                RankedContextItem(
                                    entity_type="DEPENDENCY",
                                    identifier=hop_sym.name,
                                    file_path=hop2,
                                    relevance_score=self.WEIGHT_TWO_HOP,
                                    reason=f"Two-hop dependency via {dep_file}",
                                    content=hop_sym.signature,
                                    symbol_signature=hop_sym.signature,
                                    char_count=len(hop_sym.signature or ""),
                                )
                            )

        # Budget candidate items
        budgeted_items = self.rank_and_budget(
            candidate_items,
            max_files=max_files,
            max_symbols=max_symbols,
            max_characters=max_characters,
        )

        total_chars = sum(item.char_count for item in budgeted_items)

        return RelevantContext(
            repository_id=repository_id,
            commit_sha=commit_sha,
            changed_file=changed_file,
            changed_symbol=changed_symbol or (changed_chunk.symbol_name if changed_chunk else None),
            changed_chunk=changed_chunk,
            parent_entity=changed_chunk.parent_symbol if changed_chunk else None,
            relevant_imports=sorted(set(relevant_imports)),
            direct_callers=sorted(set(direct_callers)),
            direct_dependencies=sorted(set(direct_dependencies)),
            relevant_types=sorted(set(relevant_types)),
            related_files=sorted(related_files),
            symbol_signatures=signatures,
            ranked_items=budgeted_items,
            total_characters=total_chars,
        )

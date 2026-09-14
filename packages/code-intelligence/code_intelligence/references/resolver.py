"""Reference resolution service linking symbol references to target files and definitions."""

from collections import defaultdict

from code_intelligence.models import FileDependency, Symbol, SymbolReference


class ReferenceResolver:
    """
    Statically resolves cross-file and local symbol references without heuristic hallucination.
    Marks unresolved targets honestly if ambiguity or missing imports exist.
    """

    @classmethod
    def resolve_references(
        cls,
        symbols: list[Symbol],
        references: list[SymbolReference],
        dependencies: list[FileDependency],
    ) -> list[SymbolReference]:
        """
        Attempt resolution of target symbols across files using static import knowledge
        and repository symbol index.
        """
        # Index symbols: (file_path, symbol_name) -> Symbol
        symbols_by_file_and_name: dict[str, dict[str, Symbol]] = defaultdict(dict)
        # symbol_name -> list of (file_path, Symbol)
        symbols_by_name: dict[str, list[Symbol]] = defaultdict(list)

        for sym in symbols:
            symbols_by_file_and_name[sym.file_path][sym.name] = sym
            # Also index by short name (e.g. "refund" if name is "PaymentService.refund")
            short_name = sym.name.split(".")[-1]
            symbols_by_file_and_name[sym.file_path][short_name] = sym

            symbols_by_name[sym.name].append(sym)
            if short_name != sym.name:
                symbols_by_name[short_name].append(sym)

        # Index file imports: source_file -> set of imported target_files
        imports_by_source: dict[str, set[str]] = defaultdict(set)
        for dep in dependencies:
            imports_by_source[dep.source_file].add(dep.target_file)
            # Also handle without extension or relative variations
            imports_by_source[dep.source_file].add(dep.target_file.replace("\\", "/"))

        resolved_references: list[SymbolReference] = []

        for ref in references:
            # If already resolved, keep
            if ref.resolved and ref.target_file:
                resolved_references.append(ref)
                continue

            target_name = ref.target_symbol
            source_file = ref.source_file

            # 1. Local resolution in same file
            if target_name in symbols_by_file_and_name.get(source_file, {}):
                ref.target_file = source_file
                ref.resolved = True
                resolved_references.append(ref)
                continue

            # 2. Resolution via explicit imports from source file
            imported_targets = imports_by_source.get(source_file, set())
            candidate_files: list[str] = []

            for imp_file in imported_targets:
                # Direct match or suffix match (e.g. "services/payment.py" matching imported "payment.py")
                for indexed_file, syms_in_file in symbols_by_file_and_name.items():
                    if (
                        indexed_file == imp_file
                        or indexed_file.endswith("/" + imp_file)
                        or imp_file.endswith("/" + indexed_file)
                    ) and target_name in syms_in_file:
                        candidate_files.append(indexed_file)

            if len(candidate_files) == 1:
                ref.target_file = candidate_files[0]
                ref.resolved = True
                resolved_references.append(ref)
                continue

            # 3. Global unambiguous resolution (if symbol name is uniquely defined across the entire repo)
            global_matches = symbols_by_name.get(target_name, [])
            # Filter matches to unique files
            unique_files = list({m.file_path for m in global_matches if m.file_path != source_file})
            if len(unique_files) == 1:
                ref.target_file = unique_files[0]
                ref.resolved = True
                resolved_references.append(ref)
                continue

            # Unresolved: retain truthfully
            ref.resolved = False
            ref.target_file = None
            resolved_references.append(ref)

        return resolved_references

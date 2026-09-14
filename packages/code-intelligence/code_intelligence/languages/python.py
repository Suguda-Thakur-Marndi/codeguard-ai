"""Tree-sitter language parser adapter for Python."""

import hashlib
from typing import Any

import tree_sitter_python as tspython
from code_intelligence.languages.base import LanguageParser
from code_intelligence.models import (
    ASTChunk,
    DiagnosticStage,
    FileDependency,
    ParserDiagnostic,
    ReferenceType,
    Symbol,
    SymbolKind,
    SymbolReference,
)
from tree_sitter import Language, Node, Parser, Tree


class PythonParser(LanguageParser):
    """Python AST Analyzer utilizing Tree-sitter for semantic structure extraction."""

    language_name = "python"

    def __init__(self):
        self._language = Language(tspython.language())
        self._parser = Parser(self._language)

    def parse(
        self, source_code: str | bytes, file_path: str = ""
    ) -> tuple[Tree | None, list[ParserDiagnostic]]:
        """Parse Python source code into a Tree-sitter Tree."""
        diagnostics: list[ParserDiagnostic] = []
        if isinstance(source_code, str):
            source_bytes = source_code.encode("utf-8")
        else:
            source_bytes = source_code

        try:
            tree = self._parser.parse(source_bytes)
            diagnostics.extend(self.check_tree_errors(tree, file_path))
            return tree, diagnostics
        except Exception as exc:  # noqa: BLE001
            diagnostics.append(
                ParserDiagnostic(
                    file_path=file_path,
                    stage=DiagnosticStage.AST_PARSE,
                    error_type=exc.__class__.__name__,
                    message=f"Failed to parse Python file: {exc!s}",
                )
            )
            return None, diagnostics

    def extract_symbols(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[Symbol]:
        """Extract classes, methods, functions, and top-level variables."""
        symbols: list[Symbol] = []
        if not tree or not tree.root_node:
            return symbols

        def _traverse(node: Node, parent_name: str | None = None):
            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    class_name = self.get_node_text(name_node, source_bytes)
                    start_l, end_l = self.get_node_lines(node)
                    superclasses_node = node.child_by_field_name("superclasses")
                    sig = f"class {class_name}"
                    if superclasses_node:
                        sig += self.get_node_text(superclasses_node, source_bytes)

                    symbol_id = f"{file_path}::{class_name}"
                    symbols.append(
                        Symbol(
                            symbol_id=symbol_id,
                            name=class_name,
                            kind=SymbolKind.CLASS,
                            file_path=file_path,
                            start_line=start_l,
                            end_line=end_l,
                            start_byte=node.start_byte,
                            end_byte=node.end_byte,
                            signature=sig,
                            parent_symbol=parent_name,
                            language=self.language_name,
                            source_code=self.get_node_text(node, source_bytes),
                            metadata={"superclasses": self.get_node_text(superclasses_node, source_bytes) if superclasses_node else None},
                        )
                    )

                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            _traverse(child, parent_name=class_name)
                    return

            elif node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    fn_name = self.get_node_text(name_node, source_bytes)
                    start_l, end_l = self.get_node_lines(node)
                    params_node = node.child_by_field_name("parameters")
                    ret_node = node.child_by_field_name("return_type")

                    sig_parts = [f"def {fn_name}"]
                    if params_node:
                        sig_parts.append(self.get_node_text(params_node, source_bytes))
                    if ret_node:
                        sig_parts.append(f" -> {self.get_node_text(ret_node, source_bytes)}")
                    signature = "".join(sig_parts)

                    kind = SymbolKind.METHOD if parent_name else SymbolKind.FUNCTION
                    full_name = f"{parent_name}.{fn_name}" if parent_name else fn_name
                    symbol_id = f"{file_path}::{full_name}"

                    # Extract parameter list details
                    param_list: list[dict[str, Any]] = []
                    if params_node:
                        for p in params_node.children:
                            if p.type in ("identifier", "typed_parameter", "default_parameter"):
                                param_list.append({"text": self.get_node_text(p, source_bytes)})

                    symbols.append(
                        Symbol(
                            symbol_id=symbol_id,
                            name=full_name,
                            kind=kind,
                            file_path=file_path,
                            start_line=start_l,
                            end_line=end_l,
                            start_byte=node.start_byte,
                            end_byte=node.end_byte,
                            signature=signature,
                            return_type=self.get_node_text(ret_node, source_bytes) if ret_node else None,
                            parameters=param_list,
                            parent_symbol=parent_name,
                            language=self.language_name,
                            source_code=self.get_node_text(node, source_bytes),
                        )
                    )

                    # Also traverse nested functions
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            _traverse(child, parent_name=full_name)
                    return

            for child in node.children:
                _traverse(child, parent_name)

        _traverse(tree.root_node)
        return symbols

    def extract_imports(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[FileDependency]:
        """Extract import statements (import ... and from ... import ...)."""
        deps: list[FileDependency] = []
        if not tree or not tree.root_node:
            return deps

        for node in tree.root_node.children:
            if node.type == "import_statement":
                # import foo, import foo.bar
                start_l, _ = self.get_node_lines(node)
                for child in node.children:
                    if child.type == "dotted_name":
                        mod_name = self.get_node_text(child, source_bytes)
                        deps.append(
                            FileDependency(
                                source_file=file_path,
                                target_file=mod_name.replace(".", "/") + ".py",
                                dependency_type="IMPORTS",
                                imported_symbols=[mod_name],
                                line_number=start_l,
                                metadata={"module": mod_name},
                            )
                        )
            elif node.type == "import_from_statement":
                start_l, _ = self.get_node_lines(node)
                mod_node = node.child_by_field_name("module_name")
                relative_dots = [c for c in node.children if c.type == "relative_import"]
                mod_name = ""
                if mod_node:
                    mod_name = self.get_node_text(mod_node, source_bytes)
                elif relative_dots:
                    mod_name = self.get_node_text(relative_dots[0], source_bytes)

                # Extract imported names
                imported_symbols: list[str] = []
                for child in node.children:
                    if child.type == "dotted_name" and child != mod_node:
                        imported_symbols.append(self.get_node_text(child, source_bytes))
                    elif child.type == "import_list":
                        for item in child.children:
                            if item.type in ("identifier", "dotted_name", "aliased_import"):
                                imported_symbols.append(self.get_node_text(item, source_bytes).split(" as ")[0].strip())
                    elif child.type == "identifier" and child != mod_node:
                        text = self.get_node_text(child, source_bytes)
                        if text not in ("from", "import"):
                            imported_symbols.append(text)

                target_file = mod_name.lstrip(".").replace(".", "/") + ".py"
                deps.append(
                    FileDependency(
                        source_file=file_path,
                        target_file=target_file,
                        dependency_type="IMPORTS",
                        imported_symbols=imported_symbols,
                        line_number=start_l,
                        metadata={"module": mod_name, "raw": self.get_node_text(node, source_bytes)},
                    )
                )

        return deps

    def extract_references(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[SymbolReference]:
        """Extract symbol calls, inheritance, and instantiations."""
        references: list[SymbolReference] = []
        if not tree or not tree.root_node:
            return references

        def _traverse(node: Node, current_symbol: str = "module"):
            # Update current enclosing symbol context
            enclosing = current_symbol
            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    class_name = self.get_node_text(name_node, source_bytes)
                    enclosing = class_name
                    # Check inheritance superclasses
                    superclasses = node.child_by_field_name("superclasses")
                    if superclasses:
                        start_l, _ = self.get_node_lines(node)
                        for c in superclasses.children:
                            if c.type in ("identifier", "attribute"):
                                target = self.get_node_text(c, source_bytes)
                                references.append(
                                    SymbolReference(
                                        source_symbol=class_name,
                                        target_symbol=target,
                                        source_file=file_path,
                                        line_number=start_l,
                                        reference_type=ReferenceType.INHERITANCE,
                                        resolved=False,
                                    )
                                )
            elif node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    fn_name = self.get_node_text(name_node, source_bytes)
                    enclosing = f"{current_symbol}.{fn_name}" if current_symbol != "module" else fn_name

            elif node.type == "call":
                fn_node = node.child_by_field_name("function")
                if fn_node:
                    fn_text = self.get_node_text(fn_node, source_bytes)
                    start_l, _ = self.get_node_lines(node)
                    # Extract target name (e.g. self.repo.save -> save, or verify -> verify)
                    target_name = fn_text.split(".")[-1]
                    references.append(
                        SymbolReference(
                            source_symbol=enclosing,
                            target_symbol=target_name,
                            source_file=file_path,
                            line_number=start_l,
                            reference_type=ReferenceType.CALL,
                            resolved=False,
                            metadata={"full_call_expression": fn_text},
                        )
                    )

            for child in node.children:
                _traverse(child, enclosing)

        _traverse(tree.root_node)
        return references

    def find_enclosing_chunk(
        self, tree: Tree, source_bytes: bytes, line_number: int, file_path: str
    ) -> ASTChunk | None:
        """Find smallest useful semantic entity enclosing line_number (1-indexed)."""
        if not tree or not tree.root_node:
            return None

        matching_nodes: list[Node] = []

        def _find_matches(node: Node):
            start_l, end_l = self.get_node_lines(node)
            if start_l <= line_number <= end_l:
                if node.type in ("function_definition", "class_definition", "module"):
                    matching_nodes.append(node)
                for child in node.children:
                    _find_matches(child)

        _find_matches(tree.root_node)
        if not matching_nodes:
            return None

        # Sort by smallest line span (deepest enclosing node), preferring function over class over module
        def _rank(n: Node):
            start_l, end_l = self.get_node_lines(n)
            span = end_l - start_l
            type_weight = 1 if n.type == "function_definition" else (2 if n.type == "class_definition" else 3)
            return (type_weight, span)

        best_node = min(matching_nodes, key=_rank)
        start_l, end_l = self.get_node_lines(best_node)

        name_node = best_node.child_by_field_name("name") if best_node.type != "module" else None
        symbol_name = self.get_node_text(name_node, source_bytes) if name_node else file_path

        # Determine parent
        parent_name = None
        curr = best_node.parent
        while curr:
            if curr.type in ("class_definition", "function_definition"):
                p_name = curr.child_by_field_name("name")
                if p_name:
                    parent_name = self.get_node_text(p_name, source_bytes)
                    symbol_name = f"{parent_name}.{symbol_name}"
                    break
            curr = curr.parent

        chunk_id = hashlib.sha256(f"{file_path}:{start_l}:{end_l}:{symbol_name}".encode()).hexdigest()[:16]

        sig = None
        ret_type = None
        if best_node.type == "function_definition":
            params = best_node.child_by_field_name("parameters")
            ret = best_node.child_by_field_name("return_type")
            sig = f"def {symbol_name}" + (self.get_node_text(params, source_bytes) if params else "()")
            if ret:
                ret_type = self.get_node_text(ret, source_bytes)
                sig += f" -> {ret_type}"
        elif best_node.type == "class_definition":
            sig = f"class {symbol_name}"

        return ASTChunk(
            id=chunk_id,
            file_path=file_path,
            language=self.language_name,
            node_type=best_node.type,
            symbol_name=symbol_name,
            start_line=start_l,
            end_line=end_l,
            start_byte=best_node.start_byte,
            end_byte=best_node.end_byte,
            source_code=self.get_node_text(best_node, source_bytes),
            parent_symbol=parent_name,
            signature=sig,
            return_type=ret_type,
        )

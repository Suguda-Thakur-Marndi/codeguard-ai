"""Tree-sitter language parser adapter for TypeScript and TSX."""

import hashlib

import tree_sitter_typescript as tstypescript
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


class TypeScriptParser(LanguageParser):
    """TypeScript/TSX AST Analyzer utilizing Tree-sitter for semantic structure extraction."""

    language_name = "typescript"

    def __init__(self, is_tsx: bool = False):
        self.is_tsx = is_tsx
        if is_tsx:
            self._language = Language(tstypescript.language_tsx())
        else:
            self._language = Language(tstypescript.language_typescript())
        self._parser = Parser(self._language)

    def parse(
        self, source_code: str | bytes, file_path: str = ""
    ) -> tuple[Tree | None, list[ParserDiagnostic]]:
        """Parse TypeScript source code into a Tree-sitter Tree."""
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
                    message=f"Failed to parse TypeScript file: {exc!s}",
                )
            )
            return None, diagnostics

    def extract_symbols(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[Symbol]:
        """Extract functions, classes, methods, interfaces, and types."""
        symbols: list[Symbol] = []
        if not tree or not tree.root_node:
            return symbols

        def _traverse(node: Node, parent_name: str | None = None):
            # Unwrap export statements
            target_node = node
            if node.type == "export_statement":
                inner_decl = [
                    c for c in node.children
                    if c.type in ("class_declaration", "function_declaration", "interface_declaration", "type_alias_declaration", "lexical_declaration")
                ]
                if inner_decl:
                    target_node = inner_decl[0]

            if target_node.type == "interface_declaration":
                name_n = target_node.child_by_field_name("name")
                if name_n:
                    iface_name = self.get_node_text(name_n, source_bytes)
                    start_l, end_l = self.get_node_lines(target_node)
                    symbols.append(
                        Symbol(
                            symbol_id=f"{file_path}::{iface_name}",
                            name=iface_name,
                            kind=SymbolKind.INTERFACE,
                            file_path=file_path,
                            start_line=start_l,
                            end_line=end_l,
                            start_byte=target_node.start_byte,
                            end_byte=target_node.end_byte,
                            signature=f"interface {iface_name}",
                            language=self.language_name,
                            source_code=self.get_node_text(target_node, source_bytes),
                        )
                    )
                return

            elif target_node.type == "type_alias_declaration":
                name_n = target_node.child_by_field_name("name")
                if name_n:
                    type_name = self.get_node_text(name_n, source_bytes)
                    start_l, end_l = self.get_node_lines(target_node)
                    symbols.append(
                        Symbol(
                            symbol_id=f"{file_path}::{type_name}",
                            name=type_name,
                            kind=SymbolKind.TYPE,
                            file_path=file_path,
                            start_line=start_l,
                            end_line=end_l,
                            start_byte=target_node.start_byte,
                            end_byte=target_node.end_byte,
                            signature=f"type {type_name}",
                            language=self.language_name,
                            source_code=self.get_node_text(target_node, source_bytes),
                        )
                    )
                return

            elif target_node.type == "class_declaration":
                name_n = target_node.child_by_field_name("name")
                if name_n:
                    class_name = self.get_node_text(name_n, source_bytes)
                    start_l, end_l = self.get_node_lines(target_node)
                    heritage = target_node.child_by_field_name("heritage") or [c for c in target_node.children if c.type == "class_heritage"]
                    sig = f"class {class_name}"
                    if heritage:
                        h_node = heritage if isinstance(heritage, Node) else heritage[0]
                        sig += " " + self.get_node_text(h_node, source_bytes)

                    symbols.append(
                        Symbol(
                            symbol_id=f"{file_path}::{class_name}",
                            name=class_name,
                            kind=SymbolKind.CLASS,
                            file_path=file_path,
                            start_line=start_l,
                            end_line=end_l,
                            start_byte=target_node.start_byte,
                            end_byte=target_node.end_byte,
                            signature=sig,
                            parent_symbol=parent_name,
                            language=self.language_name,
                            source_code=self.get_node_text(target_node, source_bytes),
                        )
                    )

                    body = target_node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            _traverse(child, parent_name=class_name)
                    return

            elif target_node.type == "function_declaration":
                name_n = target_node.child_by_field_name("name")
                if name_n:
                    fn_name = self.get_node_text(name_n, source_bytes)
                    start_l, end_l = self.get_node_lines(target_node)
                    params = target_node.child_by_field_name("parameters")
                    ret = target_node.child_by_field_name("return_type")

                    sig = f"function {fn_name}" + (self.get_node_text(params, source_bytes) if params else "()")
                    if ret:
                        sig += f": {self.get_node_text(ret, source_bytes)}"

                    full_name = f"{parent_name}.{fn_name}" if parent_name else fn_name
                    symbols.append(
                        Symbol(
                            symbol_id=f"{file_path}::{full_name}",
                            name=full_name,
                            kind=SymbolKind.FUNCTION,
                            file_path=file_path,
                            start_line=start_l,
                            end_line=end_l,
                            start_byte=target_node.start_byte,
                            end_byte=target_node.end_byte,
                            signature=sig,
                            return_type=self.get_node_text(ret, source_bytes) if ret else None,
                            parent_symbol=parent_name,
                            language=self.language_name,
                            source_code=self.get_node_text(target_node, source_bytes),
                        )
                    )
                    body = target_node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            _traverse(child, parent_name=full_name)
                    return

            elif target_node.type == "method_definition":
                name_n = target_node.child_by_field_name("name")
                if name_n:
                    fn_name = self.get_node_text(name_n, source_bytes)
                    start_l, end_l = self.get_node_lines(target_node)
                    params = target_node.child_by_field_name("parameters")
                    ret = target_node.child_by_field_name("return_type")

                    sig = f"{fn_name}" + (self.get_node_text(params, source_bytes) if params else "()")
                    if ret:
                        sig += f": {self.get_node_text(ret, source_bytes)}"

                    full_name = f"{parent_name}.{fn_name}" if parent_name else fn_name
                    symbols.append(
                        Symbol(
                            symbol_id=f"{file_path}::{full_name}",
                            name=full_name,
                            kind=SymbolKind.METHOD,
                            file_path=file_path,
                            start_line=start_l,
                            end_line=end_l,
                            start_byte=target_node.start_byte,
                            end_byte=target_node.end_byte,
                            signature=sig,
                            return_type=self.get_node_text(ret, source_bytes) if ret else None,
                            parent_symbol=parent_name,
                            language=self.language_name,
                            source_code=self.get_node_text(target_node, source_bytes),
                        )
                    )
                    body = target_node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            _traverse(child, parent_name=full_name)
                    return

            for child in target_node.children:
                _traverse(child, parent_name)

        _traverse(tree.root_node)
        return symbols

    def extract_imports(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[FileDependency]:
        """Extract TypeScript import statements."""
        deps: list[FileDependency] = []
        if not tree or not tree.root_node:
            return deps

        for node in tree.root_node.children:
            if node.type == "import_statement":
                start_l, _ = self.get_node_lines(node)
                source_node = node.child_by_field_name("source")
                source_val = self.get_node_text(source_node, source_bytes).strip("'\"") if source_node else ""

                imported: list[str] = []
                clause = [c for c in node.children if c.type in ("import_clause", "named_imports")]
                if clause:
                    for item in clause[0].children:
                        if item.type == "identifier":
                            imported.append(self.get_node_text(item, source_bytes))
                        elif item.type == "named_imports":
                            for spec in item.children:
                                if spec.type == "import_specifier":
                                    n = spec.child_by_field_name("name") or spec
                                    imported.append(self.get_node_text(n, source_bytes).split(" as ")[0].strip())

                target_file = source_val
                if not target_file.endswith((".ts", ".tsx", ".js", ".jsx")):
                    target_file += ".ts"

                deps.append(
                    FileDependency(
                        source_file=file_path,
                        target_file=target_file,
                        dependency_type="IMPORTS",
                        imported_symbols=imported,
                        line_number=start_l,
                        metadata={"raw": self.get_node_text(node, source_bytes)},
                    )
                )

        return deps

    def extract_references(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[SymbolReference]:
        """Extract TypeScript call references, extends (inheritance), and implements."""
        references: list[SymbolReference] = []
        if not tree or not tree.root_node:
            return references

        def _traverse(node: Node, current_symbol: str = "module"):
            enclosing = current_symbol

            target_node = node
            if node.type == "export_statement":
                inner = [c for c in node.children if c.type in ("class_declaration", "function_declaration", "interface_declaration")]
                if inner:
                    target_node = inner[0]

            if target_node.type == "class_declaration":
                name_n = target_node.child_by_field_name("name")
                if name_n:
                    enclosing = self.get_node_text(name_n, source_bytes)
                    heritage = [c for c in target_node.children if c.type == "class_heritage"]
                    if heritage:
                        start_l, _ = self.get_node_lines(target_node)
                        for h in heritage[0].children:
                            if h.type == "extends_clause":
                                for c in h.children:
                                    if c.type in ("identifier", "type_identifier"):
                                        references.append(
                                            SymbolReference(
                                                source_symbol=enclosing,
                                                target_symbol=self.get_node_text(c, source_bytes),
                                                source_file=file_path,
                                                line_number=start_l,
                                                reference_type=ReferenceType.INHERITANCE,
                                                resolved=False,
                                            )
                                        )
                            elif h.type == "implements_clause":
                                for c in h.children:
                                    if c.type in ("identifier", "type_identifier"):
                                        references.append(
                                            SymbolReference(
                                                source_symbol=enclosing,
                                                target_symbol=self.get_node_text(c, source_bytes),
                                                source_file=file_path,
                                                line_number=start_l,
                                                reference_type=ReferenceType.IMPLEMENTATION,
                                                resolved=False,
                                            )
                                        )

            elif target_node.type in ("function_declaration", "method_definition"):
                name_n = target_node.child_by_field_name("name")
                if name_n:
                    fn_name = self.get_node_text(name_n, source_bytes)
                    enclosing = f"{current_symbol}.{fn_name}" if current_symbol != "module" else fn_name

            elif target_node.type == "call_expression":
                fn_node = target_node.child_by_field_name("function")
                if fn_node:
                    fn_text = self.get_node_text(fn_node, source_bytes)
                    start_l, _ = self.get_node_lines(target_node)
                    target_name = fn_text.split(".")[-1].split("?")[-1]
                    references.append(
                        SymbolReference(
                            source_symbol=enclosing,
                            target_symbol=target_name,
                            source_file=file_path,
                            line_number=start_l,
                            reference_type=ReferenceType.CALL,
                            resolved=False,
                            metadata={"call": fn_text},
                        )
                    )

            for child in target_node.children:
                _traverse(child, enclosing)

        _traverse(tree.root_node)
        return references

    def find_enclosing_chunk(
        self, tree: Tree, source_bytes: bytes, line_number: int, file_path: str
    ) -> ASTChunk | None:
        """Find smallest semantic entity enclosing line_number."""
        if not tree or not tree.root_node:
            return None

        matching: list[Node] = []

        def _find(node: Node):
            start_l, end_l = self.get_node_lines(node)
            if start_l <= line_number <= end_l:
                if node.type in ("function_declaration", "method_definition", "class_declaration", "interface_declaration", "type_alias_declaration", "program"):
                    matching.append(node)
                for child in node.children:
                    _find(child)

        _find(tree.root_node)
        if not matching:
            return None

        def _rank(n: Node):
            start_l, end_l = self.get_node_lines(n)
            span = end_l - start_l
            weight = 1 if n.type in ("function_declaration", "method_definition") else (2 if n.type in ("class_declaration", "interface_declaration", "type_alias_declaration") else 3)
            return (weight, span)

        best = min(matching, key=_rank)
        start_l, end_l = self.get_node_lines(best)
        name_n = best.child_by_field_name("name")
        symbol_name = self.get_node_text(name_n, source_bytes) if name_n else file_path

        parent_name = None
        curr = best.parent
        while curr:
            if curr.type in ("class_declaration", "function_declaration", "interface_declaration"):
                p_name = curr.child_by_field_name("name")
                if p_name:
                    parent_name = self.get_node_text(p_name, source_bytes)
                    symbol_name = f"{parent_name}.{symbol_name}"
                    break
            curr = curr.parent

        chunk_id = hashlib.sha256(f"{file_path}:{start_l}:{end_l}:{symbol_name}".encode()).hexdigest()[:16]
        return ASTChunk(
            id=chunk_id,
            file_path=file_path,
            language=self.language_name,
            node_type=best.type,
            symbol_name=symbol_name,
            start_line=start_l,
            end_line=end_l,
            start_byte=best.start_byte,
            end_byte=best.end_byte,
            source_code=self.get_node_text(best, source_bytes),
            parent_symbol=parent_name,
            signature=f"{best.type} {symbol_name}",
        )

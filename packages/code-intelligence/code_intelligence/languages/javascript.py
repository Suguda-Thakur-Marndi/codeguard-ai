"""Tree-sitter language parser adapter for JavaScript."""

import hashlib

import tree_sitter_javascript as tsjavascript
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


class JavaScriptParser(LanguageParser):
    """JavaScript AST Analyzer utilizing Tree-sitter for semantic structure extraction."""

    language_name = "javascript"

    def __init__(self):
        self._language = Language(tsjavascript.language())
        self._parser = Parser(self._language)

    def parse(
        self, source_code: str | bytes, file_path: str = ""
    ) -> tuple[Tree | None, list[ParserDiagnostic]]:
        """Parse JavaScript source code into a Tree-sitter Tree."""
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
                    message=f"Failed to parse JavaScript file: {exc!s}",
                )
            )
            return None, diagnostics

    def extract_symbols(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[Symbol]:
        """Extract functions, classes, methods, and arrow functions."""
        symbols: list[Symbol] = []
        if not tree or not tree.root_node:
            return symbols

        def _traverse(node: Node, parent_name: str | None = None):
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    class_name = self.get_node_text(name_node, source_bytes)
                    start_l, end_l = self.get_node_lines(node)
                    heritage_node = node.child_by_field_name("heritage")
                    sig = f"class {class_name}"
                    if heritage_node:
                        sig += " " + self.get_node_text(heritage_node, source_bytes)

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
                        )
                    )

                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            _traverse(child, parent_name=class_name)
                    return

            elif node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    fn_name = self.get_node_text(name_node, source_bytes)
                    start_l, end_l = self.get_node_lines(node)
                    params_node = node.child_by_field_name("parameters")
                    sig = f"function {fn_name}" + (self.get_node_text(params_node, source_bytes) if params_node else "()")

                    kind = SymbolKind.FUNCTION
                    full_name = f"{parent_name}.{fn_name}" if parent_name else fn_name
                    symbol_id = f"{file_path}::{full_name}"

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
                            signature=sig,
                            parent_symbol=parent_name,
                            language=self.language_name,
                            source_code=self.get_node_text(node, source_bytes),
                        )
                    )
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            _traverse(child, parent_name=full_name)
                    return

            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    fn_name = self.get_node_text(name_node, source_bytes)
                    start_l, end_l = self.get_node_lines(node)
                    params_node = node.child_by_field_name("parameters")
                    sig = f"{fn_name}" + (self.get_node_text(params_node, source_bytes) if params_node else "()")

                    full_name = f"{parent_name}.{fn_name}" if parent_name else fn_name
                    symbol_id = f"{file_path}::{full_name}"

                    symbols.append(
                        Symbol(
                            symbol_id=symbol_id,
                            name=full_name,
                            kind=SymbolKind.METHOD,
                            file_path=file_path,
                            start_line=start_l,
                            end_line=end_l,
                            start_byte=node.start_byte,
                            end_byte=node.end_byte,
                            signature=sig,
                            parent_symbol=parent_name,
                            language=self.language_name,
                            source_code=self.get_node_text(node, source_bytes),
                        )
                    )
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            _traverse(child, parent_name=full_name)
                    return

            elif node.type in ("variable_declarator", "lexical_declaration"):
                # Handle const foo = () => {}
                if node.type == "variable_declarator":
                    name_n = node.child_by_field_name("name")
                    val_n = node.child_by_field_name("value")
                    if name_n and val_n and val_n.type in ("arrow_function", "function"):
                        fn_name = self.get_node_text(name_n, source_bytes)
                        start_l, end_l = self.get_node_lines(node)
                        params = val_n.child_by_field_name("parameters")
                        sig = f"const {fn_name} = " + (self.get_node_text(params, source_bytes) if params else "()") + " => ..."
                        full_name = f"{parent_name}.{fn_name}" if parent_name else fn_name
                        symbols.append(
                            Symbol(
                                symbol_id=f"{file_path}::{full_name}",
                                name=full_name,
                                kind=SymbolKind.FUNCTION,
                                file_path=file_path,
                                start_line=start_l,
                                end_line=end_l,
                                start_byte=node.start_byte,
                                end_byte=node.end_byte,
                                signature=sig,
                                parent_symbol=parent_name,
                                language=self.language_name,
                                source_code=self.get_node_text(node, source_bytes),
                            )
                        )

            for child in node.children:
                _traverse(child, parent_name)

        _traverse(tree.root_node)
        return symbols

    def extract_imports(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[FileDependency]:
        """Extract ES6 imports and CommonJS require() calls."""
        deps: list[FileDependency] = []
        if not tree or not tree.root_node:
            return deps

        def _traverse(node: Node):
            if node.type == "import_statement":
                start_l, _ = self.get_node_lines(node)
                source_node = node.child_by_field_name("source")
                source_val = self.get_node_text(source_node, source_bytes).strip("'\"") if source_node else ""

                imported: list[str] = []
                clause = node.child_by_field_name("clause") or [c for c in node.children if c.type in ("import_clause", "named_imports")]
                if clause:
                    clause_node = clause if isinstance(clause, Node) else clause[0]
                    for item in clause_node.children:
                        if item.type == "identifier":
                            imported.append(self.get_node_text(item, source_bytes))
                        elif item.type == "named_imports":
                            for spec in item.children:
                                if spec.type == "import_specifier":
                                    n = spec.child_by_field_name("name") or spec
                                    imported.append(self.get_node_text(n, source_bytes).split(" as ")[0].strip())

                target_file = source_val
                if not target_file.endswith((".js", ".ts", ".jsx", ".tsx")):
                    target_file += ".js"

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

            elif node.type == "call_expression":
                # require('./foo')
                fn = node.child_by_field_name("function")
                args = node.child_by_field_name("arguments")
                if fn and self.get_node_text(fn, source_bytes) == "require" and args and args.children:
                    start_l, _ = self.get_node_lines(node)
                    arg = [c for c in args.children if c.type == "string"]
                    if arg:
                        mod = self.get_node_text(arg[0], source_bytes).strip("'\"")
                        target_file = mod if mod.endswith((".js", ".ts")) else f"{mod}.js"
                        deps.append(
                            FileDependency(
                                source_file=file_path,
                                target_file=target_file,
                                dependency_type="REQUIRES",
                                imported_symbols=[],
                                line_number=start_l,
                                metadata={"type": "require"},
                            )
                        )

            for child in node.children:
                _traverse(child)

        _traverse(tree.root_node)
        return deps

    def extract_references(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[SymbolReference]:
        """Extract function/method call references and class inheritance."""
        references: list[SymbolReference] = []
        if not tree or not tree.root_node:
            return references

        def _traverse(node: Node, current_symbol: str = "module"):
            enclosing = current_symbol
            if node.type == "class_declaration":
                name_n = node.child_by_field_name("name")
                if name_n:
                    enclosing = self.get_node_text(name_n, source_bytes)
                    heritage = node.child_by_field_name("heritage")
                    if heritage:
                        start_l, _ = self.get_node_lines(node)
                        for c in heritage.children:
                            if c.type == "identifier":
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
            elif node.type in ("function_declaration", "method_definition"):
                name_n = node.child_by_field_name("name")
                if name_n:
                    fn_name = self.get_node_text(name_n, source_bytes)
                    enclosing = f"{current_symbol}.{fn_name}" if current_symbol != "module" else fn_name

            elif node.type == "call_expression":
                fn_node = node.child_by_field_name("function")
                if fn_node:
                    fn_text = self.get_node_text(fn_node, source_bytes)
                    start_l, _ = self.get_node_lines(node)
                    target_name = fn_text.split(".")[-1].split("?")[-1]
                    if target_name and target_name != "require":
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

            for child in node.children:
                _traverse(child, enclosing)

        _traverse(tree.root_node)
        return references

    def find_enclosing_chunk(
        self, tree: Tree, source_bytes: bytes, line_number: int, file_path: str
    ) -> ASTChunk | None:
        """Locate smallest semantic entity enclosing line_number."""
        if not tree or not tree.root_node:
            return None

        matching: list[Node] = []

        def _find(node: Node):
            start_l, end_l = self.get_node_lines(node)
            if start_l <= line_number <= end_l:
                if node.type in ("function_declaration", "method_definition", "class_declaration", "arrow_function", "program"):
                    matching.append(node)
                for child in node.children:
                    _find(child)

        _find(tree.root_node)
        if not matching:
            return None

        def _rank(n: Node):
            start_l, end_l = self.get_node_lines(n)
            span = end_l - start_l
            weight = 1 if n.type in ("function_declaration", "method_definition", "arrow_function") else (2 if n.type == "class_declaration" else 3)
            return (weight, span)

        best = min(matching, key=_rank)
        start_l, end_l = self.get_node_lines(best)
        name_n = best.child_by_field_name("name")
        symbol_name = self.get_node_text(name_n, source_bytes) if name_n else file_path

        parent_name = None
        curr = best.parent
        while curr:
            if curr.type in ("class_declaration", "function_declaration"):
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

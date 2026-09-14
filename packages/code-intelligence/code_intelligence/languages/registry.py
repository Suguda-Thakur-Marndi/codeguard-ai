"""Pluggable registry for language parsers."""

from code_intelligence.languages.base import LanguageParser
from code_intelligence.languages.javascript import JavaScriptParser
from code_intelligence.languages.python import PythonParser
from code_intelligence.languages.typescript import TypeScriptParser


class LanguageParserRegistry:
    """Registry coordinating language-specific Tree-sitter parsers by file extension."""

    def __init__(self):
        self._extension_map: dict[str, LanguageParser] = {}
        self._init_defaults()

    def _init_defaults(self):
        py_parser = PythonParser()
        js_parser = JavaScriptParser()
        ts_parser = TypeScriptParser(is_tsx=False)
        tsx_parser = TypeScriptParser(is_tsx=True)

        for ext in (".py", ".pyi"):
            self._extension_map[ext] = py_parser

        for ext in (".js", ".mjs", ".cjs"):
            self._extension_map[ext] = js_parser

        for ext in (".ts",):
            self._extension_map[ext] = ts_parser

        for ext in (".tsx", ".jsx"):
            self._extension_map[ext] = tsx_parser

    def register(self, extension: str, parser: LanguageParser) -> None:
        """Register a custom language parser for an extension."""
        ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        self._extension_map[ext] = parser

    def get_parser(self, file_path: str) -> LanguageParser | None:
        """Retrieve parser for a given file path based on its extension."""
        lower_path = file_path.lower()
        for ext, parser in self._extension_map.items():
            if lower_path.endswith(ext):
                return parser
        return None

    def is_supported(self, file_path: str) -> bool:
        """Check if a file extension is supported for AST parsing."""
        return self.get_parser(file_path) is not None


# Global singleton registry
default_registry = LanguageParserRegistry()

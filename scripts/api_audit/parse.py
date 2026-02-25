import tree_sitter_javascript as tsjs
from tree_sitter import Language, Parser

_JS_LANGUAGE = Language(tsjs.language())
_parser = Parser(_JS_LANGUAGE)


def parse_js(source: str):
    """Parse JavaScript source into a tree-sitter AST. Returns root node."""
    tree = _parser.parse(bytes(source, 'utf-8'))
    return tree.root_node

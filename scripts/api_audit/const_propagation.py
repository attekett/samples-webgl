"""Two-pass constant propagation for WebGL test file ASTs.

Pass 1: Collect all variable_declarator nodes, recording name and raw
         initializer node.
Pass 2: Resolve each initializer to a concrete value (str, list[str])
         or None if unresolvable. The two-pass approach handles forward
         references.
"""

from __future__ import annotations
from typing import Optional


def _walk(node, node_type: str) -> list:
    """Recursively collect all descendant nodes of the given type."""
    results = []
    if node.type == node_type:
        results.append(node)
    for child in node.children:
        results.extend(_walk(child, node_type))
    return results


def _resolve_node(node, declarations: dict, seen: set) -> Optional[str | list[str]]:
    """Resolve an initializer node to a value.

    Args:
        node: tree-sitter node (the initializer/value of a variable_declarator)
        declarations: mapping of variable name -> raw initializer node
        seen: set of variable names currently being resolved (cycle detection)

    Returns:
        str for gl.PROP, template strings, and chain-resolved identifiers;
        list[str] for arrays of string literals;
        None for unresolvable expressions.
    """
    if node is None:
        return None

    ntype = node.type

    # gl.PROPERTY member expression
    if ntype == 'member_expression':
        obj = node.child_by_field_name('object')
        prop = node.child_by_field_name('property')
        if obj and prop and obj.type == 'identifier' and obj.text.decode('utf-8') == 'gl':
            return f'gl.{prop.text.decode("utf-8")}'
        # Non-gl member expressions (e.g. canvas.getContext) are not resolvable
        return None

    # Identifier referencing another declaration -> follow chain
    if ntype == 'identifier':
        name = node.text.decode('utf-8')
        if name in seen:
            return None  # cycle
        if name in declarations:
            seen.add(name)
            return _resolve_node(declarations[name], declarations, seen)
        return None

    # Template string -> extract string_fragment text
    if ntype == 'template_string':
        fragments = [c for c in node.children if c.type == 'string_fragment']
        if fragments:
            return ''.join(f.text.decode('utf-8') for f in fragments)
        return ''

    # Array of string literals
    if ntype == 'array':
        strings = [c for c in node.children if c.type == 'string']
        if strings:
            values = []
            for s in strings:
                frags = [ch for ch in s.children if ch.type == 'string_fragment']
                if frags:
                    values.append(frags[0].text.decode('utf-8'))
            return values
        # Empty array or array with non-string elements
        return []

    # call_expression, new_expression, and other complex forms -> unresolvable
    return None


def resolve_constants(root) -> dict[str, str | list[str]]:
    """Two-pass constant resolution over a tree-sitter AST root node.

    Pass 1: Walk all variable_declarator nodes, collect name -> initializer node.
    Pass 2: Resolve each initializer. Forward references are handled because
            pass 1 collects everything before pass 2 resolves.

    Returns:
        dict mapping variable name to resolved value. Only includes entries
        where the value could be resolved (str or list[str]). Unresolvable
        declarations are omitted.
    """
    # Pass 1: collect all declarations
    declarators = _walk(root, 'variable_declarator')
    declarations: dict[str, object] = {}
    for decl in declarators:
        name_node = decl.child_by_field_name('name')
        value_node = decl.child_by_field_name('value')
        if name_node and value_node:
            name = name_node.text.decode('utf-8')
            declarations[name] = value_node

    # Pass 2: resolve each declaration
    result: dict[str, str | list[str]] = {}
    for name, value_node in declarations.items():
        resolved = _resolve_node(value_node, declarations, {name})
        if resolved is not None:
            result[name] = resolved

    return result

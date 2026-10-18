"""Two-pass constant propagation for WebGL test file ASTs.

Pass 1: Collect all variable_declarator nodes, recording name and raw
         initializer node.
Pass 2: Resolve each initializer to a concrete value (str, list[str])
         or None if unresolvable. The two-pass approach handles forward
         references.
"""

from __future__ import annotations
from typing import Optional


GL_NAMESPACES = {'gl', 'WebGL2RenderingContext', 'WebGLRenderingContext'}


def _walk(node, node_type: str) -> list:
    """Recursively collect all descendant nodes of the given type."""
    results = []
    if node.type == node_type:
        results.append(node)
    for child in node.children:
        results.extend(_walk(child, node_type))
    return results


def _resolve_node(node, declarations: dict, seen: set) -> Optional[str | list[str] | tuple[str, ...]]:
    """Resolve an initializer node to a value.

    Args:
        node: tree-sitter node (the initializer/value of a variable_declarator)
        declarations: mapping of variable name -> raw initializer node
        seen: set of variable names currently being resolved (cycle detection)

    Returns:
        str for gl.PROP, template strings, and chain-resolved identifiers;
        int for integer literals;
        list[str] for arrays of string literals;
        tuple[str, ...] of 'gl.X' for arrays of gl constants;
        None for unresolvable expressions.
    """
    if node is None:
        return None

    ntype = node.type

    # gl.PROPERTY member expression
    if ntype == 'member_expression':
        obj = node.child_by_field_name('object')
        prop = node.child_by_field_name('property')
        if obj and prop and obj.type == 'identifier' and obj.text.decode('utf-8') in GL_NAMESPACES:
            return f'gl.{prop.text.decode("utf-8")}'
        # Non-gl member expressions (e.g. canvas.getContext) are not resolvable
        return None

    # Integer literal (raw enum such as 0x8C8E); call_analysis maps it at GLenum params
    if ntype == 'number':
        try:
            return int(node.text.decode('utf-8'), 0)
        except ValueError:
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
        # Arrays of gl.X constants (or identifiers resolving to them) -> tuple
        elems = [c for c in node.children if c.type not in ('[', ']', ',')]
        if elems:
            names = []
            for e in elems:
                v = _resolve_node(e, declarations, set(seen))
                if not (isinstance(v, str) and v.startswith('gl.')):
                    return []
                names.append(v)
            return tuple(names)
        return []

    # textureViews[i % n] -> every candidate of the array
    if ntype == 'subscript_expression':
        v = _resolve_node(node.child_by_field_name('object'), declarations, set(seen))
        return v if isinstance(v, tuple) else None

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


_ITERATION_METHODS = {'forEach', 'map', 'filter', 'some', 'every', 'find'}
_FUNCTION_TYPES = {'arrow_function', 'function_expression', 'function_declaration',
                   'function', 'generator_function', 'generator_function_declaration',
                   'method_definition'}


def _constant_tuple(node, consts: dict) -> tuple:
    """'gl.X' tuple an array literal or identifier stands for, else ()."""
    if node is None:
        return ()
    if node.type == 'identifier':
        v = consts.get(node.text.decode('utf-8'))
    elif node.type == 'array':
        v = _resolve_node(node, {}, set())
    else:
        return ()
    return v if isinstance(v, tuple) else ()


def _binds(params, name: str) -> bool:
    return any(i.text.decode('utf-8') == name for i in _walk(params, 'identifier'))


def loop_bound_constants(ident_node, consts: dict) -> tuple[str, ...]:
    """Constant names (no 'gl.' prefix) a loop/callback variable ranges over.

    Stops at the nearest binding of the name; any binding that is not a
    for-of or an array-method callback over a gl-constant array yields ().
    """
    name = ident_node.text.decode('utf-8')
    child, node = ident_node, ident_node.parent
    while node is not None:
        t = node.type
        if t == 'for_in_statement':
            left = node.child_by_field_name('left')
            if left is not None and child.id != left.id and _binds(left, name):
                op = node.child_by_field_name('operator')
                if (left.type == 'identifier' and op is not None and op.type == 'of'
                        and child.id == node.child_by_field_name('body').id):
                    return tuple(c[3:] for c in _constant_tuple(
                        node.child_by_field_name('right'), consts))
                return ()
        elif t == 'for_statement':
            init = node.child_by_field_name('initializer')
            if init is not None and child.id == node.child_by_field_name('body').id and _binds(init, name):
                return ()
        elif t in _FUNCTION_TYPES:
            params = node.child_by_field_name('parameters') or node.child_by_field_name('parameter')
            if params is not None and _binds(params, name):
                first = node.child_by_field_name('parameter')
                if first is None and params.type == 'formal_parameters':
                    first = next((c for c in params.children if c.type not in ('(', ')', ',')), None)
                if (first is None or first.type != 'identifier'
                        or first.text.decode('utf-8') != name
                        or t not in ('arrow_function', 'function_expression')):
                    return ()
                args = node.parent
                call = args.parent if args is not None else None
                fn = call.child_by_field_name('function') if call is not None and call.type == 'call_expression' else None
                if args is None or args.type != 'arguments' or fn is None or fn.type != 'member_expression':
                    return ()
                meth = fn.child_by_field_name('property')
                if meth is None or meth.text.decode('utf-8') not in _ITERATION_METHODS:
                    return ()
                return tuple(c[3:] for c in _constant_tuple(fn.child_by_field_name('object'), consts))
        child, node = node, node.parent
    return ()

"""Context detection for WebGL test files.

Detects WebGL context variables, API version, extensions (3 patterns),
and helper function context tracking from a tree-sitter AST.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContextInfo:
    api_version: str = 'unknown'
    context_vars: set = field(default_factory=set)
    extensions: set = field(default_factory=set)
    extension_aliases: dict = field(default_factory=dict)
    helper_functions: dict = field(default_factory=dict)


def _walk(node, node_type: str) -> list:
    """Recursively collect all descendant nodes of the given type."""
    results = []
    if node.type == node_type:
        results.append(node)
    for child in node.children:
        results.extend(_walk(child, node_type))
    return results


def _get_string_value(node) -> Optional[str]:
    """Extract the string value from a tree-sitter string node.

    String nodes contain string_fragment children with the actual text.
    """
    if node.type != 'string':
        return None
    for child in node.children:
        if child.type == 'string_fragment':
            return child.text.decode('utf-8')
    return ''


def _is_get_context_call(node) -> Optional[str]:
    """Check if a call_expression is a .getContext() call.

    Returns the context string argument (e.g. 'webgl2') or None.
    """
    if node.type != 'call_expression':
        return None
    callee = node.child_by_field_name('function')
    if callee is None or callee.type != 'member_expression':
        return None
    prop = callee.child_by_field_name('property')
    if prop is None or prop.text.decode('utf-8') != 'getContext':
        return None
    args = node.child_by_field_name('arguments')
    if args is None:
        return None
    for child in args.children:
        if child.type == 'string':
            return _get_string_value(child)
    return None


def _is_get_extension_call(node) -> Optional[str]:
    """Check if a call_expression is a .getExtension() call.

    Returns the extension name string argument or None.
    If the argument is not a string literal (e.g. a variable reference),
    returns None.
    """
    if node.type != 'call_expression':
        return None
    callee = node.child_by_field_name('function')
    if callee is None or callee.type != 'member_expression':
        return None
    prop = callee.child_by_field_name('property')
    if prop is None or prop.text.decode('utf-8') != 'getExtension':
        return None
    args = node.child_by_field_name('arguments')
    if args is None:
        return None
    for child in args.children:
        if child.type == 'string':
            return _get_string_value(child)
    return None


def _detect_context_vars(root) -> tuple[set[str], str]:
    """Detect context variable names and API version.

    Walks variable_declarator nodes looking for getContext calls.
    Handles the fallback pattern: getContext('webgl2') || getContext('webgl').

    Returns:
        (context_vars, api_version) tuple.
    """
    context_vars: set[str] = set()
    api_version = 'unknown'

    for decl in _walk(root, 'variable_declarator'):
        name_node = decl.child_by_field_name('name')
        value_node = decl.child_by_field_name('value')
        if name_node is None or value_node is None:
            continue

        var_name = name_node.text.decode('utf-8')

        # Direct getContext call: const gl = canvas.getContext('webgl2')
        ctx_str = _is_get_context_call(value_node)
        if ctx_str is not None:
            context_vars.add(var_name)
            if ctx_str in ('webgl2', 'webgl'):
                api_version = ctx_str
            continue

        # Fallback pattern: canvas.getContext('webgl2') || canvas.getContext('webgl')
        if value_node.type == 'binary_expression':
            op_text = None
            for child in value_node.children:
                if child.type == '||':
                    op_text = '||'
                    break
            if op_text != '||':
                continue

            left = value_node.child_by_field_name('left')
            right = value_node.child_by_field_name('right')
            left_ctx = _is_get_context_call(left) if left else None
            right_ctx = _is_get_context_call(right) if right else None

            if left_ctx is not None or right_ctx is not None:
                context_vars.add(var_name)
                # If both sides are getContext with different versions, mark as fallback
                if left_ctx and right_ctx and left_ctx != right_ctx:
                    versions = {left_ctx, right_ctx}
                    if 'webgl2' in versions and 'webgl' in versions:
                        api_version = 'webgl1-capable'
                elif left_ctx:
                    api_version = left_ctx
                elif right_ctx:
                    api_version = right_ctx

    return context_vars, api_version


def _detect_extensions(root, resolved_consts: dict, context_vars: set[str]) -> tuple[set[str], dict[str, str]]:
    """Detect extensions from three patterns.

    Pattern 1 - Direct assignment:
        const ext = gl.getExtension('OES_vertex_array_object');
        → Records extension AND creates alias ext → OES_vertex_array_object

    Pattern 2 - Bare enable (expression statement):
        gl.getExtension('OES_standard_derivatives');
        → Records extension, no alias

    Pattern 3 - Array forEach:
        REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));
        → Resolves array from resolved_consts, records each string element

    Returns:
        (extensions, extension_aliases) tuple.
    """
    extensions: set[str] = set()
    extension_aliases: dict[str, str] = {}

    # Pattern 1: Direct assignment via variable_declarator
    for decl in _walk(root, 'variable_declarator'):
        name_node = decl.child_by_field_name('name')
        value_node = decl.child_by_field_name('value')
        if name_node is None or value_node is None:
            continue
        ext_name = _is_get_extension_call(value_node)
        if ext_name is not None:
            var_name = name_node.text.decode('utf-8')
            extensions.add(ext_name)
            extension_aliases[var_name] = ext_name

    # Pattern 2: Bare enable (expression_statement containing getExtension call)
    for expr_stmt in _walk(root, 'expression_statement'):
        for child in expr_stmt.children:
            if child.type == 'call_expression':
                ext_name = _is_get_extension_call(child)
                if ext_name is not None:
                    extensions.add(ext_name)

    # Pattern 3: Array forEach with getExtension
    # Look for: IDENTIFIER.forEach(param => CONTEXT.getExtension(param))
    for call in _walk(root, 'call_expression'):
        callee = call.child_by_field_name('function')
        if callee is None or callee.type != 'member_expression':
            continue
        prop = callee.child_by_field_name('property')
        if prop is None or prop.text.decode('utf-8') != 'forEach':
            continue
        obj = callee.child_by_field_name('object')
        if obj is None or obj.type != 'identifier':
            continue
        array_name = obj.text.decode('utf-8')

        # Get the resolved array value
        resolved = resolved_consts.get(array_name)
        if not isinstance(resolved, list):
            continue

        # Verify the callback calls getExtension
        args = call.child_by_field_name('arguments')
        if args is None:
            continue
        has_get_extension = False
        for arrow in _walk(args, 'arrow_function'):
            for inner_call in _walk(arrow, 'call_expression'):
                inner_callee = inner_call.child_by_field_name('function')
                if inner_callee and inner_callee.type == 'member_expression':
                    inner_prop = inner_callee.child_by_field_name('property')
                    if inner_prop and inner_prop.text.decode('utf-8') == 'getExtension':
                        has_get_extension = True
                        break
            if has_get_extension:
                break

        if has_get_extension:
            for ext_str in resolved:
                if isinstance(ext_str, str) and ext_str:
                    extensions.add(ext_str)

    return extensions, extension_aliases


def _detect_helper_functions(root, context_vars: set[str]) -> dict[str, list[str]]:
    """Detect helper functions that accept a context variable as parameter.

    Looks for function_declaration nodes where any formal parameter name
    matches a known context variable name.

    Returns:
        dict mapping function name to list of parameter names that match
        context variables.
    """
    helpers: dict[str, list[str]] = {}

    for func in _walk(root, 'function_declaration'):
        # Get function name
        name_node = None
        for child in func.children:
            if child.type == 'identifier':
                name_node = child
                break
        if name_node is None:
            continue
        func_name = name_node.text.decode('utf-8')

        # Get formal parameters
        params_node = None
        for child in func.children:
            if child.type == 'formal_parameters':
                params_node = child
                break
        if params_node is None:
            continue

        matching_params = []
        for param in params_node.children:
            if param.type == 'identifier':
                param_name = param.text.decode('utf-8')
                if param_name in context_vars:
                    matching_params.append(param_name)

        if matching_params:
            helpers[func_name] = matching_params

    return helpers


def detect_context(root_node, resolved_consts: dict) -> ContextInfo:
    """Detect WebGL context, extensions, and helper functions from AST.

    Args:
        root_node: tree-sitter AST root node.
        resolved_consts: resolved constants from const_propagation.resolve_constants().

    Returns:
        ContextInfo dataclass with detected information.
    """
    info = ContextInfo()

    # Step 1: Detect context variables and API version
    context_vars, api_version = _detect_context_vars(root_node)
    info.context_vars = context_vars
    info.api_version = api_version

    # Step 2: Detect extensions (3 patterns)
    extensions, extension_aliases = _detect_extensions(
        root_node, resolved_consts, context_vars
    )
    info.extensions = extensions
    info.extension_aliases = extension_aliases

    # Step 3: Detect helper functions
    info.helper_functions = _detect_helper_functions(root_node, context_vars)

    return info

"""Convention lint: detect patterns the auditor cannot fully track.

Checks for computed property access, destructuring of context objects,
concatenated shader sources, and multi-level helper indirection.
"""

from __future__ import annotations


def _walk(node, node_type: str) -> list:
    """Recursively collect all descendant nodes of the given type."""
    results = []
    if node.type == node_type:
        results.append(node)
    for child in node.children:
        results.extend(_walk(child, node_type))
    return results


def _node_text(node) -> str:
    """Get the text of a node as a string."""
    return node.text.decode('utf-8')


def _check_computed_property(root, context_vars: set) -> list[str]:
    """Detect computed property access on context variables.

    Pattern: gl[methodName](...) -- subscript_expression where the object
    is an identifier in context_vars.
    """
    warnings = []
    for sub in _walk(root, 'subscript_expression'):
        obj = sub.child_by_field_name('object')
        if obj is None or obj.type != 'identifier':
            continue
        if _node_text(obj) in context_vars:
            idx = sub.child_by_field_name('index')
            idx_text = _node_text(idx) if idx else '?'
            warnings.append(
                f"Computed property access on WebGL context: "
                f"{_node_text(obj)}[{idx_text}]"
            )
    return warnings


def _check_destructuring(root, context_vars: set) -> list[str]:
    """Detect destructuring of context objects.

    Pattern: const { DEPTH_TEST } = gl -- variable_declarator where name
    is object_pattern and value is an identifier in context_vars.
    """
    warnings = []
    for decl in _walk(root, 'variable_declarator'):
        name_node = decl.child_by_field_name('name')
        value_node = decl.child_by_field_name('value')
        if name_node is None or value_node is None:
            continue
        if name_node.type != 'object_pattern':
            continue
        if value_node.type != 'identifier':
            continue
        if _node_text(value_node) in context_vars:
            warnings.append(
                f"Destructuring of context object: "
                f"{{ ... }} = {_node_text(value_node)}"
            )
    return warnings


def _check_concatenated_shader(root, context_vars: set) -> list[str]:
    """Detect concatenated shader source arguments.

    Pattern: gl.shaderSource(s, expr + expr) -- call_expression where
    callee is member_expression with property 'shaderSource' on a context
    var, and the second argument is a binary_expression with '+'.
    """
    warnings = []
    for call in _walk(root, 'call_expression'):
        callee = call.child_by_field_name('function')
        if callee is None or callee.type != 'member_expression':
            continue
        obj = callee.child_by_field_name('object')
        prop = callee.child_by_field_name('property')
        if obj is None or prop is None:
            continue
        if obj.type != 'identifier' or _node_text(obj) not in context_vars:
            continue
        if _node_text(prop) != 'shaderSource':
            continue

        # Get argument nodes (skip parens and commas)
        args_node = call.child_by_field_name('arguments')
        if args_node is None:
            continue
        arg_nodes = [c for c in args_node.children if c.type not in ('(', ')', ',')]

        # Check if second argument (index 1) is a binary_expression with '+'
        if len(arg_nodes) >= 2:
            second_arg = arg_nodes[1]
            if second_arg.type == 'binary_expression':
                has_plus = any(c.type == '+' for c in second_arg.children)
                if has_plus:
                    warnings.append(
                        "Concatenated shader source in shaderSource() call"
                    )
    return warnings


def _check_multilevel_indirection(root, context_vars: set) -> list[str]:
    """Detect multi-level helper function indirection.

    Algorithm:
    1. Find all function_declaration nodes where any formal parameter name
       is in context_vars.
    2. For each such function, check if its body contains a call to another
       such function.
    3. If so, flag as multi-level indirection.
    """
    # Step 1: Build set of helper function names (functions with context param)
    helper_funcs = {}  # name -> function_declaration node
    for func in _walk(root, 'function_declaration'):
        name_node = None
        params_node = None
        for child in func.children:
            if child.type == 'identifier' and name_node is None:
                name_node = child
            elif child.type == 'formal_parameters':
                params_node = child

        if name_node is None or params_node is None:
            continue

        func_name = _node_text(name_node)
        has_context_param = False
        for param in params_node.children:
            if param.type == 'identifier' and _node_text(param) in context_vars:
                has_context_param = True
                break

        if has_context_param:
            helper_funcs[func_name] = func

    if len(helper_funcs) < 2:
        return []

    # Step 2: For each helper, check if it calls another helper
    warnings = []
    helper_names = set(helper_funcs.keys())

    for func_name, func_node in helper_funcs.items():
        # Find the statement_block (body)
        body = None
        for child in func_node.children:
            if child.type == 'statement_block':
                body = child
                break
        if body is None:
            continue

        # Look for call_expression nodes in the body where the callee
        # is an identifier matching another helper function
        for call in _walk(body, 'call_expression'):
            callee = call.child_by_field_name('function')
            if callee is None or callee.type != 'identifier':
                continue
            called_name = _node_text(callee)
            if called_name in helper_names and called_name != func_name:
                warnings.append(
                    f"Multi-level indirection: {func_name}() calls "
                    f"{called_name}(), both accept context parameter"
                )

    return warnings


def check_conventions(root_node, context_vars: set) -> list[str]:
    """Check for patterns the auditor cannot track. Returns warning strings.

    Detects:
    - Computed property access on context (gl[name])
    - Destructuring of context object (const { X } = gl)
    - Concatenated shader source strings
    - Multi-level helper function indirection

    Args:
        root_node: tree-sitter AST root node.
        context_vars: set of known WebGL context variable names.

    Returns:
        List of warning strings (empty if no issues found).
    """
    warnings = []
    warnings.extend(_check_computed_property(root_node, context_vars))
    warnings.extend(_check_destructuring(root_node, context_vars))
    warnings.extend(_check_concatenated_shader(root_node, context_vars))
    warnings.extend(_check_multilevel_indirection(root_node, context_vars))
    return warnings

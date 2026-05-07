"""GLSL builtin extraction from shader sources in WebGL test files.

Extracts shader source code from shaderSource() calls (both direct and
via helper functions), strips GLSL comments, and matches against the
known GLSL builtin names from the API surface definition.
"""

from __future__ import annotations

import re
from typing import Optional


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


def _get_arg_nodes(arguments_node) -> list:
    """Extract actual argument nodes from an arguments node, skipping parens and commas."""
    return [c for c in arguments_node.children if c.type not in ('(', ')', ',')]


def strip_glsl_comments(source: str) -> str:
    """Remove // and /* */ comments from GLSL source."""
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    source = re.sub(r'//[^\n]*', '', source)
    return source


def _match_builtins(shader_source: str, builtin_names: list[str]) -> set[str]:
    """Match GLSL builtins using word-boundary regex."""
    found = set()
    for name in builtin_names:
        if re.search(rf'\b{re.escape(name)}\s*\(', shader_source):
            found.add(name)
    return found


def _match_variables(shader_source: str, variable_names: list[str]) -> set[str]:
    """Match GLSL built-in variables (gl_VertexID, gl_Position, etc.).

    Variables are matched by word-boundary alone — they are never followed
    by `(`, which distinguishes them from function-style builtins.
    """
    found = set()
    for name in variable_names:
        # Forbid `(` after the name to avoid colliding with any same-named call
        if re.search(rf'\b{re.escape(name)}\b(?!\s*\()', shader_source):
            found.add(name)
    return found


def _flatten_builtin_names(surface: dict) -> list[str]:
    """Flatten all GLSL builtin names from surface['glsl_builtins']."""
    glsl_section = surface.get('glsl_builtins', {})
    names = []
    for category_names in glsl_section.values():
        names.extend(category_names)
    return names


def _flatten_variable_names(surface: dict) -> list[str]:
    """Flatten all GLSL built-in variable names from surface['glsl_builtin_variables']."""
    section = surface.get('glsl_builtin_variables', {})
    names = []
    for category_names in section.values():
        names.extend(category_names)
    return names


def _resolve_shader_arg(arg_node, consts: dict) -> Optional[str]:
    """Resolve a shader source argument to its string value.

    Handles:
    - identifier: look up in consts dict
    - template_string: extract string_fragment children
    """
    if arg_node.type == 'identifier':
        name = _node_text(arg_node)
        resolved = consts.get(name)
        if isinstance(resolved, str):
            return resolved
        return None

    if arg_node.type == 'template_string':
        fragments = [c for c in arg_node.children if c.type == 'string_fragment']
        if fragments:
            return ''.join(f.text.decode('utf-8') for f in fragments)
        return ''

    if arg_node.type == 'string':
        fragments = [c for c in arg_node.children if c.type == 'string_fragment']
        if fragments:
            return fragments[0].text.decode('utf-8')
        return ''

    return None


def _get_formal_params(func_node) -> list[str]:
    """Get formal parameter names from a function_declaration node."""
    params_node = None
    for child in func_node.children:
        if child.type == 'formal_parameters':
            params_node = child
            break
    if params_node is None:
        return []
    return [_node_text(p) for p in params_node.children if p.type == 'identifier']


def _get_function_name(func_node) -> Optional[str]:
    """Get the name of a function_declaration node."""
    for child in func_node.children:
        if child.type == 'identifier':
            return _node_text(child)
    return None


def _collect_direct_shader_sources(root_node, context_vars: set, consts: dict,
                                    helper_functions: dict | None = None) -> list[str]:
    """Collect shader sources from direct gl.shaderSource(shader, source) calls.

    Only skips calls inside known helper function bodies (they are handled
    separately by helper tracing). Calls inside non-helper functions like
    main() are collected normally.
    """
    sources = []
    helper_names = set(helper_functions or {})

    for call in _walk(root_node, 'call_expression'):
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

        # Skip only if inside a known helper function (not any function)
        if helper_names:
            parent = call.parent
            inside_helper = False
            while parent is not None:
                if parent.type == 'function_declaration':
                    fname = _get_function_name(parent)
                    if fname in helper_names:
                        inside_helper = True
                    break
                parent = parent.parent
            if inside_helper:
                continue

        # Get the second argument (index 1) - the shader source
        args_node = call.child_by_field_name('arguments')
        if args_node is None:
            continue
        arg_nodes = _get_arg_nodes(args_node)
        if len(arg_nodes) < 2:
            continue

        source_arg = arg_nodes[1]
        resolved = _resolve_shader_arg(source_arg, consts)
        if resolved is not None:
            sources.append(resolved)

    return sources


def _collect_helper_shader_sources(root_node, ctx, consts: dict) -> list[str]:
    """Collect shader sources from helper functions that wrap shaderSource.

    For each helper function detected by context.detect_context():
    1. Find the shaderSource call inside the function body
    2. Identify which formal parameter is used as the source argument
    3. Find all call sites of the helper function
    4. Resolve the corresponding argument at each call site
    """
    sources = []
    helper_functions = ctx.helper_functions
    context_vars = ctx.context_vars

    if not helper_functions:
        return sources

    # Build a map of function_declaration nodes by name
    func_decls = {}
    for func in _walk(root_node, 'function_declaration'):
        name = _get_function_name(func)
        if name and name in helper_functions:
            func_decls[name] = func

    for func_name, func_node in func_decls.items():
        formal_params = _get_formal_params(func_node)

        # Find shaderSource calls inside this function
        for call in _walk(func_node, 'call_expression'):
            callee = call.child_by_field_name('function')
            if callee is None or callee.type != 'member_expression':
                continue
            prop = callee.child_by_field_name('property')
            if prop is None or _node_text(prop) != 'shaderSource':
                continue

            # Get the source argument (2nd arg, index 1)
            args_node = call.child_by_field_name('arguments')
            if args_node is None:
                continue
            arg_nodes = _get_arg_nodes(args_node)
            if len(arg_nodes) < 2:
                continue

            source_arg = arg_nodes[1]
            if source_arg.type != 'identifier':
                continue

            param_name = _node_text(source_arg)

            # Find which formal parameter index this corresponds to
            if param_name not in formal_params:
                continue
            param_index = formal_params.index(param_name)

            # Now find all call sites of this helper function in the AST
            for call_site in _walk(root_node, 'call_expression'):
                site_callee = call_site.child_by_field_name('function')
                if site_callee is None:
                    continue

                # Match direct function calls: createShader(...)
                if site_callee.type == 'identifier' and _node_text(site_callee) == func_name:
                    pass
                else:
                    continue

                # Skip calls inside the function declaration itself
                parent = call_site.parent
                inside_self = False
                while parent is not None:
                    if parent is func_node:
                        inside_self = True
                        break
                    parent = parent.parent
                if inside_self:
                    continue

                # Get the argument at param_index
                site_args_node = call_site.child_by_field_name('arguments')
                if site_args_node is None:
                    continue
                site_arg_nodes = _get_arg_nodes(site_args_node)
                if param_index >= len(site_arg_nodes):
                    continue

                actual_arg = site_arg_nodes[param_index]
                resolved = _resolve_shader_arg(actual_arg, consts)
                if resolved is not None:
                    sources.append(resolved)

    return sources


def _collect_all_shader_sources(root_node, ctx, consts: dict) -> list[str]:
    """Collect every shader source string referenced by the test file."""
    sources = _collect_direct_shader_sources(
        root_node, ctx.context_vars, consts, ctx.helper_functions
    )
    sources.extend(_collect_helper_shader_sources(root_node, ctx, consts))
    return sources


def extract_glsl_variables(root_node, ctx, consts: dict, surface: dict,
                            extra_variables: list[str] | None = None) -> set[str]:
    """Extract GLSL built-in variables (gl_*) from shader sources.

    Args:
        root_node: tree-sitter AST root node.
        ctx: ContextInfo from context.detect_context().
        consts: resolved constants from const_propagation.resolve_constants().
        surface: API surface dict.
        extra_variables: Optional list of additional variable names to scan for.

    Returns:
        Set of matched GLSL built-in variable names found in shader sources.
    """
    all_var_names = _flatten_variable_names(surface)
    if extra_variables:
        all_var_names = list(set(all_var_names) | set(extra_variables))
    if not all_var_names:
        return set()

    sources = _collect_all_shader_sources(root_node, ctx, consts)
    result = set()
    for source in sources:
        stripped = strip_glsl_comments(source)
        result |= _match_variables(stripped, all_var_names)
    return result


def extract_glsl_builtins(root_node, ctx, consts: dict, surface: dict,
                          extra_builtins: list[str] | None = None) -> set[str]:
    """Extract GLSL builtins from shader sources in the file.

    Args:
        root_node: tree-sitter AST root node.
        ctx: ContextInfo from context.detect_context().
        consts: resolved constants from const_propagation.resolve_constants().
        surface: API surface dict (test_surface.json structure).
        extra_builtins: Optional list of additional builtin names to scan for
            (e.g. category-only builtins not in the surface definition).

    Returns:
        Set of matched GLSL builtin names found in shader sources.
    """
    all_builtin_names = _flatten_builtin_names(surface)
    if extra_builtins:
        all_builtin_names = list(set(all_builtin_names) | set(extra_builtins))
    if not all_builtin_names:
        return set()

    context_vars = ctx.context_vars

    # Collect shader sources from direct shaderSource calls
    shader_sources = _collect_direct_shader_sources(
        root_node, context_vars, consts, ctx.helper_functions
    )

    # Collect shader sources from helper function call sites
    shader_sources.extend(_collect_helper_shader_sources(root_node, ctx, consts))

    # Strip GLSL comments and match builtins across all shader sources
    result = set()
    for source in shader_sources:
        stripped = strip_glsl_comments(source)
        result |= _match_builtins(stripped, all_builtin_names)

    return result

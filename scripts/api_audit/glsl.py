"""GLSL builtin extraction from shader sources in WebGL test files.

Extracts shader source code from shaderSource() calls (both direct and
via helper functions), strips GLSL comments, and matches against the
known GLSL builtin names from the API surface definition.
"""

from __future__ import annotations

import codecs
import re
from typing import Optional

from api_audit.const_propagation import collect_declarations
from api_audit.context import is_context_receiver


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


def _defines(shader_source: str, name: str) -> bool:
    """True when the source defines or prototypes `name` (ESSL 3.00 forbids redefining builtins)."""
    return bool(re.search(
        rf'\b(?:void|float|int|uint|bool|[iub]?vec[234]|mat[234](?:x[234])?)\s+{re.escape(name)}\s*\(',
        shader_source))


def _match_builtins(shader_source: str, builtin_names: list[str]) -> set[str]:
    """Match GLSL builtins using word-boundary regex, skipping user-defined names."""
    found = set()
    for name in builtin_names:
        if re.search(rf'\b{re.escape(name)}\s*\(', shader_source) and not _defines(shader_source, name):
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


SHADER_MARKER = re.compile(r'#version|\bvoid\s+main\s*\(')


def _decode_escape(esc: str) -> str:
    try:
        return codecs.decode(esc, 'unicode_escape')
    except UnicodeDecodeError:
        return esc[1:]


def _render_leaf(node, consts: dict) -> str:
    """Render a non-literal operand: a known constant's text, else ''."""
    if node.type == 'identifier':
        v = consts.get(_node_text(node))
        return str(v) if isinstance(v, (str, int, float)) else ''
    if node.type == 'number':
        return _node_text(node)
    return ''


def _render_operand(node, consts: dict) -> str:
    if node.type in ('string', 'template_string', 'binary_expression', 'parenthesized_expression'):
        r = render_js_string(node, consts)
        return r if r is not None else ''
    return _render_leaf(node, consts)


def render_js_string(node, consts: dict, decls: dict | None = None,
                     _seen: frozenset = frozenset()) -> Optional[str]:
    """Render a JS string, template or '+' concatenation to text, else None.

    Escapes are decoded; ${} substitutions and non-literal '+' operands
    render as the text of a known constant, otherwise as ''.
    """
    t = node.type
    if t in ('string', 'template_string'):
        parts = []
        for c in node.children:
            if c.type == 'string_fragment':
                parts.append(_node_text(c))
            elif c.type == 'escape_sequence':
                parts.append(_decode_escape(_node_text(c)))
            elif c.type == 'template_substitution':
                expr = next((e for e in c.children if e.type not in ('${', '}')), None)
                if expr is not None and expr.type == 'identifier':
                    parts.append(_render_leaf(expr, consts))
        return ''.join(parts)
    if t == 'parenthesized_expression':
        inner = next((c for c in node.children if c.type not in ('(', ')')), None)
        return render_js_string(inner, consts, decls, _seen) if inner is not None else None
    if t == 'binary_expression':
        op = node.child_by_field_name('operator')
        if op is None or op.type != '+':
            return None
        return (_render_operand(node.child_by_field_name('left'), consts)
                + _render_operand(node.child_by_field_name('right'), consts))
    if t == 'identifier' and decls:
        name = _node_text(node)
        if name in decls and name not in _seen:
            return render_js_string(decls[name], consts, decls, _seen | {name})
    return None


def collect_literal_shader_sources(root, consts: dict) -> list[str]:
    """Every string/template/'+' literal in the tree that looks like GLSL."""
    found: list[str] = []

    def visit(node):
        if node.type in ('string', 'template_string', 'binary_expression'):
            text = render_js_string(node, consts)
            if text is not None and SHADER_MARKER.search(text):
                found.append(text)
                return
        for c in node.children:
            visit(c)

    visit(root)
    return found


def _resolve_shader_arg(arg_node, consts: dict, decls: dict | None = None) -> Optional[str]:
    """Resolve a shader source argument to its string value."""
    if arg_node.type in ('identifier', 'string', 'template_string', 'binary_expression',
                         'parenthesized_expression'):
        rendered = render_js_string(arg_node, consts, decls)
        if rendered is not None:
            return rendered
    if arg_node.type == 'identifier':
        resolved = consts.get(_node_text(arg_node))
        if isinstance(resolved, str):
            return resolved
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


def _collect_direct_shader_sources(root_node, ctx, consts: dict,
                                    helper_functions: dict | None = None,
                                    decls: dict | None = None) -> list[str]:
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
        if obj.type != 'identifier' or not is_context_receiver(obj, ctx):
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
        resolved = _resolve_shader_arg(source_arg, consts, decls)
        if resolved is not None:
            sources.append(resolved)

    return sources


def _collect_helper_shader_sources(root_node, ctx, consts: dict, decls: dict | None = None) -> list[str]:
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
                resolved = _resolve_shader_arg(actual_arg, consts, decls)
                if resolved is not None:
                    sources.append(resolved)

    return sources


def collect_shader_sources(root_node, ctx, consts: dict) -> list[str]:
    """Every shader source in the file, comment-stripped and deduplicated.

    Combines shaderSource() calls (direct and via helpers) with a scan for
    GLSL-looking literals, which catches sources the call tracing cannot follow.
    """
    decls = collect_declarations(root_node)
    sources = _collect_direct_shader_sources(
        root_node, ctx, consts, ctx.helper_functions, decls
    )
    sources.extend(_collect_helper_shader_sources(root_node, ctx, consts, decls))
    sources.extend(collect_literal_shader_sources(root_node, consts))
    return list(dict.fromkeys(strip_glsl_comments(s) for s in sources))


def extract_glsl_variables(root_node, ctx, consts: dict, surface: dict,
                            extra_variables: list[str] | None = None,
                            sources: list[str] | None = None) -> set[str]:
    """Extract GLSL built-in variables (gl_*) from shader sources.

    Args:
        root_node: tree-sitter AST root node.
        ctx: ContextInfo from context.detect_context().
        consts: resolved constants from const_propagation.resolve_constants().
        surface: API surface dict.
        extra_variables: Optional list of additional variable names to scan for.
        sources: Optional precomputed collect_shader_sources() result.

    Returns:
        Set of matched GLSL built-in variable names found in shader sources.
    """
    all_var_names = _flatten_variable_names(surface)
    if extra_variables:
        all_var_names = list(set(all_var_names) | set(extra_variables))
    if not all_var_names:
        return set()

    result = set()
    if sources is None:
        sources = collect_shader_sources(root_node, ctx, consts)
    for source in sources:
        result |= _match_variables(source, all_var_names)
    return result


def extract_glsl_builtins(root_node, ctx, consts: dict, surface: dict,
                          extra_builtins: list[str] | None = None,
                          sources: list[str] | None = None) -> set[str]:
    """Extract GLSL builtins from shader sources in the file.

    Args:
        root_node: tree-sitter AST root node.
        ctx: ContextInfo from context.detect_context().
        consts: resolved constants from const_propagation.resolve_constants().
        surface: API surface dict (test_surface.json structure).
        extra_builtins: Optional list of additional builtin names to scan for
            (e.g. category-only builtins not in the surface definition).
        sources: Optional precomputed collect_shader_sources() result.

    Returns:
        Set of matched GLSL builtin names found in shader sources.
    """
    all_builtin_names = _flatten_builtin_names(surface)
    if extra_builtins:
        all_builtin_names = list(set(all_builtin_names) | set(extra_builtins))
    if not all_builtin_names:
        return set()

    result = set()
    extra_set = set(extra_builtins) if extra_builtins else set()
    if sources is None:
        sources = collect_shader_sources(root_node, ctx, consts)
    for stripped in sources:
        result |= _match_builtins(stripped, all_builtin_names)
        for name in extra_set:
            if (name not in result and re.search(rf'\b{re.escape(name)}\b', stripped)
                    and not _defines(stripped, name)):
                result.add(name)

    return result

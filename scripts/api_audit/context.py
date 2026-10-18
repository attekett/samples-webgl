"""Context detection for WebGL test files.

Detects WebGL context variables, API version, extensions (3 patterns),
and helper function context tracking from a tree-sitter AST.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from api_audit.const_propagation import collect_declarations

WEBGL_CONTEXT_TYPES = {'webgl', 'webgl2', 'experimental-webgl'}

# antialias is omitted on purpose: antialias:false is boilerplate in most seeds.
CONTEXT_ATTRIBUTE_DEFAULTS = {
    'alpha': 'true', 'depth': 'true', 'stencil': 'false', 'premultipliedAlpha': 'true',
    'preserveDrawingBuffer': 'false', 'powerPreference': 'default',
    'failIfMajorPerformanceCaveat': 'false', 'desynchronized': 'false',
    'xrCompatible': 'false',
}


@dataclass
class ContextInfo:
    api_version: str = 'unknown'
    context_vars: set = field(default_factory=set)
    extensions: set = field(default_factory=set)
    extension_aliases: dict = field(default_factory=dict)
    helper_functions: dict = field(default_factory=dict)
    markers: set = field(default_factory=set)
    canvas_vars: set = field(default_factory=set)
    # (function start_byte, end_byte, parameter name) bound to a context at some call site.
    context_params: set = field(default_factory=set)


def _walk(node, node_type: str) -> list:
    """Recursively collect all descendant nodes of the given type."""
    results = []
    if node.type == node_type:
        results.append(node)
    for child in node.children:
        results.extend(_walk(child, node_type))
    return results


def get_string_value(node) -> Optional[str]:
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
            return get_string_value(child)
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
            return get_string_value(child)
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
        if ctx_str in WEBGL_CONTEXT_TYPES:
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

            if left_ctx in WEBGL_CONTEXT_TYPES or right_ctx in WEBGL_CONTEXT_TYPES:
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

    # Pattern 1b: assignment, `ext = gl.getExtension('X')`
    for assign in _walk(root, 'assignment_expression'):
        left = assign.child_by_field_name('left')
        right = assign.child_by_field_name('right')
        if left is None or right is None or left.type != 'identifier':
            continue
        ext_name = _is_get_extension_call(right)
        if ext_name is not None:
            extensions.add(ext_name)
            extension_aliases[left.text.decode('utf-8')] = ext_name

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


def _attribute_markers(options, declarations) -> set[str]:
    """ctxattr markers for the literal pairs of a getContext options object."""
    if options is not None and options.type == 'identifier':
        options = declarations.get(options.text.decode('utf-8'))
    if options is None or options.type != 'object':
        return set()
    markers = set()
    for pair in options.children:
        if pair.type != 'pair':
            continue
        key = pair.child_by_field_name('key')
        value = pair.child_by_field_name('value')
        if key is None or value is None:
            continue
        key_text = get_string_value(key) if key.type == 'string' else key.text.decode('utf-8')
        if value.type in ('true', 'false'):
            value_text = value.text.decode('utf-8')
        elif value.type == 'number':
            try:
                value_text = 'true' if float(value.text.decode('utf-8')) else 'false'
            except ValueError:
                continue
        elif value.type == 'string':
            value_text = get_string_value(value)
        else:
            continue
        default = CONTEXT_ATTRIBUTE_DEFAULTS.get(key_text)
        if default is not None and value_text != default:
            markers.add(f'ctxattr:{key_text}={value_text}')
    return markers


def _is_offscreen_canvas(node, declarations) -> bool:
    if node.type == 'identifier':
        node = declarations.get(node.text.decode('utf-8'))
        if node is None:
            return False
    if node.type == 'new_expression':
        ctor = node.child_by_field_name('constructor')
        return ctor is not None and ctor.text.decode('utf-8') == 'OffscreenCanvas'
    if node.type == 'call_expression':
        callee = node.child_by_field_name('function')
        return (callee is not None and callee.type == 'member_expression'
                and callee.child_by_field_name('property').text.decode('utf-8')
                == 'transferControlToOffscreen')
    return False


def _is_element_lookup(node) -> bool:
    """A document.getElementById/querySelector*/getElementsBy* call, possibly indexed."""
    while node.type == 'subscript_expression':
        node = node.child_by_field_name('object')
    if node.type != 'call_expression':
        return False
    callee = node.child_by_field_name('function')
    if callee is None or callee.type != 'member_expression':
        return False
    name = callee.child_by_field_name('property').text.decode('utf-8')
    return name in ('getElementById', 'querySelector', 'querySelectorAll') or name.startswith('getElementsBy')


def _receiver_key(receiver) -> str:
    """Same canvas for equal source text, except expressions that create one per site."""
    if receiver.type in ('new_expression', 'call_expression') and not _is_element_lookup(receiver):
        return str(receiver.start_byte)
    return receiver.text.decode('utf-8')


def _detect_context_markers(root) -> tuple[set[str], set[str]]:
    """Markers (ctxattr:*, ctx:multiple, ctx:offscreen) and canvas receiver names."""
    declarations = collect_declarations(root)
    markers: set[str] = set()
    canvas_vars: set[str] = set()
    receivers: set[str] = set()
    for call in _walk(root, 'call_expression'):
        if _is_get_context_call(call) not in WEBGL_CONTEXT_TYPES:
            continue
        receiver = call.child_by_field_name('function').child_by_field_name('object')
        if receiver.type == 'identifier':
            canvas_vars.add(receiver.text.decode('utf-8'))
        receivers.add(_receiver_key(receiver))
        if _is_offscreen_canvas(receiver, declarations):
            markers.add('ctx:offscreen')
        args = call.child_by_field_name('arguments').named_children
        if len(args) > 1:
            markers |= _attribute_markers(args[1], declarations)
    if len(receivers) > 1:
        markers.add('ctx:multiple')
    return markers, canvas_vars


def is_canvas_expr(node, ctx) -> bool:
    """An identifier in ctx.canvas_vars, or `<context var>.canvas`."""
    if node.type == 'identifier':
        return node.text.decode('utf-8') in ctx.canvas_vars
    if node.type == 'member_expression':
        obj = node.child_by_field_name('object')
        prop = node.child_by_field_name('property')
        return (obj.type == 'identifier' and obj.text.decode('utf-8') in ctx.context_vars
                and prop.text.decode('utf-8') == 'canvas')
    return False


def _first_arg(call):
    args = call.child_by_field_name('arguments').named_children
    return args[0] if args else None


def _drawing_buffer_markers(root, ctx) -> set[str]:
    markers: set[str] = set()
    for assign in _walk(root, 'assignment_expression'):
        left = assign.child_by_field_name('left')
        if left.type != 'member_expression':
            continue
        obj = left.child_by_field_name('object')
        prop = left.child_by_field_name('property').text.decode('utf-8')
        if prop in ('width', 'height') and is_canvas_expr(obj, ctx):
            markers.add('canvas:resize')
        elif (prop in ('drawingBufferColorSpace', 'unpackColorSpace') and obj.type == 'identifier'
                and obj.text.decode('utf-8') in ctx.context_vars):
            markers.add(f'attr:{prop}=')
    for call in _walk(root, 'call_expression'):
        callee = call.child_by_field_name('function')
        arg = _first_arg(call)
        if callee.type == 'identifier':
            name = callee.text.decode('utf-8')
        elif callee.type == 'member_expression':
            name = callee.child_by_field_name('property').text.decode('utf-8')
        else:
            continue
        if name == 'requestAnimationFrame' and (
                callee.type == 'identifier'
                or callee.child_by_field_name('object').text.decode('utf-8') == 'window'):
            markers.add('frame:raf')
        elif name in ('toDataURL', 'toBlob') and callee.type == 'member_expression':
            if is_canvas_expr(callee.child_by_field_name('object'), ctx):
                markers.add('canvas:readback')
        elif name == 'drawImage' and callee.type == 'member_expression':
            if arg is not None and is_canvas_expr(arg, ctx):
                markers.add('canvas:readback')
        elif name == 'createImageBitmap' and callee.type == 'identifier':
            if arg is not None and is_canvas_expr(arg, ctx):
                markers.add('canvas:readback')
    return markers


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


_FUNCTION_NODES = ('function_declaration', 'function_expression', 'arrow_function',
                   'generator_function', 'generator_function_declaration', 'method_definition')


def _param_slots(fn) -> list[Optional[str]]:
    """Parameter names by position; None for destructuring and rest slots."""
    single = fn.child_by_field_name('parameter')
    if single is not None:
        return [single.text.decode('utf-8')] if single.type == 'identifier' else [None]
    params = fn.child_by_field_name('parameters')
    slots: list[Optional[str]] = []
    for p in params.named_children if params is not None else []:
        if p.type == 'assignment_pattern':
            p = p.child_by_field_name('left')
        slots.append(p.text.decode('utf-8') if p is not None and p.type == 'identifier' else None)
    return slots


def _bound_names(fn) -> set:
    """Every name the parameter list binds, destructured and rest included."""
    params = fn.child_by_field_name('parameters') or fn.child_by_field_name('parameter')
    names: set = set()

    def visit(n):
        if n.type in ('assignment_pattern', 'object_assignment_pattern'):
            n = n.child_by_field_name('left')
        if n.type in ('identifier', 'shorthand_property_identifier_pattern'):
            names.add(n.text.decode('utf-8'))
        elif n.type == 'pair_pattern':
            visit(n.child_by_field_name('value'))
        else:
            for c in n.named_children:
                visit(c)

    if params is not None:
        visit(params)
    return names


def _function_name(fn) -> Optional[str]:
    if fn.type in ('function_declaration', 'generator_function_declaration'):
        name = fn.child_by_field_name('name')
    else:
        holder = fn.parent
        if holder is not None and holder.type == 'variable_declarator':
            name = holder.child_by_field_name('name')
        elif holder is not None and holder.type == 'assignment_expression':
            name = holder.child_by_field_name('left')
        else:
            return None
    return name.text.decode('utf-8') if name is not None and name.type == 'identifier' else None


def _binding_function(ident):
    """Nearest enclosing function that binds the identifier's name as a parameter."""
    name = ident.text.decode('utf-8')
    node = ident.parent
    while node is not None:
        if node.type in _FUNCTION_NODES and name in _bound_names(node):
            return node
        node = node.parent
    return None


def is_context_receiver(ident, ctx) -> bool:
    """A context variable, or a helper parameter some call site passes a context to."""
    name = ident.text.decode('utf-8')
    if name in ctx.context_vars:
        return True
    fn = _binding_function(ident)
    return fn is not None and (fn.start_byte, fn.end_byte, name) in ctx.context_params


def _detect_context_params(root, info) -> set:
    """Fixed point of parameters that receive a context from a call site."""
    defs: dict[str, list] = {}
    for t in _FUNCTION_NODES:
        for fn in _walk(root, t):
            name = _function_name(fn)
            if name:
                defs.setdefault(name, []).append(fn)
    if not defs:
        return set()
    calls = []
    for call in _walk(root, 'call_expression'):
        callee = call.child_by_field_name('function')
        callee_name = callee.text.decode('utf-8')
        if callee.type == 'identifier' and callee_name in defs:
            args = call.child_by_field_name('arguments').named_children
            calls.append((defs[callee_name], args))
    changed = True
    while changed:
        changed = False
        for fns, args in calls:
            for i, arg in enumerate(args):
                if arg.type != 'identifier' or not is_context_receiver(arg, info):
                    continue
                for fn in fns:
                    slots = _param_slots(fn)
                    if i < len(slots) and slots[i]:
                        key = (fn.start_byte, fn.end_byte, slots[i])
                        if key not in info.context_params:
                            info.context_params.add(key)
                            changed = True
    return info.context_params


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

    _detect_context_params(root_node, info)

    info.markers, info.canvas_vars = _detect_context_markers(root_node)
    info.markers |= _drawing_buffer_markers(root_node, info)

    # Step 3: Detect helper functions
    info.helper_functions = _detect_helper_functions(root_node, context_vars)

    return info

"""WebGL call analysis: method recording, constant resolution,
overload disambiguation, extension method tracking, and return-value
comparison detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from api_audit.const_propagation import GL_NAMESPACES, collect_declarations, loop_bound_constants
from api_audit.context import get_string_value, is_canvas_expr, is_context_receiver


@dataclass
class CallRecord:
    constants: set = field(default_factory=set)
    constant_roles: dict = field(default_factory=dict)  # {const_name: param_name}
    arity: int = 0
    overload_tag: str | None = None  # 'size', 'data', or None


@dataclass
class CallAnalysisResult:
    methods: dict = field(default_factory=dict)       # {method_name: [CallRecord]}
    extension_methods: dict = field(default_factory=dict)  # {ext_name: {method_name: [CallRecord]}}
    return_constants: set = field(default_factory=set)  # constants in === / !== comparisons
    markers: set = field(default_factory=set)  # src:* texture upload sources


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


def _resolve_arg_constant(arg_node, ctx, consts: dict) -> Optional[str]:
    """Resolve an argument node to a WebGL constant name (without 'gl.' prefix).

    Returns the constant name if the argument resolves to a gl.SOMETHING,
    or None otherwise.
    """
    if arg_node.type == 'member_expression':
        obj = arg_node.child_by_field_name('object')
        prop = arg_node.child_by_field_name('property')
        if obj and prop and obj.type == 'identifier' and (
                is_context_receiver(obj, ctx) or _node_text(obj) in GL_NAMESPACES):
            return _node_text(prop)
        return None

    if arg_node.type == 'identifier':
        name = _node_text(arg_node)
        resolved = consts.get(name)
        if isinstance(resolved, str) and resolved.startswith('gl.'):
            return resolved[3:]  # strip 'gl.' prefix
        return None

    if arg_node.type == 'binary_expression':
        # Handle bitmask OR: gl.A | gl.B
        constants = []
        left = arg_node.child_by_field_name('left')
        right = arg_node.child_by_field_name('right')
        if left:
            c = _resolve_arg_constant(left, ctx, consts)
            if c:
                constants.append(c)
        if right:
            c = _resolve_arg_constant(right, ctx, consts)
            if c:
                constants.append(c)
        # Return first found for simple cases, or None
        return constants[0] if constants else None

    return None


def _resolve_all_arg_constants(arg_node, ctx, consts: dict) -> list[str]:
    """Resolve an argument node to all WebGL constant names it contains.

    For binary_expression with |, returns all constituent constants.
    """
    if arg_node.type == 'member_expression':
        obj = arg_node.child_by_field_name('object')
        prop = arg_node.child_by_field_name('property')
        if obj and prop and obj.type == 'identifier' and (
                is_context_receiver(obj, ctx) or _node_text(obj) in GL_NAMESPACES):
            return [_node_text(prop)]
        return []

    if arg_node.type == 'identifier':
        name = _node_text(arg_node)
        resolved = consts.get(name)
        if isinstance(resolved, str) and resolved.startswith('gl.'):
            return [resolved[3:]]
        if isinstance(resolved, tuple):
            return [r[3:] for r in resolved]
        if name not in consts:
            return list(loop_bound_constants(arg_node, consts))
        return []

    if arg_node.type == 'subscript_expression':
        obj = arg_node.child_by_field_name('object')
        if obj is not None and obj.type == 'identifier':
            resolved = consts.get(_node_text(obj))
            return [r[3:] for r in resolved] if isinstance(resolved, tuple) else []
        if obj is not None and obj.type == 'array':
            return _resolve_all_arg_constants(obj, ctx, consts)
        return []

    if arg_node.type == 'binary_expression':
        result = []
        left = arg_node.child_by_field_name('left')
        right = arg_node.child_by_field_name('right')
        if left:
            result.extend(_resolve_all_arg_constants(left, ctx, consts))
        if right:
            result.extend(_resolve_all_arg_constants(right, ctx, consts))
        return result

    if arg_node.type == 'array':
        result = []
        for child in arg_node.children:
            if child.type not in ('[', ']', ','):
                result.extend(_resolve_all_arg_constants(child, ctx, consts))
        return result

    return []


_ENUM_NAMES = {}


def _numeric_enum(arg_node, consts: dict, surface: dict) -> Optional[str]:
    """Name of the core constant a raw integer enum argument (0x8C8E, 35345) stands for.

    Returns None unless exactly one surface constant has that value.
    """
    if arg_node.type == 'number':
        try:
            value = int(_node_text(arg_node), 0)
        except ValueError:
            return None
    elif arg_node.type == 'identifier':
        value = consts.get(_node_text(arg_node))
        if not isinstance(value, int):
            return None
    else:
        return None
    cached = _ENUM_NAMES.get(id(surface))
    if cached is None or cached[0] is not surface:
        by_value = {}
        for name, info in surface.get('constants', {}).items():
            try:
                by_value.setdefault(int(str(info.get('value')), 0), []).append(name)
            except ValueError:
                continue
        cached = _ENUM_NAMES[id(surface)] = (surface, by_value)
    by_value = cached[1]
    names = by_value.get(value, [])
    return names[0] if len(names) == 1 else None


def _classify_arg_for_overload(arg_node) -> str:
    """Classify an argument node for overload disambiguation.

    Returns: 'new_expression', 'number', or 'other'.
    """
    if arg_node.type == 'new_expression':
        return 'new_expression'
    if arg_node.type == 'number':
        return 'number'
    return 'other'


def _find_overload_params(method_name: str, arity: int, surface: dict) -> Optional[list[dict]]:
    """Find the matching overload params list from the surface for a method and arity."""
    method_info = surface.get('methods', {}).get(method_name)
    if not method_info:
        return None
    overloads = method_info.get('overloads', [])
    for overload in overloads:
        if overload.get('arity') == arity:
            return overload.get('params', [])
    return None


def _disambiguate_overload(method_name: str, arg_nodes: list, surface: dict) -> Optional[str]:
    """For ambiguous_arity methods, determine the overload tag.

    Currently handles bufferData: if the second argument is a new_expression -> 'data',
    if it's a number -> 'size'.
    """
    method_info = surface.get('methods', {}).get(method_name)
    if not method_info or not method_info.get('ambiguous_arity'):
        return None

    if method_name == 'bufferData' and len(arg_nodes) >= 2:
        second_arg = arg_nodes[1]
        classification = _classify_arg_for_overload(second_arg)
        if classification == 'new_expression':
            return 'data'
        if classification == 'number':
            return 'size'

    return None


def _find_extension_for_method(method_name: str, surface: dict) -> Optional[str]:
    """Find which extension defines a given method name."""
    for ext_name, ext_info in surface.get('extensions', {}).items():
        if method_name in ext_info.get('methods', {}):
            return ext_name
    return None


_DOM_UPLOADS = {'texImage2D', 'texSubImage2D', 'texImage3D', 'texSubImage3D'}
_NEW_SOURCES = {'ImageData', 'OffscreenCanvas', 'VideoFrame'}
_ELEMENT_SOURCES = {'img': 'image', 'video': 'video', 'canvas': 'canvas'}


def _unwrap(node):
    while node.type in ('await_expression', 'parenthesized_expression'):
        node = node.named_children[0]
    return node


def _upload_source_marker(arg, ctx, declarations) -> Optional[str]:
    """src:* marker for a texImage* source argument; identifiers resolve one declaration level."""
    arg = _unwrap(arg)
    if is_canvas_expr(arg, ctx):
        return 'src:webgl_canvas'
    if arg.type == 'identifier':
        arg = declarations.get(_node_text(arg))
        if arg is None:
            return None
        arg = _unwrap(arg)
        if is_canvas_expr(arg, ctx):
            return 'src:webgl_canvas'
    if arg.type == 'new_expression':
        ctor = _node_text(arg.child_by_field_name('constructor'))
        if ctor in _NEW_SOURCES:
            return f'src:{ctor}'
        return 'src:image' if ctor == 'Image' else None
    if arg.type == 'call_expression':
        callee = arg.child_by_field_name('function')
        if callee.type == 'identifier' and _node_text(callee) == 'createImageBitmap':
            return 'src:ImageBitmap'
        if callee.type == 'member_expression' and _node_text(callee) == 'document.createElement':
            first = arg.child_by_field_name('arguments').named_children
            tag = get_string_value(first[0]) if first else None
            return f'src:{_ELEMENT_SOURCES[tag]}' if tag in _ELEMENT_SOURCES else None
    return None


def _process_call(call_node, extension_aliases: dict,
                  consts: dict, surface: dict, result: CallAnalysisResult,
                  ctx, declarations=None):
    """Process a single call_expression node."""
    callee = call_node.child_by_field_name('function')
    if callee is None or callee.type != 'member_expression':
        return

    obj = callee.child_by_field_name('object')
    prop = callee.child_by_field_name('property')
    if obj is None or prop is None:
        return
    if obj.type == 'call_expression':
        inner_callee = obj.child_by_field_name('function')
        if inner_callee is not None and inner_callee.type == 'member_expression':
            inner_obj = inner_callee.child_by_field_name('object')
            inner_prop = inner_callee.child_by_field_name('property')
            if (inner_obj and inner_prop
                    and inner_obj.type == 'identifier'
                    and is_context_receiver(inner_obj, ctx)
                    and _node_text(inner_prop) == 'getExtension'):
                inner_args = obj.child_by_field_name('arguments')
                if inner_args:
                    for child in inner_args.children:
                        if child.type == 'string':
                            fragments = [c for c in child.children
                                         if c.type == 'string_fragment']
                            if fragments:
                                ext_name_str = fragments[0].text.decode('utf-8')
                                ext_info = surface.get('extensions', {}).get(ext_name_str, {})
                                if ext_info:
                                    method_name = _node_text(prop)
                                    ext_methods = ext_info.get('methods', {})
                                    if method_name in ext_methods:
                                        outer_args = call_node.child_by_field_name('arguments')
                                        outer_arg_nodes = _get_arg_nodes(outer_args) if outer_args else []
                                        record = CallRecord(arity=len(outer_arg_nodes))
                                        result.extension_methods.setdefault(
                                            ext_name_str, {}).setdefault(method_name, []).append(record)
                                return
        return
    if obj.type != 'identifier':
        return

    receiver_name = _node_text(obj)
    method_name = _node_text(prop)

    # Determine if this is a context method call or extension method call
    is_context_call = is_context_receiver(obj, ctx)
    ext_name = extension_aliases.get(receiver_name) if not is_context_call else None

    if not is_context_call and ext_name is None:
        return  # Unknown receiver, ignore

    # Skip getContext calls - these are canvas method, not WebGL API
    if method_name == 'getContext':
        return

    # Get argument nodes
    args_node = call_node.child_by_field_name('arguments')
    arg_nodes = _get_arg_nodes(args_node) if args_node else []
    arity = len(arg_nodes)

    # Resolve constants in arguments
    constants = set()
    constant_roles = {}

    for i, arg in enumerate(arg_nodes):
        arg_constants = _resolve_all_arg_constants(arg, ctx, consts)
        for const_name in arg_constants:
            constants.add(const_name)

    # Determine overload tag for ambiguous methods
    overload_tag = None
    if is_context_call:
        overload_tag = _disambiguate_overload(method_name, arg_nodes, surface)

    # Map constants to parameter roles
    # Find the matching overload from surface
    if is_context_call:
        params = _find_overload_params(method_name, arity, surface)
        if params is None and overload_tag:
            # For ambiguous arity, try to find any matching arity overload
            params = _find_overload_params(method_name, arity, surface)
        if params:
            for i, arg in enumerate(arg_nodes):
                if i < len(params):
                    param_name = params[i].get('name', '')
                    arg_constants = _resolve_all_arg_constants(arg, ctx, consts)
                    if not arg_constants and params[i].get('type') == 'GLenum':
                        enum_name = _numeric_enum(arg, consts, surface)
                        if enum_name:
                            arg_constants = [enum_name]
                            constants.add(enum_name)
                    for const_name in arg_constants:
                        constant_roles[const_name] = param_name

    record = CallRecord(
        constants=constants,
        constant_roles=constant_roles,
        arity=arity,
        overload_tag=overload_tag,
    )

    if is_context_call:
        # Only record if method is known in surface
        if method_name in surface.get('methods', {}):
            result.methods.setdefault(method_name, []).append(record)
            if method_name in _DOM_UPLOADS and arg_nodes:
                marker = _upload_source_marker(arg_nodes[-1], ctx, declarations)
                if marker:
                    result.markers.add(marker)
    elif ext_name:
        # Extension method call
        ext_info = surface.get('extensions', {}).get(ext_name, {})
        if method_name in ext_info.get('methods', {}):
            result.extension_methods.setdefault(ext_name, {})
            result.extension_methods[ext_name].setdefault(method_name, []).append(record)


def _detect_return_comparisons(root_node, ctx, result: CallAnalysisResult):
    """Walk binary_expression nodes with === or !== to find return value comparisons.

    When one side is a gl.CONSTANT member_expression, record the constant name
    in return_constants.
    """
    for binexpr in _walk(root_node, 'binary_expression'):
        # Check for === or !== operator
        has_comparison_op = False
        for child in binexpr.children:
            if child.type in ('===', '!=='):
                has_comparison_op = True
                break
        if not has_comparison_op:
            continue

        left = binexpr.child_by_field_name('left')
        right = binexpr.child_by_field_name('right')

        for side in (left, right):
            if side is None or side.type != 'member_expression':
                continue
            obj = side.child_by_field_name('object')
            prop = side.child_by_field_name('property')
            if obj and prop and obj.type == 'identifier' and is_context_receiver(obj, ctx):
                result.return_constants.add(_node_text(prop))


def analyze_calls(root_node, ctx, consts: dict, surface: dict) -> CallAnalysisResult:
    """Analyze method calls, resolve constants, disambiguate overloads.

    Args:
        root_node: tree-sitter AST root node.
        ctx: ContextInfo from context.detect_context().
        consts: resolved constants from const_propagation.resolve_constants().
        surface: API surface dict (test_surface.json structure).

    Returns:
        CallAnalysisResult with methods, extension_methods, and return_constants.
    """
    result = CallAnalysisResult()

    extension_aliases = ctx.extension_aliases

    declarations = collect_declarations(root_node)
    for call_node in _walk(root_node, 'call_expression'):
        _process_call(call_node, extension_aliases,
                      consts, surface, result, ctx, declarations)

    # Detect return value comparisons (=== / !==)
    _detect_return_comparisons(root_node, ctx, result)

    return result

"""Safe static argument and overload classification for WebGL calls.

Static analysis deliberately leaves identifiers and computed expressions
unknown. Runtime profiling can classify those after observing their values.
"""

from __future__ import annotations

from api_audit.context import is_context_receiver


TYPED_ARRAY_CONSTRUCTORS = {
    "Int8Array", "Uint8Array", "Uint8ClampedArray", "Int16Array",
    "Uint16Array", "Int32Array", "Uint32Array", "Float32Array", "Float64Array",
    "BigInt64Array", "BigUint64Array",
}
ARRAY_BUFFER_CONSTRUCTORS = {"ArrayBuffer", "SharedArrayBuffer"}


def node_text(node) -> str:
    return node.text.decode("utf-8") if node is not None else ""


def argument_nodes(call_node) -> list:
    args = call_node.child_by_field_name("arguments")
    return [child for child in args.children if child.type not in ("(", ")", ",")] if args else []


def classify_static_value(node) -> str:
    """Classify only literal values whose meaning is unambiguous without JS eval."""
    if node is None:
        return "unknown"
    if node.type == "number":
        try:
            value = float(node_text(node).replace("_", ""))
        except ValueError:
            return "unknown"
        if value == 0:
            return "zero"
        if value == 1:
            return "one"
        return "positive" if value > 0 else "negative"
    if node.type == "unary_expression":
        operand = node.child_by_field_name("argument")
        operator = next((node_text(c) for c in node.children if c.type in ("-", "+")), "")
        if operand and operand.type == "number" and operator == "-":
            return "negative" if classify_static_value(operand) != "zero" else "zero"
    if node.type == "new_expression":
        constructor = node.child_by_field_name("constructor")
        if constructor is not None and constructor.type == "identifier":
            if node_text(constructor) in TYPED_ARRAY_CONSTRUCTORS:
                return "typed_array_constructor"
            if node_text(constructor) in ARRAY_BUFFER_CONSTRUCTORS:
                return "array_buffer_constructor"
        return "unknown"
    if node.type == "array":
        return "array_literal"
    return "unknown"


def overload_requirement(method_name: str, overload: dict) -> str:
    """Return the stable requirement key used by coverage reports."""
    signature = ",".join(
        f"{param.get('type', '?')}{'?' if param.get('optional') else ''}"
        for param in overload.get("params", [])
    )
    return f"overload:{method_name}:{signature}"


def resolve_static_overload(method_name: str, arg_nodes: list, surface: dict) -> str | None:
    """Resolve an overload key or return ``None`` when static evidence is ambiguous."""
    method = surface.get("methods", {}).get(method_name, {})
    overloads = method.get("overloads", [])
    arity = len(arg_nodes)
    candidates = [o for o in overloads
                  if o.get("arity", len(o.get("params", []))) <= arity <= len(o.get("params", []))]
    if method_name == "bufferData" and arity >= 2:
        value_type = arg_nodes[1].type
        if value_type == "number":
            candidates = [o for o in candidates if len(o.get("params", [])) > 1
                          and o["params"][1].get("name") == "size"]
        elif classify_static_value(arg_nodes[1]) in (
                "typed_array_constructor", "array_buffer_constructor"):
            candidates = [o for o in candidates if len(o.get("params", [])) > 1
                          and o["params"][1].get("name") in ("data", "srcData")]
        else:
            return None
    if len(candidates) != 1:
        return None
    return overload_requirement(method_name, candidates[0])


def static_overload_calls(root, ctx, surface: dict) -> list[dict]:
    """Collect direct core API calls with an overload key or explicit unknown."""
    calls = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "call_expression":
            callee = node.child_by_field_name("function")
            if callee is not None and callee.type == "member_expression":
                receiver = callee.child_by_field_name("object")
                method = callee.child_by_field_name("property")
                method_name = node_text(method)
                if (receiver is not None and receiver.type == "identifier"
                        and is_context_receiver(receiver, ctx)
                        and method_name in surface.get("methods", {})):
                    args = argument_nodes(node)
                    overload = resolve_static_overload(method_name, args, surface)
                    calls.append({
                        "method": method_name,
                        "arity": len(args),
                        "overload": overload if overload is not None else "unknown",
                        "argument_classes": [classify_static_value(arg) for arg in args],
                    })
        stack.extend(reversed(node.children))
    return calls

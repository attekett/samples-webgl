"""Static mapping from mutator edit spans to WebGL call arguments."""

from __future__ import annotations

import json
from pathlib import Path

from api_audit.context import detect_context
from api_audit.const_propagation import resolve_constants
from api_audit.html_extract import extract_script
from api_audit.parse import parse_js
from webgl_mutator import _script


def analyze_sites(html_source: bytes | str, candidates: dict[str, list[dict]],
                  surface: dict | None = None) -> list[dict]:
    """Map candidate edit spans to WebGL call arguments in one inline script.

    Candidate offsets must be relative to the raw UTF-8 script body, as emitted
    by ``webgl_mutator.candidate_families``. ``eligible_edits`` counts distinct
    candidate edit records, while ``direct_edit_families`` lists their family
    names. A wrapper or partially overlapping span is reported as unknown.
    """
    source = html_source.encode("utf-8") if isinstance(html_source, str) else html_source
    _, raw_script = _script(source)
    extracted_script = extract_script(source.decode("utf-8"))
    leading_bytes = len(raw_script.encode("utf-8")) - len(raw_script.lstrip().encode("utf-8"))
    if raw_script.encode("utf-8").strip() != extracted_script.encode("utf-8"):
        raise ValueError("script extraction changed source bytes; offsets cannot be mapped safely")
    if surface is None:
        surface_path = Path(__file__).resolve().parents[2] / "docs/webgl_api_surface.json"
        surface = json.loads(surface_path.read_text())

    root = parse_js(extracted_script)
    context = detect_context(root, resolve_constants(root))
    extension_methods = {
        (ext_name, method)
        for ext_name, info in surface.get("extensions", {}).items()
        for method in info.get("methods", {})
    }
    spans = _candidate_spans(candidates)
    calls = []
    for node in _walk(root):
        if node.type != "call_expression":
            continue
        resolved = _resolve_call(node, context, surface, extension_methods)
        if resolved is None:
            continue
        method, kind, extension = resolved
        args_node = node.child_by_field_name("arguments")
        arg_nodes = [child for child in args_node.children
                     if child.type not in ("(", ")", ",")] if args_node else []
        known_receiver = kind != "unknown"
        args = []
        for index, arg in enumerate(arg_nodes):
            start, end = arg.start_byte + leading_bytes, arg.end_byte + leading_bytes
            matched, ambiguous, wrappers = _match_spans(start, end, spans)
            status = "unknown" if not known_receiver or ambiguous else (
                "eligible" if matched else "no_direct_edits")
            args.append({
                "index": index,
                "start": start,
                "end": end,
                "direct_edit_families": sorted({family for family, _ in matched}),
                "eligible_edits": len({edit_id for _, edit_id in matched}) if status == "eligible" else 0,
                "wrapper_only_families": sorted({family for family, _ in wrappers}),
                "status": status,
            })
        calls.append({
            "method": method,
            "kind": kind,
            "extension": extension,
            "start": node.start_byte + leading_bytes,
            "end": node.end_byte + leading_bytes,
            "args": args,
        })
    return calls


def _candidate_spans(candidates):
    result = []
    for family, edits in candidates.items():
        for edit_index, edit in enumerate(edits):
            edit_id = f"{family}:{edit_index}"
            edit_spans = edit.get("spans")
            if edit_spans is None:
                edit_spans = [edit]
            for span in edit_spans:
                start, end = span.get("start"), span.get("end")
                if isinstance(start, int) and isinstance(end, int) and 0 <= start <= end:
                    result.append((start, end, family, edit_id))
    return result


def _match_spans(arg_start, arg_end, spans):
    matched, wrappers, ambiguous = [], [], False
    for start, end, family, edit_id in spans:
        if start == end:
            if arg_start <= start <= arg_end:
                ambiguous = True
        elif start >= arg_start and end <= arg_end:
            matched.append((family, edit_id))
        elif start <= arg_start and end >= arg_end:
            # A statement-level replacement can contain the argument but does
            # not make this argument a directly editable site.
            wrappers.append((family, edit_id))
        elif start < arg_end and end > arg_start:
            ambiguous = True
    return matched, ambiguous, wrappers


def _resolve_call(node, context, surface, extension_methods):
    callee = node.child_by_field_name("function")
    if callee is None or callee.type != "member_expression":
        return None
    receiver = callee.child_by_field_name("object")
    prop = callee.child_by_field_name("property")
    if receiver is None or prop is None or prop.type != "property_identifier":
        return None
    method = prop.text.decode("utf-8")
    core_methods = surface.get("methods", {})
    if receiver.type == "identifier":
        receiver_name = receiver.text.decode("utf-8")
        if receiver_name in context.context_vars and method in core_methods:
            return method, "core", None
        extension = context.extension_aliases.get(receiver_name)
        if extension and (extension, method) in extension_methods:
            return method, "extension", extension
    elif receiver.type == "call_expression":
        extension = _chained_extension_name(receiver, context.context_vars)
        if extension and (extension, method) in extension_methods:
            return method, "extension", extension
    if method in core_methods or any(name == method for _, name in extension_methods):
        return method, "unknown", None
    return None


def _chained_extension_name(receiver, context_vars):
    callee = receiver.child_by_field_name("function")
    args = receiver.child_by_field_name("arguments")
    if callee is None or callee.type != "member_expression" or args is None:
        return None
    obj = callee.child_by_field_name("object")
    prop = callee.child_by_field_name("property")
    if (obj is None or prop is None or obj.type != "identifier"
            or obj.text.decode("utf-8") not in context_vars
            or prop.text.decode("utf-8") != "getExtension"):
        return None
    string_arg = next((child for child in args.children if child.type == "string"), None)
    if string_arg is None:
        return None
    fragments = [child.text.decode("utf-8") for child in string_arg.children
                 if child.type == "string_fragment"]
    return "".join(fragments)


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)

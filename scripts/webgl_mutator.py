import argparse
from functools import lru_cache
import hashlib
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from api_audit.parse import parse_js

SCRIPT_RE = re.compile(rb'<script(?=\s|>)(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>', re.I | re.S)
GLSLANG = shutil.which('glslangValidator')


@lru_cache(maxsize=512)
def _glsl_compiles(stage, source):
    if not GLSLANG:
        return False
    try:
        result = subprocess.run([GLSLANG, '--stdin', '-S', stage], input=source,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@lru_cache(maxsize=128)
def _glsl_links(vertex, fragment):
    if not GLSLANG:
        return False
    try:
        with tempfile.TemporaryDirectory(prefix='webgl-glsl-link-') as directory:
            vert = Path(directory) / 'shader.vert'
            frag = Path(directory) / 'shader.frag'
            vert.write_bytes(vertex)
            frag.write_bytes(fragment)
            result = subprocess.run([GLSLANG, '-l', str(vert), str(frag)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _glsl_interface_varyings(source):
    if b'\\' in source:
        return None
    masked = _glsl_mask(source)
    if not re.match(rb'^\s*#\s*version\s+300\s+es\b', masked):
        return None
    for directive in re.finditer(rb'^\s*#.*$', masked, re.M):
        if not re.match(rb'^\s*#\s*version\s+300\s+es\s*$', directive.group()):
            return None
    declarations = []
    pattern = re.compile(rb'\b(out|in)\s+([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*;')
    for match in pattern.finditer(masked):
        if masked[:match.start()].count(b'{') != masked[:match.start()].count(b'}'):
            continue
        direction, glsl_type, name = match.groups()
        if name.startswith(b'gl_'):
            continue
        declarations.append((direction.decode(), glsl_type, name, match.start(3), match.end(3)))
    return masked, declarations


def _glsl_mask(source):
    return re.sub(rb'//[^\r\n]*|/\*.*?\*/',
                  lambda match: re.sub(rb'[^\r\n]', b' ', match.group()), source, flags=re.S)


def _glsl_edits(source, base, stage):
    if not GLSLANG or b'\\' in source:
        return []
    masked = _glsl_mask(source)
    main = re.search(rb'\bvoid\s+main\s*\(\s*\)\s*\{', masked)
    if not main:
        return []
    brace, depth, close = main.end() - 1, 1, None
    for index in range(brace + 1, len(masked)):
        if masked[index:index + 1] == b'{':
            depth += 1
        elif masked[index:index + 1] == b'}':
            depth -= 1
            if depth == 0:
                close = index
                break
    if close is None:
        return []
    body = masked[brace + 1:close]
    custom_trig = re.search(rb'\b(?:sin|cos)\s*\([^;{}]*\)\s*\{', masked) or re.search(
        rb'^\s*#\s*define\s+(?:sin|cos)\b', masked, re.M)
    candidates = []
    patterns = (
        (rb'\bmat[234]\s*\(\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*\)', 'matrix_scalar'),
        (rb'\b(sin|cos)\s*\(', 'trig_function'),
        (rb'\b[A-Za-z_]\w*\s*=\s*[A-Za-z_]\w*\s*\[\s*([1-9]\d*)\s*\]', 'array_index'),
        (rb'for\s*\(\s*int\s+([A-Za-z_]\w*)\s*=\s*0\s*;\s*\1\s*<\s*(\d+)\s*;\s*\1\s*\+\+\s*\)\s*\{\s*([A-Za-z_]\w*)\s*\+=\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*;\s*\}', 'loop_bound'),
    )
    for pattern, kind in patterns:
        for match in re.finditer(pattern, body):
            if kind == 'matrix_scalar':
                number = match.group(1)
                replacement = b'1.0' if float(number) == 0 else b'0.0'
                start, end = match.span(1)
            elif kind == 'trig_function':
                if custom_trig:
                    continue
                replacement = b'cos' if match.group(1) == b'sin' else b'sin'
                start, end = match.span(1)
            elif kind == 'array_index':
                number = int(match.group(1))
                replacement = str(number - 1).encode()
                start, end = match.span(1)
            else:
                number = int(match.group(2))
                if not 2 <= number <= 16:
                    continue
                if body[:match.start()].count(b'{') != body[:match.start()].count(b'}'):
                    continue
                accumulator = re.escape(match.group(3))
                if match.group(1) == match.group(3) or not re.search(
                        rb'\b(?:float|int|uint)\s+' + accumulator + rb'\s*=', body[:match.start()]):
                    continue
                replacement = str(number - 1).encode()
                start, end = match.span(2)
            edited = source[:brace + 1 + start] + replacement + source[brace + 1 + end:]
            if _glsl_compiles(stage, edited):
                candidates.append((kind, base + brace + 1 + start, base + brace + 1 + end, replacement))
    return candidates


def _binding_names(node):
    return {child.text.decode() for child in _walk(node)
            if child.type in ('identifier', 'shorthand_property_identifier_pattern')}


def _script(source):
    for comment in re.finditer(rb'<!--.*?(?:-->|$)', source, re.S):
        if re.search(rb'<script(?=\s|>)', comment.group(), re.I):
            raise ValueError('script tags inside HTML comments are unsupported')
    matches = list(SCRIPT_RE.finditer(source))
    if len(matches) != 1:
        raise ValueError('expected exactly one inline script')
    match = matches[0]
    attrs = match.group('attrs').lower()
    if re.search(rb'\bsrc\s*=|\btype\s*=\s*(?:["\']module["\']|module\b)', attrs):
        raise ValueError('external and module scripts are unsupported')
    return match, match.group('body').decode('utf-8')


def _valid(source):
    root = parse_js(source)
    return not root.has_error


def _direct_context_initializer(value):
    if not value:
        return False
    if value.type == 'binary_expression':
        children = value.named_children
        if (len(children) != 2 or not any(child.type == '||' for child in value.children)
                or not all(_direct_context_initializer(child) for child in children)):
            return None
        for child in children:
            fn = child.child_by_field_name('function') if child.type == 'call_expression' else None
            obj = fn.child_by_field_name('object') if fn and fn.type == 'member_expression' else None
            if not obj or obj.type != 'identifier':
                return None
        left, right = (_direct_context_initializer(child) for child in children)
        return left if left and left == right else None
    if value.type != 'call_expression':
        return None
    fn = value.child_by_field_name('function')
    args = value.child_by_field_name('arguments')
    obj = fn.child_by_field_name('object') if fn and fn.type == 'member_expression' else None
    prop = fn.child_by_field_name('property') if fn and fn.type == 'member_expression' else None
    if (prop and prop.text == b'getContext' and obj and args and args.named_children
            and args.named_children[0].type == 'string'
            and args.named_children[0].text.strip(b"'\" ").lower() in (b'webgl', b'webgl2')):
        return obj.text
    return None


def _context_names(root):
    names = set()
    declarations = {}
    unsafe = set()
    def visit(node):
        if node.type == 'variable_declarator':
            name = node.child_by_field_name('name')
            value = node.child_by_field_name('value')
            if name and name.type == 'identifier':
                declarations[name.text] = declarations.get(name.text, 0) + 1
            elif name:
                unsafe.update(_binding_names(name))
            if name and name.type == 'identifier' and _direct_context_initializer(value):
                names.add(name.text.decode())
        if node.type in ('assignment_expression', 'augmented_assignment_expression'):
            left = node.child_by_field_name('left')
            if left and left.type == 'identifier':
                unsafe.add(left.text.decode())
        if node.type == 'formal_parameters':
            unsafe.update(_binding_names(node))
        if node.type == 'catch_clause':
            parameter = node.child_by_field_name('parameter')
            if parameter:
                unsafe.update(_binding_names(parameter))
        if node.type in ('arrow_function', 'function_declaration', 'function_expression', 'class_declaration'):
            name = node.child_by_field_name('name')
            if name and name.type == 'identifier':
                unsafe.add(name.text.decode())
            if node.type == 'arrow_function':
                parameter = node.child_by_field_name('parameter')
                if parameter and parameter.type == 'identifier':
                    unsafe.add(parameter.text.decode())
        for child in node.children:
            visit(child)
    visit(root)
    return {name for name in names if declarations.get(name.encode()) == 1 and name not in unsafe}


def _scope_key(node):
    parent = node.parent
    while parent and parent.type not in ('statement_block', 'program'):
        parent = parent.parent
    return parent.id if parent else 0


def _block_depth(node):
    depth = 0
    while node:
        if node.type == 'statement_block':
            depth += 1
        node = node.parent
    return depth


def _binding_scope_key(node, declaration):
    if not declaration or declaration.type != 'variable_declaration':
        return _scope_key(node)
    scope = node.parent
    while scope and scope.type not in ('function_declaration', 'function_expression', 'arrow_function', 'method_definition', 'program'):
        scope = scope.parent
    body = scope.child_by_field_name('body') if scope and scope.type != 'program' else None
    return body.id if body and body.type == 'statement_block' else scope.id if scope else 0


def _numeric_constants(root):
    values = {}
    duplicates = set()
    assignments = []
    for node in _walk(root):
        if node.type in ('assignment_expression', 'augmented_assignment_expression'):
            left = node.child_by_field_name('left')
            if left and left.type == 'identifier':
                assignments.append((node, left.text))
        elif node.type == 'update_expression':
            for child in node.named_children:
                if child.type == 'identifier':
                    assignments.append((node, child.text))
    def visit(node):
        if node.type == 'variable_declarator':
            name = node.child_by_field_name('name')
            value = node.child_by_field_name('value')
            declaration = node.parent
            if name and name.type == 'identifier':
                key = (_binding_scope_key(node, declaration), name.text)
                if key in values:
                    duplicates.add(key)
                is_const = declaration and declaration.type == 'lexical_declaration' and declaration.text.lstrip().startswith(b'const')
                try:
                    number = int(value.text.decode(), 0) if is_const and value and value.type == 'number' else -1
                except ValueError:
                    number = -1
                values[key] = number if 0 <= number <= 16 * 1024 * 1024 else None
            elif name:
                for binding in _binding_names(name):
                    values[(_binding_scope_key(node, declaration), binding.encode())] = None
        for child in node.children:
            visit(child)
    visit(root)
    for key in duplicates:
        values[key] = None
    for node in _walk(root):
        if node.type != 'formal_parameters':
            continue
        function = node.parent
        while function and function.type not in ('function_declaration', 'function_expression', 'arrow_function', 'method_definition'):
            function = function.parent
        body = function.child_by_field_name('body') if function else None
        if body and body.type == 'statement_block':
            for name in _binding_names(node):
                values[(body.id, name.encode())] = None
    for node, name in assignments:
        scope = node
        while scope:
            key = (scope.id, name)
            if scope.type in ('statement_block', 'program') and key in values:
                values[key] = None
                break
            scope = scope.parent
    return values


def _resolve_constant(constants, node, name):
    if _shadowed_binding(node, name):
        return -1
    scope = node
    while scope:
        key = (scope.id, name)
        if scope.type in ('statement_block', 'program') and key in constants:
            return constants[key] if constants[key] is not None else -1
        scope = scope.parent
    return -1


def _array_buffer_sizes(root, constants):
    sizes, duplicates, assignments = {}, set(), []
    for node in _walk(root):
        if node.type == 'variable_declarator':
            name = node.child_by_field_name('name')
            value = node.child_by_field_name('value')
            if not name:
                continue
            binding_scope = _binding_scope_key(node, node.parent)
            if name.type != 'identifier':
                for binding in _binding_names(name):
                    key = (binding_scope, binding.encode())
                    if key in sizes:
                        duplicates.add(key)
                    sizes[key] = None
                continue
            key = (binding_scope, name.text)
            if key in sizes:
                duplicates.add(key)
            size = -1
            declaration = node.parent
            if (declaration and declaration.type == 'lexical_declaration'
                    and declaration.text.lstrip().startswith(b'const')
                    and value and value.type == 'new_expression'):
                constructor = value.child_by_field_name('constructor')
                args = value.child_by_field_name('arguments')
                values = args.named_children if args else []
                if (constructor and constructor.type == 'identifier' and constructor.text == b'ArrayBuffer'
                        and len(values) == 1 and _unshadowed_builtin(root, node, 'ArrayBuffer')):
                    size = _integer_argument(values[0], constants, node)
            sizes[key] = size if 1 <= size <= 16 * 1024 * 1024 else None
        elif node.type in ('assignment_expression', 'augmented_assignment_expression', 'update_expression'):
            left = node.child_by_field_name('left')
            if node.type == 'update_expression' and node.named_children:
                left = node.named_children[0]
            if left and left.type == 'identifier':
                assignments.append((node, left.text))
    for key in duplicates:
        sizes[key] = None
    for node, name in assignments:
        scope = node
        while scope:
            key = (scope.id, name)
            if scope.type in ('statement_block', 'program') and key in sizes:
                sizes[key] = None
                break
            scope = scope.parent
    return sizes


def _resolve_array_buffer_size(sizes, node, name):
    if _shadowed_binding(node, name):
        return -1
    scope = node
    while scope:
        key = (scope.id, name)
        if scope.type in ('statement_block', 'program') and key in sizes:
            return sizes[key] if sizes[key] is not None else -1
        scope = scope.parent
    return -1


def _created_resource_bindings(root, contexts, factory):
    bindings, duplicates, assignments = {}, set(), []
    for node in _walk(root):
        if node.type == 'variable_declarator':
            name = node.child_by_field_name('name')
            value = node.child_by_field_name('value')
            if not name:
                continue
            scope = _binding_scope_key(node, node.parent)
            names = [name.text] if name.type == 'identifier' else [item.encode() for item in _binding_names(name)]
            approved = None
            declaration = node.parent
            if (name.type == 'identifier' and declaration and declaration.type == 'lexical_declaration'
                    and declaration.text.lstrip().startswith(b'const') and value
                    and value.type == 'call_expression'):
                function = value.child_by_field_name('function')
                args = value.child_by_field_name('arguments')
                receiver = function.child_by_field_name('object') if function and function.type == 'member_expression' else None
                method = function.child_by_field_name('property') if function and function.type == 'member_expression' else None
                valid_factory_args = (args and len(args.named_children) == 1 if factory == 'createShader'
                                      else args and not args.named_children)
                if (receiver and receiver.text.decode() in contexts and method and method.text == factory.encode()
                        and valid_factory_args):
                    approved = receiver.text.decode()
            for binding in names:
                key = (scope, binding)
                if key in bindings:
                    duplicates.add(key)
                bindings[key] = approved if name.type == 'identifier' and binding == name.text else None
        elif node.type in ('assignment_expression', 'augmented_assignment_expression', 'update_expression'):
            left = node.child_by_field_name('left')
            if node.type == 'update_expression' and node.named_children:
                left = node.named_children[0]
            if left and left.type == 'identifier':
                assignments.append((node, left.text))
    for key in duplicates:
        bindings[key] = None
    for node, name in assignments:
        scope = node
        while scope:
            key = (scope.id, name)
            if scope.type in ('statement_block', 'program') and key in bindings:
                bindings[key] = None
                break
            scope = scope.parent
    return bindings


def _resolve_created_resource(bindings, node, name):
    if _shadowed_binding(node, name):
        return None
    name = name if isinstance(name, bytes) else name.encode()
    scope = node
    while scope:
        key = (scope.id, name)
        if scope.type in ('statement_block', 'program') and key in bindings:
            return bindings[key]
        scope = scope.parent
    return None


def _created_buffer_bindings(root, contexts):
    return _created_resource_bindings(root, contexts, 'createBuffer')


def _created_textures(root, contexts):
    return _created_resource_bindings(root, contexts, 'createTexture')


def _created_programs(root, contexts):
    return _created_resource_bindings(root, contexts, 'createProgram')


def _compatible_texture_update_edits(root, contexts, constants, aliases, calls, opaque_calls):
    created = _created_textures(root, contexts)
    context_starts = {}
    for declaration in _walk(root):
        if declaration.type != 'variable_declarator':
            continue
        name = declaration.child_by_field_name('name')
        value = declaration.child_by_field_name('value')
        if (name and name.type == 'identifier' and name.text.decode() in contexts
                and _direct_context_initializer(value)):
            context_starts[name.text.decode()] = declaration.end_byte
    bound, storage, deleted = {}, {}, set()
    edits = []
    for name, args, node in calls:
        vals = args.named_children
        fn = node.child_by_field_name('function')
        receiver = fn.child_by_field_name('object').text.decode()
        scope = _scope_key(node)
        target = _enum_key(vals[0], receiver, node, aliases) if vals else None

        if name in ('activeTexture', 'deleteTexture'):
            if name == 'deleteTexture' and len(vals) == 1 and vals[0].type == 'identifier':
                deleted_name = vals[0].text.decode()
                deleted.add((receiver, deleted_name))
                storage = {key: value for key, value in storage.items()
                           if key[1] != receiver or key[2] != deleted_name}
                bound = {key: value for key, value in bound.items()
                         if key[1] != receiver or value != deleted_name}
            else:
                bound = {key: value for key, value in bound.items() if key[1] != receiver}
                storage = {key: value for key, value in storage.items() if key[1] != receiver}
            continue

        if name in ('texStorage2D', 'copyTexImage2D', 'compressedTexImage2D'):
            storage = {key: value for key, value in storage.items() if key[1] != receiver}
            continue

        if name == 'bindTexture':
            # A binding change inside another block makes outer texture-unit state uncertain.
            if any(key[1] == receiver and key[0] != scope for key in bound):
                bound = {key: value for key, value in bound.items() if key[1] != receiver}
                storage = {key: value for key, value in storage.items() if key[1] != receiver}
            if len(vals) == 2 and target == f'{receiver}.TEXTURE_2D' and not _conditional(node):
                resource = vals[1]
                resource_name = resource.text.decode() if resource.type == 'identifier' else None
                if resource_name and _resolve_created_resource(created, node, resource_name) == receiver:
                    bound[(scope, receiver, target)] = resource_name
                else:
                    bound.pop((scope, receiver, target), None)
            else:
                bound = {key: value for key, value in bound.items() if key[1] != receiver}
                storage = {key: value for key, value in storage.items() if key[1] != receiver}
            continue

        if name == 'texImage2D':
            if any(key[1] == receiver and key[0] != scope for key in bound):
                bound = {key: value for key, value in bound.items() if key[1] != receiver}
                storage = {key: value for key, value in storage.items() if key[1] != receiver}
            resource = bound.get((scope, receiver, f'{receiver}.TEXTURE_2D'))
            if (len(vals) == 9 and target == f'{receiver}.TEXTURE_2D' and resource
                    and not _conditional(node)):
                level = _integer_argument(vals[1], constants, node)
                width = _integer_argument(vals[3], constants, node)
                height = _integer_argument(vals[4], constants, node)
                border = _integer_argument(vals[5], constants, node)
                internal = _enum_key(vals[2], receiver, node, aliases)
                fmt = _enum_key(vals[6], receiver, node, aliases)
                typ = _enum_key(vals[7], receiver, node, aliases)
                if (level >= 0 and width > 0 and height > 0 and border == 0 and internal and fmt and typ
                        and _safe_pixel_source(root, vals[8], node)):
                    storage[(scope, receiver, resource)] = ((level, internal, width, height, fmt, typ), node.end_byte)
                else:
                    storage.pop((scope, receiver, resource), None)
            else:
                if resource:
                    storage.pop((scope, receiver, resource), None)
                if _conditional(node):
                    bound = {key: value for key, value in bound.items() if key[1] != receiver}
                    storage = {key: value for key, value in storage.items() if key[1] != receiver}
            continue

        if name != 'texSubImage2D' or len(vals) != 9 or _conditional(node):
            continue
        if any(key[1] == receiver and key[0] != scope for key in bound):
            bound = {key: value for key, value in bound.items() if key[1] != receiver}
            storage = {key: value for key, value in storage.items() if key[1] != receiver}
        if target != f'{receiver}.TEXTURE_2D':
            continue
        original = bound.get((scope, receiver, target))
        original_storage = storage.get((scope, receiver, original)) if original else None
        if not original_storage:
            continue
        level = _integer_argument(vals[1], constants, node)
        x = _integer_argument(vals[2], constants, node)
        y = _integer_argument(vals[3], constants, node)
        width = _integer_argument(vals[4], constants, node)
        height = _integer_argument(vals[5], constants, node)
        fmt = _enum_key(vals[6], receiver, node, aliases)
        typ = _enum_key(vals[7], receiver, node, aliases)
        signature, original_end = original_storage
        if (x < 0 or y < 0 or width <= 0 or height <= 0 or level != signature[0]
                or fmt != signature[4] or typ != signature[5]
                or x + width > signature[2] or y + height > signature[3]):
            continue
        stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
        if not stmt:
            continue
        if any(context_starts.get(receiver, node.start_byte) <= call.start_byte < node.start_byte
               for call in opaque_calls):
            continue
        for (storage_scope, storage_receiver, other), (other_signature, other_end) in sorted(storage.items()):
            if (storage_scope != scope or storage_receiver != receiver or other == original
                    or other_signature != signature or _resolve_created_resource(created, node, other) != receiver
                    or (receiver, other) in deleted or (receiver, original) in deleted):
                continue
            earliest = min(original_end, other_end)
            if any(earliest <= call.start_byte < node.start_byte for call in opaque_calls):
                continue
            replacement = (f'{receiver}.bindTexture({receiver}.TEXTURE_2D, {other}); '
                           f'{stmt.text.decode()} '
                           f'{receiver}.bindTexture({receiver}.TEXTURE_2D, {original});')
            edits.append(('compatible_texture_update_switch', stmt.start_byte, stmt.end_byte, replacement))
            break
    return edits


def _texture_allocation_update_dimensions(root, contexts, constants, aliases, calls, opaque_calls):
    created = _created_textures(root, contexts)
    attached = set()
    for name, args, node in calls:
        vals = args.named_children
        if name in ('framebufferTexture2D', 'framebufferTextureLayer'):
            texture_index = 3 if name == 'framebufferTexture2D' else 2
            if len(vals) <= texture_index:
                continue
            texture = vals[texture_index]
            if texture.type == 'identifier':
                attached.add((node.child_by_field_name('function').child_by_field_name('object').text.decode(),
                              texture.text.decode()))
    edits = []

    def has_rgba8_source(arg, node, width, height):
        if not _safe_pixel_source(root, arg, node):
            return False
        constructor = arg.child_by_field_name('constructor')
        arguments = arg.child_by_field_name('arguments')
        values = arguments.named_children if arguments else []
        if not constructor or constructor.text != b'Uint8Array' or len(values) != 1:
            return False
        value = values[0]
        if value.type == 'array':
            return len(value.named_children) >= width * height * 4
        return _integer_argument(value, constants, node) >= width * height * 4

    def has_unaliased_uses(resource, receiver):
        for use in _walk(root):
            if use.type not in ('identifier', 'shorthand_property_identifier') or use.text.decode() != resource:
                continue
            parent = use.parent
            if parent and parent.type == 'variable_declarator' and parent.child_by_field_name('name') == use:
                if _resolve_created_resource(created, use, resource) == receiver:
                    continue
            if parent and parent.type == 'arguments':
                call = parent.parent
                fn = call.child_by_field_name('function') if call and call.type == 'call_expression' else None
                prop = fn.child_by_field_name('property') if fn and fn.type == 'member_expression' else None
                obj = fn.child_by_field_name('object') if fn and fn.type == 'member_expression' else None
                args = parent.named_children
                if (prop and prop.text == b'bindTexture' and obj and obj.text.decode() == receiver
                        and len(args) == 2 and args[1] == use and not _conditional(call)
                        and _enum_key(args[0], receiver, call, aliases) == f'{receiver}.TEXTURE_2D'):
                    continue
            return False
        return True

    for index, (name, args, allocation) in enumerate(calls):
        vals = args.named_children
        if (name != 'texImage2D' or len(vals) != 9 or _conditional(allocation)
                or not allocation.parent or allocation.parent.type != 'expression_statement'):
            continue
        fn = allocation.child_by_field_name('function')
        receiver = fn.child_by_field_name('object').text.decode()
        scope = _scope_key(allocation)
        if _enum_key(vals[0], receiver, allocation, aliases) != f'{receiver}.TEXTURE_2D':
            continue
        level = _integer_argument(vals[1], constants, allocation)
        width = _integer_argument(vals[3], constants, allocation)
        height = _integer_argument(vals[4], constants, allocation)
        internal = _enum_key(vals[2], receiver, allocation, aliases)
        fmt = _enum_key(vals[6], receiver, allocation, aliases)
        typ = _enum_key(vals[7], receiver, allocation, aliases)
        if (level != 0 or width <= 1 or height <= 1 or _integer_argument(vals[5], constants, allocation) != 0
                or internal not in (f'{receiver}.RGBA8', f'{receiver}.RGBA')
                or fmt != f'{receiver}.RGBA' or typ != f'{receiver}.UNSIGNED_BYTE'
                or not has_rgba8_source(vals[8], allocation, width, height)):
            continue
        resource = None
        bind = None
        for previous in reversed(calls[:index]):
            pname, pargs, pnode = previous
            pvals = pargs.named_children
            pfn = pnode.child_by_field_name('function')
            if pfn.child_by_field_name('object').text.decode() != receiver:
                continue
            if pname in ('activeTexture', 'bindTexture', 'deleteTexture'):
                if (pname == 'bindTexture' and len(pvals) == 2 and not _conditional(pnode)
                        and _scope_key(pnode) == scope
                        and _enum_key(pvals[0], receiver, pnode, aliases) == f'{receiver}.TEXTURE_2D'
                        and pvals[1].type == 'identifier'
                        and _resolve_created_resource(created, pnode, pvals[1].text) == receiver):
                    resource, bind = pvals[1].text.decode(), pnode
                break
        if (not resource or (receiver, resource) in attached
                or _resolve_created_resource(created, allocation, resource) != receiver
                or not has_unaliased_uses(resource, receiver)
                or any(pname == 'activeTexture' and pnode.start_byte > bind.start_byte
                       for pname, _, pnode in calls[:index]
                       if pnode.child_by_field_name('function').child_by_field_name('object').text.decode() == receiver)):
            continue
        update = None
        for later_name, later_args, later in calls[index + 1:]:
            later_fn = later.child_by_field_name('function')
            if later_fn.child_by_field_name('object').text.decode() != receiver:
                continue
            if _scope_key(later) != scope or _conditional(later):
                update = None
                break
            if later_name in ('activeTexture', 'bindTexture', 'deleteTexture'):
                update = None
                break
            if later_name in ('texImage2D', 'texSubImage2D', 'copyTexImage2D',
                              'copyTexSubImage2D', 'texStorage2D', 'compressedTexImage2D'):
                if later_name != 'texSubImage2D':
                    update = None
                    break
                uvals = later_args.named_children
                if (len(uvals) != 9 or _enum_key(uvals[0], receiver, later, aliases) != f'{receiver}.TEXTURE_2D'
                        or _integer_argument(uvals[1], constants, later) != 0
                        or _integer_argument(uvals[2], constants, later) != 0
                        or _integer_argument(uvals[3], constants, later) != 0
                        or _integer_argument(uvals[4], constants, later) != width
                        or _integer_argument(uvals[5], constants, later) != height
                        or _enum_key(uvals[6], receiver, later, aliases) != fmt
                        or _enum_key(uvals[7], receiver, later, aliases) != typ
                        or not has_rgba8_source(uvals[8], later, width, height)):
                    update = None
                    break
                update = later
                break
        if not update:
            continue
        if any(bind.start_byte <= call.start_byte < update.start_byte for call in opaque_calls):
            continue
        if any(call.start_byte > update.end_byte for call in opaque_calls):
            continue
        bound = resource
        unsafe_later_update = False
        for later_name, later_args, later in calls:
            if later.start_byte <= update.end_byte:
                continue
            later_fn = later.child_by_field_name('function')
            if later_fn.child_by_field_name('object').text.decode() != receiver:
                continue
            later_vals = later_args.named_children
            if later_name == 'activeTexture':
                bound = None
            elif later_name == 'bindTexture':
                if len(later_vals) == 2 and _enum_key(later_vals[0], receiver, later, aliases) == f'{receiver}.TEXTURE_2D':
                    bound = (later_vals[1].text.decode()
                             if later_vals[1].type == 'identifier'
                             and _resolve_created_resource(created, later, later_vals[1].text) == receiver
                             else None)
            elif later_name == 'deleteTexture' and later_vals:
                if later_vals[0].type == 'identifier' and later_vals[0].text.decode() == resource:
                    unsafe_later_update = True
                    break
            elif later_name in ('texSubImage2D', 'copyTexSubImage2D', 'texImage2D',
                                'copyTexImage2D', 'texStorage2D', 'compressedTexImage2D',
                                'compressedTexSubImage2D'):
                if later_vals and _enum_key(later_vals[0], receiver, later, aliases) == f'{receiver}.TEXTURE_2D':
                    if bound is None or bound == resource:
                        unsafe_later_update = True
                        break
        if unsafe_later_update:
            continue
        update_vals = update.child_by_field_name('arguments').named_children
        spans = []
        for arg, dimension in ((vals[3], width), (vals[4], height),
                               (update_vals[4], width), (update_vals[5], height)):
            spans.append((arg.start_byte, arg.end_byte, str(max(1, dimension // 2))))
        edits.append(('texture_allocation_update_dimensions', spans))
    return edits


def _glsl_linked_varying_edits(root, contexts, aliases, calls, opaque_calls):
    created_shaders = _created_resource_bindings(root, contexts, 'createShader')
    created_programs = _created_resource_bindings(root, contexts, 'createProgram')
    stages, shader_starts = {}, {}
    for declaration in _walk(root):
        if declaration.type != 'variable_declarator':
            continue
        name = declaration.child_by_field_name('name')
        value = declaration.child_by_field_name('value')
        if (not name or name.type != 'identifier' or not value or value.type != 'call_expression'
                or not declaration.parent or declaration.parent.type != 'lexical_declaration'
                or not declaration.parent.text.lstrip().startswith(b'const')):
            continue
        fn = value.child_by_field_name('function')
        args = value.child_by_field_name('arguments')
        receiver = fn.child_by_field_name('object') if fn and fn.type == 'member_expression' else None
        method = fn.child_by_field_name('property') if fn and fn.type == 'member_expression' else None
        values = args.named_children if args else []
        if (not receiver or receiver.text.decode() not in contexts or not method
                or method.text != b'createShader' or len(values) != 1
                or _resolve_created_resource(created_shaders, declaration, name.text) != receiver.text.decode()):
            continue
        enum = _enum_key(values[0], receiver.text.decode(), declaration, aliases)
        stage = 'vertex' if enum == f'{receiver.text.decode()}.VERTEX_SHADER' else (
            'fragment' if enum == f'{receiver.text.decode()}.FRAGMENT_SHADER' else None)
        if stage:
            key = (_scope_key(declaration), receiver.text.decode(), name.text)
            stages[key] = stage
            shader_starts[key] = declaration.start_byte

    sources, attachments, links = {}, {}, {}
    source_calls = {}
    for name, args, node in calls:
        vals = args.named_children
        fn = node.child_by_field_name('function')
        receiver = fn.child_by_field_name('object').text.decode()
        scope = _scope_key(node)
        if name == 'shaderSource' and vals and vals[0].type == 'identifier':
            shader = vals[0].text
            if _resolve_created_resource(created_shaders, node, shader) == receiver:
                key = (scope, receiver, shader)
                source_calls.setdefault((receiver, shader), []).append(node)
                sources.setdefault(key, []).append((vals, node))
        elif name == 'attachShader' and vals and vals[0].type == 'identifier':
            program = vals[0].text
            if _resolve_created_resource(created_programs, node, program) == receiver:
                attachments.setdefault((receiver, program), []).append((scope, vals, node))
        elif name == 'linkProgram' and vals and vals[0].type == 'identifier':
            program = vals[0].text
            if _resolve_created_resource(created_programs, node, program) == receiver:
                links.setdefault((receiver, program), []).append((scope, vals, node))

    edits = []
    for (receiver, program), program_links in links.items():
        if len(program_links) != 1:
            continue
        link_scope, link_args, link_node = program_links[0]
        if (len(link_args) != 1 or _conditional(link_node)
                or not link_node.parent or link_node.parent.type != 'expression_statement'):
            continue
        program_attachments = attachments.get((receiver, program), [])
        if len(program_attachments) != 2:
            continue
        if any(scope != link_scope or len(values) != 2 or _conditional(node)
               or not node.parent or node.parent.type != 'expression_statement'
               or values[1].type != 'identifier'
               for scope, values, node in program_attachments):
            continue
        attach_nodes = [node for _, _, node in program_attachments]
        shader_names = [values[1].text for _, values, _ in program_attachments]
        if len(set(shader_names)) != 2 or max(node.end_byte for node in attach_nodes) >= link_node.start_byte:
            continue
        shader_records = []
        valid_pair = True
        for (_, values, attach_node), shader in zip(program_attachments, shader_names):
            if _resolve_created_resource(created_shaders, attach_node, shader) != receiver:
                valid_pair = False
                break
            shader_stage = stages.get((link_scope, receiver, shader))
            source_entries = sources.get((link_scope, receiver, shader), [])
            if shader_stage is None or len(source_entries) != 1 or len(source_calls.get((receiver, shader), [])) != 1:
                valid_pair = False
                break
            source_vals, source_node = source_entries[0]
            if (len(source_vals) != 2 or source_vals[1].type != 'template_string'
                    or any(child.type == 'template_substitution' for child in source_vals[1].named_children)
                    or _conditional(source_node) or not source_node.parent
                    or source_node.parent.type != 'expression_statement'
                    or source_node.start_byte >= attach_node.start_byte):
                valid_pair = False
                break
            shader_records.append((shader_stage, source_vals[1], source_node))
        if not valid_pair or {record[0] for record in shader_records} != {'vertex', 'fragment'}:
            continue
        if any(sum(1 for attach_list in attachments.values()
                   for _, values, _ in attach_list
                   if len(values) == 2 and values[1].type == 'identifier'
                   and values[1].text == shader) != 1 for shader in shader_names):
            continue
        source_start = min(
            min(record[2].start_byte for record in shader_records),
            *(shader_starts[(link_scope, receiver, shader)] for shader in shader_names))
        if any(source_start <= call.start_byte < link_node.end_byte for call in opaque_calls):
            continue
        vertex_template = next(template for stage, template, _ in shader_records if stage == 'vertex')
        fragment_template = next(template for stage, template, _ in shader_records if stage == 'fragment')
        vertex_source = vertex_template.text[1:-1]
        fragment_source = fragment_template.text[1:-1]
        vertex_info = _glsl_interface_varyings(vertex_source)
        fragment_info = _glsl_interface_varyings(fragment_source)
        if not vertex_info or not fragment_info:
            continue
        vertex_mask, vertex_decls = vertex_info
        fragment_mask, fragment_decls = fragment_info
        outs = {}
        ins = {}
        for direction, glsl_type, name, start, end in vertex_decls:
            if direction == 'out':
                outs.setdefault(name, []).append((glsl_type, start, end))
        for direction, glsl_type, name, start, end in fragment_decls:
            if direction == 'in':
                ins.setdefault(name, []).append((glsl_type, start, end))
        all_names = set(re.findall(rb'\b[A-Za-z_]\w*\b', vertex_mask + b'\n' + fragment_mask))
        for name in sorted(outs.keys() & ins.keys()):
            out_decls = outs[name]
            in_decls = ins[name]
            if len(out_decls) != 1 or len(in_decls) != 1 or out_decls[0][0] != in_decls[0][0]:
                continue
            if (sum(1 for _, _, declared, _, _ in vertex_decls if declared == name) != 1
                    or sum(1 for _, _, declared, _, _ in fragment_decls if declared == name) != 1):
                continue
            fresh_id = 0
            while f'mut_varying_{fresh_id}'.encode() in all_names:
                fresh_id += 1
            replacement = f'mut_varying_{fresh_id}'.encode()
            token = re.compile(rb'\b' + re.escape(name) + rb'\b')
            vertex_tokens = [(match.start(), match.end()) for match in token.finditer(vertex_mask)]
            fragment_tokens = [(match.start(), match.end()) for match in token.finditer(fragment_mask)]
            if not vertex_tokens or not fragment_tokens:
                continue
            spans = []
            for template, tokens in ((vertex_template, vertex_tokens), (fragment_template, fragment_tokens)):
                base = template.start_byte + 1
                spans.extend((base + start, base + end, replacement.decode()) for start, end in tokens)
            edited_vertex = vertex_source
            for start, end in reversed(vertex_tokens):
                edited_vertex = edited_vertex[:start] + replacement + edited_vertex[end:]
            edited_fragment = fragment_source
            for start, end in reversed(fragment_tokens):
                edited_fragment = edited_fragment[:start] + replacement + edited_fragment[end:]
            if _glsl_links(vertex_source, fragment_source) and _glsl_links(edited_vertex, edited_fragment):
                edits.append(('glsl_linked_varying_rename', spans))
    return edits


def _framebuffer_attachment_cycle_edits(root, contexts, constants, aliases, calls, opaque_calls):
    created_fbos = _created_resource_bindings(root, contexts, 'createFramebuffer')
    created_textures = _created_resource_bindings(root, contexts, 'createTexture')
    bound = {}
    bind_counts = {}
    texture_targets = {}
    texture_starts = {}
    deleted_fbos, deleted_textures = set(), set()
    context_starts = {}
    for declaration in _walk(root):
        if declaration.type != 'variable_declarator':
            continue
        name = declaration.child_by_field_name('name')
        value = declaration.child_by_field_name('value')
        if (name and name.type == 'identifier' and name.text.decode() in contexts
                and _direct_context_initializer(value)):
            context_starts[name.text.decode()] = declaration.end_byte
        if (name and name.type == 'identifier' and value and value.type == 'call_expression'):
            fn = value.child_by_field_name('function')
            obj = fn.child_by_field_name('object') if fn and fn.type == 'member_expression' else None
            prop = fn.child_by_field_name('property') if fn and fn.type == 'member_expression' else None
            binding = (_binding_scope_key(declaration, declaration.parent), name.text)
            if (obj and prop and prop.text == b'createTexture' and obj.text.decode() in contexts
                    and created_textures.get(binding) == obj.text.decode()):
                texture_starts[binding] = declaration.end_byte

    def texture_binding(node, name):
        if _shadowed_binding(node, name):
            return None
        scope = node
        while scope:
            key = (scope.id, name)
            if scope.type in ('statement_block', 'program') and key in created_textures:
                return key if created_textures[key] else None
            scope = scope.parent
        return None

    edits = []
    target_name = 'FRAMEBUFFER'
    for name, args, node in calls:
        vals = args.named_children
        fn = node.child_by_field_name('function')
        receiver = fn.child_by_field_name('object').text.decode()
        scope = _scope_key(node)
        target = _enum_key(vals[0], receiver, node, aliases) if vals else None
        if name == 'bindTexture' and len(vals) == 2 and vals[1].type == 'identifier':
            texture = vals[1].text.decode()
            binding = texture_binding(node, vals[1].text)
            if (binding and created_textures[binding] == receiver and node.parent
                    and node.parent.type == 'expression_statement'):
                texture_targets.setdefault((scope, receiver, binding), None if _conditional(node) else target)
            continue
        if name == 'bindFramebuffer':
            bind_counts[receiver] = bind_counts.get(receiver, 0) + 1
            if any(key[1] == receiver and key[0] != scope for key in bound):
                bound = {key: value for key, value in bound.items() if key[1] != receiver}
            key = (scope, receiver, f'{receiver}.{target_name}')
            if (len(vals) == 2 and target == f'{receiver}.{target_name}' and not _conditional(node)
                    and vals[1].type == 'identifier'
                    and _resolve_created_resource(created_fbos, node, vals[1].text) == receiver
                    and (receiver, vals[1].text.decode()) not in deleted_fbos):
                bound[key] = (vals[1].text.decode(), node.end_byte)
            else:
                bound = {key_: value for key_, value in bound.items() if key_[1] != receiver}
            continue
        if name == 'deleteFramebuffer':
            if len(vals) == 1 and vals[0].type == 'identifier':
                resource = vals[0].text.decode()
                deleted_fbos.add((receiver, resource))
                bound = {key: value for key, value in bound.items()
                         if key[1] != receiver or value[0] != resource}
            else:
                bound = {key: value for key, value in bound.items() if key[1] != receiver}
            continue
        if name == 'deleteTexture' and len(vals) == 1 and vals[0].type == 'identifier':
            deleted_textures.add((receiver, vals[0].text.decode()))
            continue
        if name != 'framebufferTexture2D' or len(vals) != 5 or _conditional(node):
            continue
        if (target != f'{receiver}.{target_name}'
                or not _is_safe_enum(vals[1], receiver, node, aliases)
                or _enum_key(vals[2], receiver, node, aliases) != f'{receiver}.TEXTURE_2D'
                or vals[3].type != 'identifier'
                or _resolve_created_resource(created_textures, node, vals[3].text) != receiver
                or _integer_argument(vals[4], constants, node) != 0):
            continue
        key = (scope, receiver, f'{receiver}.{target_name}')
        fbo = bound.get(key)
        texture = vals[3].text.decode()
        texture_key = texture_binding(node, vals[3].text)
        if (not fbo or not texture_key
                or texture_targets.get((scope, receiver, texture_key)) != f'{receiver}.TEXTURE_2D'
                or any(texture_starts.get(texture_key, node.start_byte) <= call.start_byte < node.start_byte
                       for call in opaque_calls)
                or bind_counts.get(receiver, 0) != 1
                or (receiver, fbo[0]) in deleted_fbos or (receiver, texture) in deleted_textures):
            continue
        stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
        if not stmt or any(fbo[1] <= call.start_byte < node.start_byte
                           for call in opaque_calls
                           if call.start_byte >= context_starts.get(receiver, node.start_byte)):
            continue
        original = stmt.text.decode()
        detach = (f'{receiver}.framebufferTexture2D({vals[0].text.decode()}, {vals[1].text.decode()}, '
                 f'{vals[2].text.decode()}, null, 0);')
        edits.append(('framebuffer_attachment_cycle', stmt.start_byte, stmt.end_byte,
                      f'{original} {detach} {original}'))
    return edits


def _framebuffer_retire_edits(root, contexts, aliases, calls, opaque_calls):
    created = _created_resource_bindings(root, contexts, 'createFramebuffer')
    declarations = {}
    references = {}
    for node in _walk(root):
        if node.type == 'variable_declarator':
            name = node.child_by_field_name('name')
            if name and name.type == 'identifier':
                declarations[(name.text, _scope_key(node))] = (node, name)
        if node.type in ('identifier', 'shorthand_property_identifier'):
            references.setdefault(node.text, []).append(node)

    calls_by_scope = {}
    for name, args, node in calls:
        if name == 'bindFramebuffer':
            calls_by_scope.setdefault((_scope_key(node),
                                       node.child_by_field_name('function').child_by_field_name('object').text.decode()), []).append((args, node))

    edits = []
    for name, args, node in calls:
        vals = args.named_children
        fn = node.child_by_field_name('function')
        receiver = fn.child_by_field_name('object').text.decode()
        stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
        if (name != 'bindFramebuffer' or len(vals) != 2 or not stmt or _conditional(node)
                or _enum_key(vals[0], receiver, node, aliases) != f'{receiver}.FRAMEBUFFER'
                or vals[1].type != 'null'):
            continue
        scope = _scope_key(node)
        key = (scope, receiver)
        prior = [(prior_args, prior_node) for prior_args, prior_node in calls_by_scope.get(key, [])
                 if prior_node.start_byte < node.start_byte]
        if not prior:
            continue
        bind_args, bind_node = prior[-1]
        if (len(bind_args.named_children) != 2 or _conditional(bind_node)
                or _enum_key(bind_args.named_children[0], receiver, bind_node, aliases) != f'{receiver}.FRAMEBUFFER'):
            continue
        resource = bind_args.named_children[1]
        if (resource.type != 'identifier'
                or _resolve_created_resource(created, bind_node, resource.text) != receiver):
            continue
        resource_name = resource.text
        declaration_info = declarations.get((resource_name, scope))
        if not declaration_info:
            continue
        declaration, name_node = declaration_info
        decl_value = declaration.child_by_field_name('value')
        if (not declaration.parent or declaration.parent.type != 'lexical_declaration'
                or not declaration.parent.text.lstrip().startswith(b'const')
                or not decl_value or decl_value.type != 'call_expression'):
            continue
        resource_refs = references.get(resource_name, [])
        if {(ref.start_byte, ref.end_byte) for ref in resource_refs} != {
                (name_node.start_byte, name_node.end_byte), (resource.start_byte, resource.end_byte)}:
            continue
        if any(call_name == 'bindFramebuffer' and call_node.start_byte > bind_node.start_byte
               and call_node.start_byte < node.start_byte
               and call_node.child_by_field_name('function').child_by_field_name('object').text.decode() == receiver
               for call_name, _, call_node in calls):
            continue
        if any(bind_node.end_byte <= call.start_byte < node.start_byte
               and _scope_key(call) == scope for call in opaque_calls):
            continue
        if any(call_name == 'deleteFramebuffer' and call_node.start_byte < node.start_byte
               and call_args.named_children and call_args.named_children[0].type == 'identifier'
               and call_args.named_children[0].text == resource_name
               for call_name, call_args, call_node in calls):
            continue
        if any(call.start_byte > node.start_byte and _scope_key(call) == scope for call in opaque_calls):
            continue
        edits.append(('framebuffer_retire', stmt.start_byte, stmt.end_byte,
                      f'{stmt.text.decode()} {receiver}.deleteFramebuffer({resource_name.decode()});'))
    return edits


def _texture_retire_edits(root, contexts, aliases, calls, opaque_calls):
    created = _created_resource_bindings(root, contexts, 'createTexture')
    declarations = {}
    references = {}
    for node in _walk(root):
        if node.type == 'variable_declarator':
            name = node.child_by_field_name('name')
            if name and name.type == 'identifier':
                declarations[(name.text, _scope_key(node))] = (node, name)
        if node.type in ('identifier', 'shorthand_property_identifier'):
            references.setdefault(node.text, []).append(node)

    calls_by_scope = {}
    for name, args, node in calls:
        fn = node.child_by_field_name('function')
        receiver = fn.child_by_field_name('object').text.decode()
        calls_by_scope.setdefault((_scope_key(node), receiver), []).append((name, args, node))

    edits = []
    for name, args, node in calls:
        vals = args.named_children
        fn = node.child_by_field_name('function')
        receiver = fn.child_by_field_name('object').text.decode()
        stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
        if (name != 'bindTexture' or len(vals) != 2 or not stmt or _conditional(node)
                or _enum_key(vals[0], receiver, node, aliases) != f'{receiver}.TEXTURE_2D'
                or vals[1].type != 'null'):
            continue
        scope = _scope_key(node)
        prior = [(call_name, call_args, call_node)
                 for call_name, call_args, call_node in calls_by_scope.get((scope, receiver), [])
                 if call_node.start_byte < node.start_byte]
        matching = [(call_args, call_node) for call_name, call_args, call_node in prior
                    if call_name == 'bindTexture' and len(call_args.named_children) == 2
                    and _enum_key(call_args.named_children[0], receiver, call_node, aliases) == f'{receiver}.TEXTURE_2D'
                    and call_args.named_children[1].type == 'identifier']
        if not matching:
            continue
        bind_args, bind_node = matching[-1]
        bind_stmt = bind_node.parent if bind_node.parent and bind_node.parent.type == 'expression_statement' else None
        if not bind_stmt:
            continue
        resource = bind_args.named_children[1]
        if _resolve_created_resource(created, bind_node, resource.text) != receiver:
            continue
        resource_name = resource.text
        declaration_info = declarations.get((resource_name, scope))
        if not declaration_info:
            continue
        declaration, name_node = declaration_info
        decl_value = declaration.child_by_field_name('value')
        if (not declaration.parent or declaration.parent.type != 'lexical_declaration'
                or not declaration.parent.text.lstrip().startswith(b'const')
                or not decl_value or decl_value.type != 'call_expression'):
            continue
        receiver_calls = [(call_name, call_args, call_node) for (call_scope, call_receiver), entries in calls_by_scope.items()
                          if call_receiver == receiver for call_name, call_args, call_node in entries]
        if any(call_name == 'activeTexture' and decl_value.end_byte <= call_node.start_byte < node.start_byte
               for call_name, _, call_node in receiver_calls):
            continue
        if any(call_name in ('getParameter', 'getFramebufferAttachmentParameter')
               and decl_value.end_byte <= call_node.start_byte < node.start_byte
               for call_name, _, call_node in receiver_calls):
            continue
        if _block_depth(bind_node) != _block_depth(node):
            continue
        resource_refs = references.get(resource_name, [])
        approved_refs = {(name_node.start_byte, name_node.end_byte)}
        safe_refs = True
        for ref in resource_refs:
            if (ref.start_byte, ref.end_byte) in approved_refs:
                continue
            parent = ref.parent
            args_node = parent if parent and parent.type == 'arguments' else None
            call_node = args_node.parent if args_node else None
            call_fn = call_node.child_by_field_name('function') if call_node else None
            call_args = args_node.named_children if args_node else []
            if (not call_node or call_node.type != 'call_expression' or not call_fn
                    or call_fn.type != 'member_expression'
                    or call_fn.child_by_field_name('object').text.decode() != receiver
                    or call_fn.child_by_field_name('property').text != b'bindTexture'
                    or len(call_args) != 2
                    or (call_args[1].start_byte, call_args[1].end_byte) != (ref.start_byte, ref.end_byte)
                    or _enum_key(call_args[0], receiver, call_node, aliases) != f'{receiver}.TEXTURE_2D'
                    or not (declaration.end_byte <= call_node.start_byte < node.start_byte)
                    or _scope_key(call_node) != scope or _conditional(call_node)):
                safe_refs = False
                break
            approved_refs.add((ref.start_byte, ref.end_byte))
        if not safe_refs:
            continue
        target_binds = [(call_args, call_node) for call_name, call_args, call_node in prior
                        if call_name == 'bindTexture' and call_args.named_children
                        and _enum_key(call_args.named_children[0], receiver, call_node, aliases) == f'{receiver}.TEXTURE_2D']
        later_binds = [(call_args.named_children, call_node) for call_name, call_args, call_node in receiver_calls
                       if call_name == 'bindTexture' and call_node.start_byte > node.start_byte
                       and _scope_key(call_node) == scope]
        if (not target_binds or target_binds[-1][1] is not bind_node
                or any(len(args) != 2
                       or _enum_key(args[0], receiver, call_node, aliases) != f'{receiver}.TEXTURE_2D'
                       or args[1].type != 'identifier'
                       or _resolve_created_resource(created, call_node, args[1].text) != receiver
                       for args, call_node in later_binds)
                or any(call_name == 'bindTexture' and call_node.start_byte > bind_node.start_byte
                       and call_node.start_byte < node.start_byte
                       for call_name, _, call_node in receiver_calls
                       if _scope_key(call_node) != scope or _conditional(call_node))):
            continue
        if any(call_name == 'framebufferTexture2D' and len(call_args.named_children) >= 4
               and call_args.named_children[3].type == 'identifier'
               and call_args.named_children[3].text == resource_name
               for call_name, call_args, call_node in calls_by_scope.get((scope, receiver), [])):
            continue
        if any(call_name == 'deleteTexture' and call_args.named_children
               and call_args.named_children[0].type == 'identifier'
               and call_args.named_children[0].text == resource_name
               for call_name, call_args, call_node in calls_by_scope.get((scope, receiver), [])):
            continue
        if any(call.start_byte <= bind_node.start_byte and call.end_byte >= bind_node.end_byte
               or bind_node.end_byte <= call.start_byte < node.start_byte or call.start_byte > node.start_byte
               and _scope_key(call) == scope for call in opaque_calls):
            continue
        if any(bind_node.end_byte <= call_node.start_byte < node.start_byte
               and (_scope_key(call_node) != scope or _conditional(call_node))
               for _, _, call_node in calls):
            continue
        edits.append(('texture_retire', stmt.start_byte, stmt.end_byte,
                      f'{stmt.text.decode()} {receiver}.deleteTexture({resource_name.decode()});'))
    return edits


def _shadowed_binding(node, name):
    name = name.decode() if isinstance(name, bytes) else name
    while node:
        if node.type == 'catch_clause':
            parameter = node.child_by_field_name('parameter')
            if parameter and name in _binding_names(parameter):
                return True
        if node.type in ('function_declaration', 'function_expression', 'arrow_function', 'method_definition'):
            parameters = node.child_by_field_name('parameters') or node.child_by_field_name('parameter')
            if parameters and name in _binding_names(parameters):
                return True
        node = node.parent
    return False


def _conditional(node):
    while node:
        if node.type in ('if_statement', 'ternary_expression', 'switch_body', 'for_statement',
                         'for_in_statement', 'while_statement', 'do_statement'):
            return True
        node = node.parent
    return False


def _enum_aliases(root, contexts):
    aliases = {}
    duplicates = set()
    reassigned = set()
    assignments = []
    for node in _walk(root):
        if node.type in ('assignment_expression', 'augmented_assignment_expression', 'update_expression'):
            left = node.child_by_field_name('left')
            if node.type == 'update_expression' and node.named_children:
                left = node.named_children[0]
            if left and left.type == 'identifier':
                assignments.append((node, left.text))
        if node.type != 'variable_declarator':
            continue
        name = node.child_by_field_name('name')
        value = node.child_by_field_name('value')
        decl = node.parent
        if not name:
            continue
        binding_scope = _binding_scope_key(node, decl)
        if name.type != 'identifier':
            for binding in _binding_names(name):
                aliases[(binding_scope, binding.encode())] = None
            continue
        key = (binding_scope, name.text)
        if key in aliases:
            duplicates.add(key)
        alias = None
        if decl and decl.type == 'lexical_declaration' and decl.text.lstrip().startswith(b'const') and value and value.type == 'member_expression':
            obj = value.child_by_field_name('object')
            prop = value.child_by_field_name('property')
            if obj and obj.text.decode() in contexts and prop:
                alias = (obj.text.decode(), value.text.decode())
        aliases[key] = alias
    for key in duplicates:
        aliases[key] = None
    for node, name in assignments:
        scope = node
        while scope:
            key = (scope.id, name)
            if scope.type in ('statement_block', 'program') and key in aliases:
                aliases[key] = None
                break
            scope = scope.parent
    return aliases


def _is_safe_enum(arg, receiver, node, aliases):
    if arg.type == 'member_expression':
        obj = arg.child_by_field_name('object')
        return bool(obj and obj.text.decode() == receiver and arg.child_by_field_name('property'))
    if arg.type != 'identifier':
        return False
    if _shadowed_binding(node, arg.text):
        return False
    scope = node
    while scope:
        key = (scope.id, arg.text)
        if scope.type in ('statement_block', 'program') and key in aliases:
            value = aliases[key]
            return bool(value and value[0] == receiver)
        scope = scope.parent
    return False


def _enum_key(arg, receiver, node, aliases):
    if arg.type == 'member_expression':
        return arg.text.decode() if _is_safe_enum(arg, receiver, node, aliases) else None
    if arg.type == 'identifier':
        if _shadowed_binding(node, arg.text):
            return None
        scope = node
        while scope:
            key = (scope.id, arg.text)
            if scope.type in ('statement_block', 'program') and key in aliases:
                value = aliases[key]
                return value[1] if value and value[0] == receiver else None
            scope = scope.parent
    return None


def _is_bound_identifier(root, arg, node):
    if arg.type != 'identifier':
        return False
    scopes = set()
    for declaration in _walk(root):
        if declaration.type == 'variable_declarator':
            name = declaration.child_by_field_name('name')
            if name and name.type == 'identifier' and name.text == arg.text:
                scopes.add((_scope_key(declaration), name.text))
        elif declaration.type == 'formal_parameters':
            function = declaration.parent
            while function and function.type not in ('function_declaration', 'function_expression', 'arrow_function', 'method_definition'):
                function = function.parent
            body = function.child_by_field_name('body') if function else None
            if body and body.type == 'statement_block':
                for name in declaration.named_children:
                    if name.type == 'identifier' and name.text == arg.text:
                        scopes.add((body.id, name.text))
    scope = node
    while scope:
        key = (scope.id, arg.text)
        if scope.type in ('statement_block', 'program') and key in scopes:
            return True
        scope = scope.parent
    return False


def _integer_argument(arg, constants, node):
    if arg.type == 'number':
        try:
            return int(arg.text.decode(), 0)
        except ValueError:
            return -1
    if arg.type == 'identifier':
        return _resolve_constant(constants, node, arg.text)
    return -1


def _safe_pixel_source(root, arg, node):
    if arg.type != 'new_expression':
        return False
    constructor = arg.child_by_field_name('constructor')
    if not constructor or constructor.type != 'identifier':
        return False
    name = constructor.text.decode()
    if name not in {'Uint8Array', 'Uint8ClampedArray', 'Int8Array', 'Uint16Array',
                    'Int16Array', 'Uint32Array', 'Int32Array', 'Float32Array'}:
        return False
    if _shadowed_binding(node, name):
        return False
    for declaration in _walk(root):
        if declaration.type == 'variable_declarator':
            binding = declaration.child_by_field_name('name')
            if binding and name in _binding_names(binding):
                return False
        if declaration.type in ('function_declaration', 'class_declaration'):
            binding = declaration.child_by_field_name('name')
            if binding and binding.text.decode() == name:
                return False
        if declaration.type in ('assignment_expression', 'augmented_assignment_expression'):
            left = declaration.child_by_field_name('left')
            if left and left.type == 'identifier' and left.text.decode() == name:
                return False
    return True


def _unshadowed_builtin(root, node, name):
    if _shadowed_binding(node, name):
        return False
    for declaration in _walk(root):
        if declaration.type == 'variable_declarator':
            binding = declaration.child_by_field_name('name')
            if binding and name in _binding_names(binding):
                return False
        elif declaration.type in ('function_declaration', 'class_declaration'):
            binding = declaration.child_by_field_name('name')
            if binding and binding.text.decode() == name:
                return False
        elif declaration.type in ('assignment_expression', 'augmented_assignment_expression'):
            left = declaration.child_by_field_name('left')
            if left and left.type == 'identifier' and left.text.decode() == name:
                return False
    return True


def _bounded_values(count):
    return sorted({value for value in (0, count - 1, count // 2) if value < count})


def _storage_sizes(size):
    if size < 0 or size >= 16 * 1024 * 1024:
        return ()
    cap = 16 * 1024 * 1024
    return tuple(sorted({value for value in (
        ((size // 256) + 1) * 256,
        1 << size.bit_length(),
    ) if size < value <= cap}))


def _walk(root):
    yield root
    for child in root.children:
        yield from _walk(child)


def _call_nodes(root, context_names):
    out = []
    def visit(node):
        if node.type == 'call_expression' and node.child_by_field_name('function'):
            fn = node.child_by_field_name('function')
            if fn.type == 'member_expression':
                obj = fn.child_by_field_name('object')
                prop = fn.child_by_field_name('property')
                if obj and obj.text.decode() in context_names and prop:
                    args = node.child_by_field_name('arguments')
                    if args:
                        out.append((prop.text.decode(), args, node))
        for child in node.children:
            visit(child)
    visit(root)
    return out


def _edits(js):
    root = parse_js(js)
    contexts = _context_names(root)
    calls = _call_nodes(root, contexts)
    constants = _numeric_constants(root)
    array_buffer_sizes = _array_buffer_sizes(root, constants)
    created_buffers = _created_buffer_bindings(root, contexts)
    created_programs = _created_programs(root, contexts)
    enum_aliases = _enum_aliases(root, contexts)
    shader_types = {}
    for declaration in _walk(root):
        if declaration.type != 'variable_declarator':
            continue
        name = declaration.child_by_field_name('name')
        value = declaration.child_by_field_name('value')
        parent = declaration.parent
        if (not name or name.type != 'identifier' or not value or value.type != 'call_expression'
                or not parent or parent.type != 'lexical_declaration'
                or not parent.text.lstrip().startswith(b'const')):
            continue
        function = value.child_by_field_name('function')
        arguments = value.child_by_field_name('arguments')
        if not function or function.type != 'member_expression' or not arguments:
            continue
        context = function.child_by_field_name('object')
        method = function.child_by_field_name('property')
        args = arguments.named_children
        if not context or context.text.decode() not in contexts or not method or method.text != b'createShader' or len(args) != 1:
            continue
        shader_type = _enum_key(args[0], context.text.decode(), declaration, enum_aliases)
        stage = 'vert' if shader_type == f'{context.text.decode()}.VERTEX_SHADER' else 'frag' if shader_type == f'{context.text.decode()}.FRAGMENT_SHADER' else None
        if stage:
            shader_types[(_scope_key(declaration), name.text, context.text.decode())] = stage
    edits = []
    view_widths = {'Uint8Array': 1, 'Uint16Array': 2, 'Uint32Array': 4,
                   'Int8Array': 1, 'Int16Array': 2, 'Int32Array': 4,
                   'Float32Array': 4, 'Float64Array': 8, 'DataView': 1}
    for node in _walk(root):
        if node.type != 'new_expression':
            continue
        constructor = node.child_by_field_name('constructor')
        args = node.child_by_field_name('arguments')
        vals = args.named_children if args else []
        if (not constructor or constructor.type != 'identifier' or len(vals) != 3
                or constructor.text.decode() not in view_widths):
            continue
        type_name = constructor.text.decode()
        if not _unshadowed_builtin(root, node, type_name):
            continue
        backing, offset_arg, length_arg = vals
        if backing.type != 'identifier':
            continue
        size = _resolve_array_buffer_size(array_buffer_sizes, node, backing.text)
        offset = _integer_argument(offset_arg, constants, node)
        length = _integer_argument(length_arg, constants, node)
        width = view_widths[type_name]
        if (size < 1 or offset <= 0 or length < 0 or offset % width
                or offset + length * width > size):
            continue
        edits.append(('typed_array_view_offset', offset_arg.start_byte, offset_arg.end_byte, '0'))
    bound_buffers = {}
    # shortcut: track direct binds within one block; expand when modeling helper calls and texture units.
    safe_bound_buffers = {}
    compatible_buffer_caps = {}
    pending_compatible_switches = []
    deleted_buffers = set()
    buffer_delete_seen = set()
    buffer_allocations = {}
    pending_buffer_redefines = {}
    safe_bound_textures = {}
    initialized_textures = {}
    opaque_calls = [call for call in _walk(root) if call.type == 'call_expression'
                    and not (call.child_by_field_name('function')
                             and call.child_by_field_name('function').type == 'member_expression'
                             and call.child_by_field_name('function').child_by_field_name('object')
                             and call.child_by_field_name('function').child_by_field_name('object').text.decode() in contexts)
                    and not (call.child_by_field_name('function')
                             and call.child_by_field_name('function').type == 'member_expression'
                             and call.child_by_field_name('function').child_by_field_name('property')
                             and call.child_by_field_name('function').child_by_field_name('property').text == b'getContext')]
    draw_arities = {'drawArrays': 3, 'drawElements': 4, 'drawRangeElements': 6,
                    'drawArraysInstanced': 4, 'drawElementsInstanced': 5}
    indexed_draws = {'drawElements', 'drawRangeElements', 'drawElementsInstanced'}
    valid_modes = ('POINTS', 'LINES', 'LINE_LOOP', 'LINE_STRIP', 'TRIANGLES',
                   'TRIANGLE_STRIP', 'TRIANGLE_FAN')
    transform_feedback = ('beginTransformFeedback', 'pauseTransformFeedback',
                          'resumeTransformFeedback', 'endTransformFeedback')
    draw_mode_safe = not any(re.search(r'\b' + name + r'\b', js) for name in transform_feedback)
    program_transition_safe = draw_mode_safe and not re.search(r'\bdeleteProgram\b', js)
    for name, args, node in calls:
        vals = [c for c in args.named_children]
        scope = _scope_key(node)
        block_depth = _block_depth(node)
        fn = node.child_by_field_name('function')
        receiver = fn.child_by_field_name('object').text.decode()
        if name == 'bindBuffer' and vals:
            bound_target = _enum_key(vals[0], receiver, node, enum_aliases)
            if (bound_target == f'{receiver}.ARRAY_BUFFER'
                    and any(key[1] == receiver and cap[2] < block_depth
                            for key, cap in compatible_buffer_caps.items())):
                compatible_buffer_caps = {key: cap for key, cap in compatible_buffer_caps.items()
                                          if key[1] != receiver}
        for pending in list(pending_compatible_switches):
            pending_scope, pending_receiver, bind_node, original_arg, replacement = pending
            if bind_node.end_byte > node.start_byte or pending_receiver != receiver:
                continue
            invalidated = (pending_scope != scope or _conditional(node)
                           or any(bind_node.end_byte <= call.start_byte < node.start_byte
                                  for call in opaque_calls))
            if invalidated:
                pending_compatible_switches.remove(pending)
                continue
            target = _enum_key(vals[0], receiver, node, enum_aliases) if vals else None
            if name in ('vertexAttribPointer', 'vertexAttribIPointer'):
                if (len(vals) == (6 if name == 'vertexAttribPointer' else 5)
                        and node.parent and node.parent.type == 'expression_statement'):
                    edits.append(('compatible_buffer_switch', original_arg.start_byte,
                                  original_arg.end_byte, replacement.decode()))
                pending_compatible_switches.remove(pending)
            elif name == 'deleteBuffer':
                pending_compatible_switches.remove(pending)
            elif name == 'bindBuffer':
                if len(vals) != 2 or target in (None, f'{receiver}.ARRAY_BUFFER'):
                    pending_compatible_switches.remove(pending)
            elif name in ('bufferData', 'bufferSubData'):
                if not vals or target in (None, f'{receiver}.ARRAY_BUFFER'):
                    pending_compatible_switches.remove(pending)
        if name == 'bindBuffer' and len(vals) == 2 and not _conditional(node):
            target_key = _enum_key(vals[0], receiver, node, enum_aliases)
            original = vals[1]
            if (target_key == f'{receiver}.ARRAY_BUFFER' and original.type == 'identifier'
                    and node.parent and node.parent.type == 'expression_statement'):
                original_name = original.text
                original_context = _resolve_created_resource(created_buffers, node, original_name)
                original_cap = compatible_buffer_caps.get((scope, receiver, original_name))
                if (original_context == receiver and original_cap and receiver not in buffer_delete_seen
                        and (receiver, original_name) not in deleted_buffers):
                    for (cap_scope, cap_receiver, other_name), other_cap in sorted(
                            compatible_buffer_caps.items(), key=lambda item: item[0][2]):
                        other_context = _resolve_created_resource(created_buffers, node, other_name)
                        if (cap_scope == scope and cap_receiver == receiver and other_name != original_name
                                and other_context == receiver and other_cap[0] == original_cap[0]
                                and receiver not in buffer_delete_seen
                                and (receiver, other_name) not in deleted_buffers
                                and not any(min(other_cap[1], original_cap[1]) <= call.start_byte < node.start_byte
                                            for call in opaque_calls)):
                            pending_compatible_switches.append((scope, receiver, node, original, other_name))
                            break
        if name == 'bindBuffer' and len(vals) >= 2:
            target_key = _enum_key(vals[0], receiver, node, enum_aliases)
            if target_key:
                bound_buffers = {key: value for key, value in bound_buffers.items()
                                 if key[1] != receiver or key[2] != vals[0].text}
                safe_bound_buffers = {key: value for key, value in safe_bound_buffers.items()
                                      if key[1] != receiver or key[2] != target_key}
            else:
                bound_buffers = {key: value for key, value in bound_buffers.items() if key[1] != receiver}
                safe_bound_buffers = {key: value for key, value in safe_bound_buffers.items() if key[1] != receiver}
            buffer_allocations = {key: value for key, value in buffer_allocations.items()
                                  if key[1] != receiver or (target_key and key[2] != target_key)}
            pending_buffer_redefines = {key: value for key, value in pending_buffer_redefines.items()
                                        if key[1] != receiver or (target_key and key[2] != target_key)}
        if name == 'bindVertexArray':
            target_key = f'{receiver}.ELEMENT_ARRAY_BUFFER'
            bound_buffers = {key: value for key, value in bound_buffers.items() if key[1] != receiver}
            safe_bound_buffers = {key: value for key, value in safe_bound_buffers.items()
                                  if key[1] != receiver or key[2] != target_key}
            buffer_allocations = {key: value for key, value in buffer_allocations.items()
                                  if key[1] != receiver or key[2] != target_key}
            pending_buffer_redefines = {key: value for key, value in pending_buffer_redefines.items()
                                        if key[1] != receiver or key[2] != target_key}
        if name == 'bindBuffer' and len(vals) >= 2 and not _conditional(node):
            target = vals[0]
            resource = vals[1]
            bound_buffers[(scope, receiver, target.text)] = None if resource.text == b'null' else resource.text
            target_key = _enum_key(target, receiver, node, enum_aliases) if len(vals) == 2 else None
            if target_key:
                safe_bound_buffers[(scope, receiver, target_key)] = resource.text if resource.type == 'identifier' else None
        if name == 'activeTexture':
            safe_bound_textures = {key: value for key, value in safe_bound_textures.items() if key[1] != receiver}
            initialized_textures = {key: value for key, value in initialized_textures.items() if key[1] != receiver}
        if name == 'texImage2D' and vals:
            target_key = _enum_key(vals[0], receiver, node, enum_aliases)
            initialized_textures = {key: value for key, value in initialized_textures.items()
                                    if key[1] != receiver or (target_key and key[2] != target_key)}
        if name == 'bindTexture' and len(vals) == 2:
            target_key = _enum_key(vals[0], receiver, node, enum_aliases)
            if target_key:
                resource = vals[1]
                key = (scope, receiver, target_key)
                resource_name = resource.text if resource.type == 'identifier' else None
                initialized_textures = {key_: value for key_, value in initialized_textures.items()
                                        if key_[1] != receiver or key_[2] != target_key}
                safe_bound_textures = {key_: value for key_, value in safe_bound_textures.items()
                                       if key_[1] != receiver or key_[2] != target_key}
                if not _conditional(node):
                    safe_bound_textures[key] = resource_name
            else:
                safe_bound_textures = {key: value for key, value in safe_bound_textures.items()
                                       if key[1] != receiver}
                initialized_textures = {key: value for key, value in initialized_textures.items()
                                        if key[1] != receiver}
        if name == 'bufferData' and len(vals) >= 3 and not _conditional(node):
            target, data = vals[0].text, vals[1]
            if (scope, receiver, target) in bound_buffers and bound_buffers[(scope, receiver, target)] is not None:
                size = _integer_argument(data, constants, node)
                for value in _storage_sizes(size):
                    edits.append(('resource_storage', data.start_byte, data.end_byte, str(value)))
        if name == 'bufferData' and vals:
            target_key = _enum_key(vals[0], receiver, node, enum_aliases)
            if (target_key == f'{receiver}.ARRAY_BUFFER'
                    and any(key[1] == receiver and cap[2] < block_depth
                            for key, cap in compatible_buffer_caps.items())):
                compatible_buffer_caps = {key: cap for key, cap in compatible_buffer_caps.items()
                                          if key[1] != receiver}
            resource = safe_bound_buffers.get((scope, receiver, target_key)) if target_key else None
            resource_name = resource if resource else None
            if target_key == f'{receiver}.ARRAY_BUFFER' and len(vals) == 3 and not _conditional(node):
                size = _integer_argument(vals[1], constants, node)
                if (resource_name and receiver not in buffer_delete_seen
                        and (receiver, resource_name) not in deleted_buffers
                        and _resolve_created_resource(created_buffers, node, resource_name) == receiver
                        and _is_safe_enum(vals[2], receiver, node, enum_aliases)
                        and 1 <= size <= 16 * 1024 * 1024):
                    compatible_buffer_caps[(scope, receiver, resource_name)] = (size, node.start_byte, block_depth)
                elif resource_name:
                    compatible_buffer_caps.pop((scope, receiver, resource_name), None)
            elif resource_name:
                compatible_buffer_caps.pop((scope, receiver, resource_name), None)
            elif not target_key:
                compatible_buffer_caps = {key: value for key, value in compatible_buffer_caps.items()
                                          if key[1] != receiver}
        if name == 'bufferData' and vals:
            target_key = _enum_key(vals[0], receiver, node, enum_aliases)
            key = (scope, receiver, target_key)
            buffer_allocations = {key_: value for key_, value in buffer_allocations.items()
                                  if key_[1] != receiver or (target_key and key_[2] != target_key)}
            pending_buffer_redefines = {key_: value for key_, value in pending_buffer_redefines.items()
                                        if key_[1] != receiver or (target_key and key_[2] != target_key)}
            if len(vals) == 3 and not _conditional(node):
                stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
                usage_ok = _is_safe_enum(vals[2], receiver, node, enum_aliases)
                size = _integer_argument(vals[1], constants, node)
                resource = safe_bound_buffers.get(key) if target_key else None
                helper_in_call = any(node.start_byte <= call.start_byte < node.end_byte for call in opaque_calls)
                if (stmt and target_key and usage_ok and resource and not helper_in_call
                        and 1 <= size <= 16 * 1024 * 1024):
                    buffer_allocations[key] = (resource, size, stmt.text.decode(), node.end_byte)
        if name == 'bufferData' and len(vals) == 3 and not _conditional(node):
            stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
            target_key = _enum_key(vals[0], receiver, node, enum_aliases)
            usage_ok = _is_safe_enum(vals[2], receiver, node, enum_aliases)
            size = _integer_argument(vals[1], constants, node)
            resource = safe_bound_buffers.get((scope, receiver, target_key)) if target_key else None
            if stmt and target_key and usage_ok and resource and 0 <= size <= 16 * 1024 * 1024:
                edits.append(('storage_duplicate', stmt.start_byte, stmt.end_byte,
                              f'{stmt.text.decode()} {stmt.text.decode()}'))
        if name == 'bufferSubData' and len(vals) == 3 and not _conditional(node):
            stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
            target_key = _enum_key(vals[0], receiver, node, enum_aliases)
            key = (scope, receiver, target_key)
            allocation = buffer_allocations.get(key)
            resource = safe_bound_buffers.get(key)
            offset = _integer_argument(vals[1], constants, node)
            helper_between = allocation and any(allocation[3] <= call.start_byte < node.end_byte
                                                for call in opaque_calls)
            if (stmt and allocation and resource == allocation[0] and allocation[0] == resource
                    and 0 <= offset < allocation[1] and not helper_between):
                pending_buffer_redefines[key] = (stmt, allocation, node.end_byte)
        if name == 'deleteBuffer' and len(vals) == 1:
            deleted = vals[0].text
            buffer_delete_seen.add(receiver)
            compatible_buffer_caps = {key: value for key, value in compatible_buffer_caps.items()
                                      if key[1] != receiver}
            deleted_buffers.add((receiver, deleted))
            safe_bound_buffers = {key: value for key, value in safe_bound_buffers.items()
                                  if key[1] != receiver or value != deleted}
            buffer_allocations = {key: value for key, value in buffer_allocations.items()
                                  if key[1] != receiver or value[0] != deleted}
            pending_buffer_redefines = {key: value for key, value in pending_buffer_redefines.items()
                                        if key[1] != receiver or value[1][0] != deleted}
        if name == 'texImage2D' and len(vals) == 9 and not _conditional(node):
            stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
            target_key = _enum_key(vals[0], receiver, node, enum_aliases)
            target = f'{receiver}.TEXTURE_2D'
            level = _integer_argument(vals[1], constants, node)
            width = _integer_argument(vals[3], constants, node)
            height = _integer_argument(vals[4], constants, node)
            border = _integer_argument(vals[5], constants, node)
            enums_safe = all(_enum_key(vals[index], receiver, node, enum_aliases) for index in (2, 6, 7))
            resource = safe_bound_textures.get((scope, receiver, target))
            texture_key = (scope, receiver, target_key)
            full_upload = (target_key == target and resource and _safe_pixel_source(root, vals[8], node) and enums_safe
                           and level >= 0 and border == 0 and width > 0 and height > 0)
            if full_upload:
                initialized_textures[texture_key] = (resource, node.end_byte, level)
            else:
                initialized_textures.pop(texture_key, None)
            if (stmt and target_key == target and vals[8].type == 'null' and enums_safe and resource
                    and level >= 0 and border == 0 and width > 0 and height > 0 and width * height <= 1048576):
                edits.append(('texture_storage_duplicate', stmt.start_byte, stmt.end_byte,
                              f'{stmt.text.decode()} {stmt.text.decode()}'))
        if ((name == 'vertexAttribPointer' and len(vals) == 6)
                or (name == 'vertexAttribIPointer' and len(vals) == 5)):
            stride_index, offset_index = (4, 5) if name == 'vertexAttribPointer' else (3, 4)
            size = _integer_argument(vals[1], constants, node)
            stride = _integer_argument(vals[stride_index], constants, node)
            offset = _integer_argument(vals[offset_index], constants, node)
            type_key = _enum_key(vals[2], receiver, node, enum_aliases)
            type_size = {f'{receiver}.{enum}': width for enum, width in (
                ('BYTE', 1), ('UNSIGNED_BYTE', 1), ('SHORT', 2), ('UNSIGNED_SHORT', 2),
                ('HALF_FLOAT', 2), ('INT', 4), ('UNSIGNED_INT', 4), ('FLOAT', 4),
            )}.get(type_key)
            if name == 'vertexAttribIPointer' and type_key in (f'{receiver}.FLOAT', f'{receiver}.HALF_FLOAT'):
                type_size = None
            if offset > 0:
                edits.append(('vertex_attrib_offset', vals[offset_index].start_byte, vals[offset_index].end_byte, '0'))
            if type_size and 1 <= size <= 4 and stride >= size * type_size and stride > 0:
                edits.append(('vertex_attrib_stride', vals[stride_index].start_byte, vals[stride_index].end_byte, '0'))
        if name == 'texSubImage2D' and len(vals) == 9 and not _conditional(node):
            target_key = _enum_key(vals[0], receiver, node, enum_aliases)
            texture_key = (scope, receiver, target_key)
            bound_resource = safe_bound_textures.get(texture_key)
            initialized = initialized_textures.get(texture_key)
            level = _integer_argument(vals[1], constants, node)
            has_helper = initialized and any(initialized[1] <= call.start_byte < node.end_byte
                                             for call in opaque_calls)
            if (not target_key or not bound_resource or not initialized or initialized[0] != bound_resource
                    or initialized[2] != level or has_helper):
                continue
            for arg in vals[4:6]:
                dimension = _integer_argument(arg, constants, node)
                if dimension > 1:
                    edits.append(('texture_subimage_dimension', arg.start_byte, arg.end_byte,
                                  str(max(1, dimension // 2))))
        if name in ('viewport', 'scissor') and len(vals) >= 4:
            for arg in vals[2:4]:
                dimension = _integer_argument(arg, constants, node)
                if dimension > 1:
                    smaller = max(1, dimension // 2)
                    edits.append(('viewport_dimension', arg.start_byte, arg.end_byte, str(smaller)))
        if name in draw_arities and len(vals) == draw_arities[name]:
            if not _conditional(node):
                for key, pending in list(pending_buffer_redefines.items()):
                    if key[1] != receiver or key[0] != scope:
                        continue
                    if key[2] == f'{receiver}.ELEMENT_ARRAY_BUFFER' and name not in indexed_draws:
                        continue
                    sub_stmt, allocation, sub_end = pending
                    helper_between = any(sub_end <= call.start_byte < node.end_byte for call in opaque_calls)
                    if safe_bound_buffers.get(key) == allocation[0] and not helper_between:
                        edits.append(('buffer_redefine_after_upload', sub_stmt.start_byte, sub_stmt.end_byte,
                                      f'{sub_stmt.text.decode()} {allocation[2]}'))
                        pending_buffer_redefines.pop(key, None)
            if draw_mode_safe:
                mode = vals[0]
                current_mode = _enum_key(mode, receiver, node, enum_aliases)
                if current_mode in {f'{receiver}.{value}' for value in valid_modes}:
                    for value in valid_modes:
                        if current_mode != f'{receiver}.{value}':
                            edits.append(('draw_mode', mode.start_byte, mode.end_byte, f'{receiver}.{value}'))
            stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
            if stmt and not _conditional(node):
                statement = stmt.text.decode()
                edits.append(('sync_placement', stmt.start_byte, stmt.end_byte,
                              f'{receiver}.flush(); {statement}'))
                edits.append(('sync_placement', stmt.start_byte, stmt.end_byte,
                              f'{statement} {receiver}.flush();'))
        if name in ('drawArrays', 'drawElements') and len(vals) >= 3:
            arg = vals[1] if name == 'drawElements' else vals[2]
            count = _integer_argument(arg, constants, node)
            if 1 <= count <= 4096:
                for value in _bounded_values(count):
                    edits.append(('bounded_parameter', arg.start_byte, arg.end_byte, str(value)))
        if name == 'drawRangeElements' and len(vals) == 6:
            arg = vals[3]
            count = _integer_argument(arg, constants, node)
            if 1 <= count <= 4096:
                for value in _bounded_values(count):
                    edits.append(('bounded_parameter', arg.start_byte, arg.end_byte, str(value)))
        if name in ('drawArraysInstanced', 'drawElementsInstanced') and len(vals) == (4 if name == 'drawArraysInstanced' else 5):
            count_arg = vals[2] if name == 'drawArraysInstanced' else vals[1]
            instance_arg = vals[3] if name == 'drawArraysInstanced' else vals[4]
            for arg in (count_arg, instance_arg):
                count = _integer_argument(arg, constants, node)
                if 1 <= count <= 4096:
                    for value in _bounded_values(count):
                        edits.append(('bounded_parameter', arg.start_byte, arg.end_byte, str(value)))
        resource_calls = {'bindBuffer', 'bindTexture', 'bindFramebuffer', 'bindVertexArray'}
        if name in resource_calls and not _conditional(node):
            stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
            has_target = name in ('bindBuffer', 'bindTexture', 'bindFramebuffer')
            resource = vals[-1] if vals else None
            target_ok = not has_target or (len(vals) == 2 and _is_safe_enum(vals[0], receiver, node, enum_aliases))
            resource_ok = resource and _is_bound_identifier(root, resource, node)
            if stmt and target_ok and resource_ok:
                null_args = f'{vals[0].text.decode()}, null' if has_target else 'null'
                edits.append(('state_transition', stmt.start_byte, stmt.end_byte,
                              f'{receiver}.{name}({null_args}); {node.text.decode()};'))
        if name == 'shaderSource' and len(vals) == 2 and vals[0].type == 'identifier' and vals[1].type == 'template_string':
            scope_node = node
            stage = None
            while scope_node:
                key = (scope_node.id, vals[0].text, receiver)
                if key in shader_types:
                    stage = shader_types[key]
                    break
                scope_node = scope_node.parent
            template = vals[1]
            if stage and not any(child.type == 'template_substitution' for child in template.named_children):
                shader = template.text[1:-1]
                for kind, start, end, replacement in _glsl_edits(shader, template.start_byte + 1, stage):
                    edits.append((f'glsl_{kind}', start, end, replacement.decode()))
        if name == 'useProgram' and len(vals) == 1 and not _conditional(node) and program_transition_safe:
            stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
            program = vals[0]
            if stmt and program.type == 'identifier' and _is_bound_identifier(root, program, node):
                edits.append(('state_transition', stmt.start_byte, stmt.end_byte,
                              f'{receiver}.useProgram(null); {node.text.decode()};'))
        if name == 'linkProgram' and len(vals) == 1 and not _conditional(node):
            stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
            program = vals[0]
            if (stmt and program.type == 'identifier'
                    and _resolve_created_resource(created_programs, node, program.text) == receiver):
                edits.append(('program_relink_duplicate', stmt.start_byte, stmt.end_byte,
                              f'{stmt.text.decode()} {stmt.text.decode()}'))
    edits.extend(_compatible_texture_update_edits(root, contexts, constants, enum_aliases, calls, opaque_calls))
    edits.extend(_texture_allocation_update_dimensions(root, contexts, constants, enum_aliases, calls, opaque_calls))
    edits.extend(_framebuffer_attachment_cycle_edits(root, contexts, constants, enum_aliases, calls, opaque_calls))
    edits.extend(_framebuffer_retire_edits(root, contexts, enum_aliases, calls, opaque_calls))
    edits.extend(_texture_retire_edits(root, contexts, enum_aliases, calls, opaque_calls))
    edits.extend(_glsl_linked_varying_edits(root, contexts, enum_aliases, calls, opaque_calls))
    return edits


def _validation_edits(js):
    root = parse_js(js)
    contexts = _context_names(root)
    calls = _call_nodes(root, contexts)
    constants = _numeric_constants(root)
    aliases = _enum_aliases(root, contexts)
    created = _created_buffer_bindings(root, contexts)
    backing_sizes = _array_buffer_sizes(root, constants)
    opaque_calls = [call for call in _walk(root) if call.type == 'call_expression'
                    and not (call.child_by_field_name('function')
                             and call.child_by_field_name('function').type == 'member_expression'
                             and call.child_by_field_name('function').child_by_field_name('object')
                             and call.child_by_field_name('function').child_by_field_name('object').text.decode() in contexts)
                    and not (call.child_by_field_name('function')
                             and call.child_by_field_name('function').type == 'member_expression'
                             and call.child_by_field_name('function').child_by_field_name('property')
                             and call.child_by_field_name('function').child_by_field_name('property').text == b'getContext')]
    context_starts = {}
    for declaration in _walk(root):
        if declaration.type != 'variable_declarator':
            continue
        name = declaration.child_by_field_name('name')
        value = declaration.child_by_field_name('value')
        if (name and name.type == 'identifier' and name.text.decode() in contexts
                and _direct_context_initializer(value)):
            context_starts[name.text.decode()] = declaration.end_byte
    widths = {'Uint8Array': 1, 'Uint8ClampedArray': 1, 'Int8Array': 1,
              'Uint16Array': 2, 'Int16Array': 2,
              'Uint32Array': 4, 'Int32Array': 4, 'Float32Array': 4,
              'Float64Array': 8}
    candidates = []
    bound, allocated = {}, {}
    clean_prefix = {}
    for name, args, node in calls:
        vals = args.named_children
        scope = _scope_key(node)
        fn = node.child_by_field_name('function')
        receiver = fn.child_by_field_name('object').text.decode()
        clean_key = (scope, receiver)
        if name not in {'createBuffer', 'bindBuffer', 'bufferData', 'bufferSubData'}:
            clean_prefix[clean_key] = False
        if name == 'createBuffer' and (vals or _conditional(node)):
            clean_prefix[clean_key] = False
        target = _enum_key(vals[0], receiver, node, aliases) if vals else None
        if name == 'bindBuffer':
            key = (scope, receiver, f'{receiver}.ARRAY_BUFFER')
            stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
            valid_resource = (len(vals) == 2 and (vals[1].type == 'null'
                              or vals[1].type == 'identifier'
                              and _resolve_created_resource(created, node, vals[1].text) == receiver))
            if (target == f'{receiver}.ARRAY_BUFFER' and valid_resource and not _conditional(node)
                    and stmt):
                resource = vals[1]
                bound[key] = (resource.text if resource.type == 'identifier'
                              and _resolve_created_resource(created, node, resource.text) == receiver else None)
            elif target == f'{receiver}.ARRAY_BUFFER':
                clean_prefix[clean_key] = False
                bound.pop(key, None)
            elif target in (None, f'{receiver}.ARRAY_BUFFER'):
                clean_prefix[clean_key] = False
                bound.pop(key, None)
            continue
        if name == 'bufferData':
            key = (scope, receiver, f'{receiver}.ARRAY_BUFFER')
            resource = bound.get(key)
            if target == f'{receiver}.ARRAY_BUFFER' and resource:
                allocated.pop((scope, receiver, resource), None)
                stmt = node.parent if node.parent and node.parent.type == 'expression_statement' else None
                if len(vals) == 3 and not _conditional(node) and stmt:
                    size = _integer_argument(vals[1], constants, node)
                    if (1 <= size <= 16 * 1024 * 1024
                            and _is_safe_enum(vals[2], receiver, node, aliases)):
                        allocated[(scope, receiver, resource)] = (size, node.end_byte)
                    else:
                        clean_prefix[clean_key] = False
                else:
                    clean_prefix[clean_key] = False
            elif target is None:
                clean_prefix[clean_key] = False
                allocated = {key: value for key, value in allocated.items() if key[1] != receiver}
                bound.pop(key, None)
            elif target == f'{receiver}.ARRAY_BUFFER':
                clean_prefix[clean_key] = False
            else:
                clean_prefix[clean_key] = False
            continue
        if name != 'bufferSubData' or (len(vals) != 3 or _conditional(node) or not node.parent
                                        or node.parent.type != 'expression_statement'):
            continue
        if target != f'{receiver}.ARRAY_BUFFER':
            continue
        resource = bound.get((scope, receiver, target))
        if not resource or _resolve_created_resource(created, node, resource) != receiver:
            continue
        allocation = allocated.get((scope, receiver, resource))
        if not allocation:
            continue
        offset = _integer_argument(vals[1], constants, node)
        data = vals[2]
        constructor = data.child_by_field_name('constructor') if data.type == 'new_expression' else None
        data_args = data.child_by_field_name('arguments') if data.type == 'new_expression' else None
        data_values = data_args.named_children if data_args else []
        if not constructor or constructor.type != 'identifier' or not data_values:
            continue
        type_name = constructor.text.decode()
        width = widths.get(type_name)
        if not width or not _unshadowed_builtin(root, node, type_name):
            continue
        byte_length = -1
        if len(data_values) == 1 and data_values[0].type in ('number', 'identifier'):
            length = _integer_argument(data_values[0], constants, node)
            if length > 0:
                byte_length = length * width
        elif len(data_values) == 1 and data_values[0].type == 'array':
            literal = data_values[0].text.decode('utf-8')
            number = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
            if re.fullmatch(r'\[\s*' + number + r'(?:\s*,\s*' + number + r')*\s*,?\s*\]', literal):
                byte_length = len(re.findall(number, literal)) * width
        elif (len(data_values) == 3 and data_values[0].type == 'identifier'):
            backing_size = _resolve_array_buffer_size(backing_sizes, node, data_values[0].text)
            view_offset = _integer_argument(data_values[1], constants, node)
            view_length = _integer_argument(data_values[2], constants, node)
            if (backing_size > 0 and view_offset >= 0 and view_length > 0
                    and view_offset % width == 0 and view_offset + view_length * width <= backing_size):
                byte_length = view_length * width
        size, allocation_end = allocation
        if not 0 <= offset < size or byte_length <= 0 or offset + byte_length > size:
            continue
        if not clean_prefix.get(clean_key, True):
            continue
        if any(prior.start_byte < node.start_byte and _scope_key(prior) == scope
               and prior.child_by_field_name('function').child_by_field_name('property').text.decode()
               not in {'createBuffer', 'bindBuffer', 'bufferData'}
               for _, _, prior in calls
               if prior.child_by_field_name('function').child_by_field_name('object').text.decode() == receiver):
            continue
        if any(prior.start_byte < node.start_byte and _scope_key(prior) != scope
               for _, _, prior in calls
               if prior.child_by_field_name('function').child_by_field_name('object').text.decode() == receiver):
            continue
        if any(context_starts.get(receiver, node.start_byte) <= call.start_byte < node.start_byte
               for call in opaque_calls):
            continue
        if any(prior.start_byte >= context_starts.get(receiver, node.start_byte)
               and prior.start_byte < node.start_byte and _scope_key(prior) != scope
               for _, _, prior in calls):
            continue
        stmt = node.parent
        replacement = stmt.text
        local_start = vals[1].start_byte - stmt.start_byte
        local_end = vals[1].end_byte - stmt.start_byte
        replacement = (replacement[:local_start] + str(size).encode() + replacement[local_end:]
                       + f' window.__validationError = {receiver}.getError();'.encode())
        candidates.append(('buffer_subdata_boundary_validation', stmt.start_byte, stmt.end_byte,
                           replacement.decode()))
        return candidates
    return candidates


def _edit_owner(root, start, end):
    owners = [node for node in _walk(root) if node.type == 'expression_statement'
              and node.start_byte <= start and end <= node.end_byte]
    return min(owners, key=lambda node: node.end_byte - node.start_byte).id if owners else (start, end)


def _apply_edits(raw, edits):
    spans = []
    for edit in edits:
        if 'spans' in edit:
            spans.extend(edit['spans'])
        else:
            spans.append(edit)
    for span in sorted(spans, key=lambda item: item['start'], reverse=True):
        raw = raw[:span['start']] + span['replacement'].encode() + raw[span['end']:]
    return raw


def _edit_spans(edit):
    return edit.get('spans', [edit])


def candidate_families(source):
    """Expose existing valid edit sites grouped by operator for profiling."""
    source_bytes = source.encode('utf-8') if isinstance(source, str) else source
    match, js = _script(source_bytes)
    if not _valid(js):
        raise ValueError('input JavaScript does not parse')
    groups = {}
    for candidate in _edits(js):
        if len(candidate) == 2:
            operator, raw_spans = candidate
            edit = {'operator': operator, 'spans': [
                {'start': start, 'end': end, 'replacement': replacement}
                for start, end, replacement in raw_spans]}
        else:
            operator, start, end, replacement = candidate
            edit = {'operator': operator, 'start': start, 'end': end,
                    'replacement': replacement}
        groups.setdefault(operator, []).append(edit)
    return groups


def apply_candidate(source, edit):
    """Apply one previously enumerated candidate and return HTML plus replay metadata."""
    source_is_text = isinstance(source, str)
    source_bytes = source.encode('utf-8') if source_is_text else source
    match, js = _script(source_bytes)
    raw = _apply_edits(js.encode('utf-8'), [edit])
    decoded = raw.decode('utf-8')
    if raw == js.encode('utf-8') or not _valid(decoded):
        raise ValueError('candidate did not produce a valid edit')
    result = source_bytes[:match.start('body')] + raw + source_bytes[match.end('body'):]
    return result.decode('utf-8') if source_is_text else result


def mutate_bytes(source, rng, max_edits=1, arm='valid'):
    if not 1 <= max_edits <= 3:
        raise ValueError('max_edits must be between 1 and 3')
    if arm not in ('valid', 'validation'):
        raise ValueError("arm must be 'valid' or 'validation'")
    match, js = _script(source)
    if not _valid(js):
        raise ValueError('input JavaScript does not parse')
    root = parse_js(js)
    raw = js.encode('utf-8')
    if arm == 'validation':
        candidates = _validation_edits(js)
        rng.shuffle(candidates)
        for operator, start, end, replacement in candidates:
            edit = {'operator': operator, 'start': start, 'end': end, 'replacement': replacement}
            changed = _apply_edits(raw, [edit])
            try:
                decoded = changed.decode('utf-8')
            except UnicodeDecodeError:
                continue
            if changed != raw and _valid(decoded):
                return source[:match.start('body')] + changed + source[match.end('body'):], [edit]
        raise ValueError('no applicable validation mutation')
    candidates = _edits(js)
    groups = {}
    for edit in candidates:
        groups.setdefault(edit[0], []).append(edit)
    families = sorted(groups)
    rng.shuffle(families)
    options = []
    for family in families:
        rng.shuffle(groups[family])
        options.extend(groups[family])
    selected, owners = [], set()
    for candidate in options:
        if len(selected) >= max_edits:
            break
        if len(candidate) == 2:
            operator, raw_spans = candidate
            spans = [{'start': start, 'end': end, 'replacement': replacement}
                     for start, end, replacement in raw_spans]
            edit = {'operator': operator, 'spans': spans}
        else:
            operator, start, end, replacement = candidate
            spans = [{'start': start, 'end': end, 'replacement': replacement}]
            edit = {'operator': operator, 'start': start, 'end': end, 'replacement': replacement}
        if any(span['start'] < existing['end'] and existing['start'] < span['end']
               for span in spans for item in selected for existing in _edit_spans(item)):
            continue
        edit_owners = {_edit_owner(root, span['start'], span['end']) for span in spans}
        if edit_owners & owners:
            continue
        candidate = selected + [edit]
        changed = _apply_edits(raw, candidate)
        try:
            decoded = changed.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if not _valid(decoded) or changed == raw:
            continue
        selected.append(edit)
        owners.update(edit_owners)
    if not selected:
        raise ValueError('no applicable valid mutation')
    changed = _apply_edits(raw, selected)
    return source[:match.start('body')] + changed + source[match.end('body'):], selected


def replay(source, metadata):
    match, js = _script(source)
    edits = metadata['edits']
    raw = _apply_edits(js.encode('utf-8'), edits)
    if not _valid(raw.decode('utf-8')):
        raise ValueError('replayed output does not parse')
    return source[:match.start('body')] + raw + source[match.end('body'):]


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _output_path(seed, output, index):
    value = str(output)
    if '%n' in value:
        return Path(value.replace('%n', str(index)))
    path = Path(value)
    return path / f'{seed.stem}_{index}{seed.suffix}'


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('seeds', nargs='*', type=Path)
    parser.add_argument('-n', type=int, default=1)
    parser.add_argument('-s', type=int, default=0)
    parser.add_argument('-o', required=True)
    parser.add_argument('--replay', type=Path)
    parser.add_argument('--max-edits', type=int, choices=range(1, 4), default=1)
    parser.add_argument('--arm', choices=('valid', 'validation'), default='valid')
    args = parser.parse_args(argv)
    if args.replay:
        meta = json.loads(args.replay.read_text())
        seed = Path(meta['source_path'])
        sources = [(seed, seed.read_bytes(), meta)]
        count = 1
    else:
        if not args.seeds or args.n < 1:
            parser.error('provide seed files and positive -n')
        sources = [(p, p.read_bytes(), None) for p in args.seeds]
        count = args.n
    outarg = args.o
    output = Path(outarg)
    pending = []
    destinations = set()
    output_index = 0
    for seed, original, replay_meta in sources:
        for i in range(count):
            rng = random.Random(args.s + i)
            if replay_meta:
                if replay_meta.get('source_sha256') != _hash(original):
                    raise ValueError('replay source hash mismatch')
                result = replay(original, replay_meta)
                if replay_meta.get('output_sha256') != _hash(result):
                    raise ValueError('replay output hash mismatch')
                edits = replay_meta['edits']
                output_arm = replay_meta.get('arm', args.arm)
            else:
                result, edits = mutate_bytes(original, rng, args.max_edits, arm=args.arm)
                output_arm = args.arm
            dest = _output_path(seed, output, output_index)
            output_index += 1
            sidecar = dest.with_suffix('.mutation.json')
            dest_key, sidecar_key = dest.resolve(), sidecar.resolve()
            if dest_key == sidecar_key or dest_key in destinations or sidecar_key in destinations or dest.exists() or sidecar.exists():
                raise FileExistsError(f'output exists: {dest}')
            meta = {'source_path': str(seed.resolve()), 'source_sha256': _hash(original), 'seed': args.s + i,
                    'edits': edits, 'output_sha256': _hash(result), 'arm': output_arm}
            if output_arm == 'validation':
                meta['expected_error'] = 'INVALID_VALUE'
            destinations.update((dest_key, sidecar_key))
            pending.append((dest, sidecar, result, meta))
    for dest, sidecar, result, meta in pending:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(result)
        sidecar.write_text(json.dumps(meta, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)

"""Reduce bounded WebGL profiles into executed values and resource flows."""

from collections import Counter, defaultdict
import json


REDUCER_VERSION = "webgl-flow-3"
_ENUM = {
    34962: "ARRAY_BUFFER", 34963: "ELEMENT_ARRAY_BUFFER", 35051: "PIXEL_PACK_BUFFER",
    35052: "PIXEL_UNPACK_BUFFER", 35345: "UNIFORM_BUFFER", 35982: "TRANSFORM_FEEDBACK_BUFFER",
    36662: "COPY_READ_BUFFER", 36663: "COPY_WRITE_BUFFER", 3553: "TEXTURE_2D",
    34067: "TEXTURE_CUBE_MAP", 32879: "TEXTURE_3D", 35866: "TEXTURE_2D_ARRAY",
    36160: "FRAMEBUFFER", 36008: "READ_FRAMEBUFFER", 36009: "DRAW_FRAMEBUFFER",
    36064: "COLOR_ATTACHMENT0", 36096: "DEPTH_ATTACHMENT",
    36161: "RENDERBUFFER",
    5121: "UNSIGNED_BYTE", 5123: "UNSIGNED_SHORT", 5125: "UNSIGNED_INT",
    0: "POINTS", 1: "LINES", 2: "LINE_LOOP", 3: "LINE_STRIP", 4: "TRIANGLES",
    5: "TRIANGLE_STRIP", 6: "TRIANGLE_FAN", 35040: "STREAM_DRAW", 35041: "STREAM_READ",
    35042: "STREAM_COPY", 35044: "STATIC_DRAW", 35045: "STATIC_READ", 35046: "STATIC_COPY",
    35048: "DYNAMIC_DRAW", 35049: "DYNAMIC_READ", 35050: "DYNAMIC_COPY",
}


def _id(value):
    return value.get("id") if isinstance(value, dict) else None


def _arg(event, index, default=None):
    args = event.get("args") or []
    return args[index] if len(args) > index else default


def _captured_slice(value, offset, count):
    if (not isinstance(value, dict) or value.get("kind") not in ("view", "array") or
            value.get("truncated") or not isinstance(value.get("values"), list) or
            not isinstance(offset, (int, float)) or not isinstance(count, (int, float)) or
            offset < 0 or count < 0 or int(offset) != offset or int(count) != count):
        return None
    values = value["values"]
    if offset + count > len(values) or any(not isinstance(item, (int, float)) for item in values[offset:offset + count]):
        return None
    return values[offset:offset + count]


def _enum(value):
    return _ENUM.get(value, value)


def _count_class(value):
    if not isinstance(value, (int, float)):
        return "unknown"
    if value == 0:
        return "zero"
    if value == 1:
        return "one"
    return "positive" if value > 0 else "negative"


def _size_class(size):
    if not isinstance(size, (int, float)) or size < 0:
        return "unknown"
    if size == 0:
        return "zero"
    if size <= 256:
        return "tiny"
    if size <= 4096:
        return "small"
    if size <= 65536:
        return "medium"
    if size <= 1048576:
        return "large"
    return "very_large"


def _view_size(value, args, offset_index=None, length_index=None):
    if not isinstance(value, dict) or value.get("kind") != "view":
        return value if isinstance(value, (int, float)) else None
    widths = {"Int8Array": 1, "Uint8Array": 1, "Uint8ClampedArray": 1, "Int16Array": 2,
              "Uint16Array": 2, "Int32Array": 4, "Uint32Array": 4, "Float32Array": 4,
              "Float64Array": 8, "BigInt64Array": 8, "BigUint64Array": 8}
    width = widths.get(value.get("type"))
    length = value.get("length")
    if width is None or not isinstance(length, (int, float)):
        return value.get("byte_length") if offset_index is None and length_index is None else None
    offset = args[offset_index] if offset_index is not None and len(args) > offset_index else 0
    count = args[length_index] if length_index is not None and len(args) > length_index else length - offset
    if not isinstance(offset, (int, float)) or not isinstance(count, (int, float)):
        return None
    if offset < 0 or count < 0 or offset + count > length:
        return None
    return count * width


def _positive_draws(event):
    """Return the positive subdraw count, retaining zero-work calls elsewhere."""
    method, args = event.get("method", ""), event.get("args") or []
    if method.startswith("multiDraw"):
        elements = "Elements" in method
        instanced = "Instanced" in method
        count_index, count_offset_index, instance_index, instance_offset_index, drawcount_index = (
            (1, 2, 6, 7, 8) if elements and instanced else
            (1, 2, None, None, 6) if elements else
            (3, 4, 5, 6, 7) if instanced else (3, 4, None, None, 5))
        counts = args[count_index] if len(args) > count_index else None
        offset = args[count_offset_index] if len(args) > count_offset_index else 0
        drawcount = args[drawcount_index] if len(args) > drawcount_index else 0
        if not isinstance(drawcount, (int, float)) or drawcount < 0:
            return None
        values = _captured_slice(counts, offset, drawcount)
        if values is None:
            return None
        if not instanced:
            return sum(1 for value in values if isinstance(value, (int, float)) and value > 0)
        instances = args[instance_index] if len(args) > instance_index else None
        instance_offset = args[instance_offset_index] if len(args) > instance_offset_index else 0
        instance_values = _captured_slice(instances, instance_offset, drawcount)
        if instance_values is None:
            return None
        return sum(1 for count, instance_count in zip(values, instance_values)
                   if isinstance(count, (int, float)) and count > 0 and
                   isinstance(instance_count, (int, float)) and instance_count > 0)
    if method.startswith("draw"):
        elements = "Elements" in method
        if "Instanced" in method:
            count_index, instance_index = (1, 4) if elements else (2, 3)
            count = args[count_index] if len(args) > count_index else None
            instances = args[instance_index] if len(args) > instance_index else None
            if not isinstance(count, (int, float)) or not isinstance(instances, (int, float)):
                return None
            return int(count > 0 and instances > 0)
        count_index = 3 if "Range" in method else 1 if elements else 2
        count = args[count_index] if len(args) > count_index else None
        return int(count > 0) if isinstance(count, (int, float)) else None
    return 0


def _value_classes(method, args, positive):
    values = set()
    if method.startswith("multiDraw"):
        values.add(f"positive_subdraws:{'zero' if positive == 0 else 'one' if positive == 1 else 'few' if isinstance(positive, int) and positive <= 4 else 'many' if isinstance(positive, int) else 'unknown'}")
    if method.startswith("draw"):
        count_index = 3 if "Range" in method else 1 if "Elements" in method else 2
        if len(args) > count_index:
            values.add(f"draw_count:{_count_class(args[count_index])}")
        if args:
            values.add(f"draw_mode:{_enum(args[0])}")
        if "Elements" in method:
            type_index = 4 if "Range" in method else 2
            if len(args) > type_index:
                values.add(f"index_type:{_enum(args[type_index])}")
        if "Instanced" in method and len(args) > (4 if "Elements" in method else 3):
            instance_index = 4 if "Elements" in method else 3
            values.add(f"instance_count:{_count_class(args[instance_index])}")
    if method.startswith("multiDraw"):
        elements = "Elements" in method
        instanced = "Instanced" in method
        count_index, draw_index, instance_index = ((1, 8, 6) if elements and instanced else
                                                    (1, 6, None) if elements else
                                                    (3, 7, 5) if instanced else (3, 5, None))
        counts = args[count_index] if len(args) > count_index else None
        count_offset_index = 2 if elements else 4
        count_offset = args[count_offset_index] if len(args) > count_offset_index else 0
        drawcount = args[draw_index] if len(args) > draw_index else None
        count_values = _captured_slice(counts, count_offset, drawcount) if isinstance(drawcount, (int, float)) else None
        if count_values is not None:
            values.add("multi_draw_counts:mixed_zero_positive" if any(v > 0 for v in count_values) and any(v == 0 for v in count_values)
                       else "multi_draw_counts:positive" if any(v > 0 for v in count_values)
                       else "multi_draw_counts:zero" if count_values else "multi_draw_counts:unknown")
        values.add(f"draw_count:{_count_class(drawcount)}")
        if args:
            values.add(f"draw_mode:{_enum(args[0])}")
        if elements and len(args) > 3:
            values.add(f"index_type:{_enum(args[3])}")
        if instanced and instance_index is not None and len(args) > instance_index:
            instances = args[instance_index]
            instance_offset_index = 7 if elements else 6
            instance_offset = args[instance_offset_index] if len(args) > instance_offset_index else 0
            instance_values = _captured_slice(instances, instance_offset, drawcount) if isinstance(drawcount, (int, float)) else None
            if instance_values is not None:
                classes = {_count_class(value) for value in instance_values}
                values.add("instance_count:mixed_zero_positive" if "zero" in classes and "positive" in classes or "zero" in classes and "one" in classes
                           else f"instance_count:{next(iter(classes))}" if len(classes) == 1 else "instance_count:mixed")
    if method == "bufferData" and len(args) > 1:
        value = args[1]
        size = _view_size(value, args, 3 if len(args) > 3 else None, 4 if len(args) > 4 else None)
        values.add(f"buffer_allocation:{_size_class(size)}")
        if len(args) > 2:
            values.add(f"buffer_usage:{_enum(args[2])}")
        values.add(f"buffer_target:{_enum(args[0])}")
    if method == "bufferSubData" and len(args) > 2:
        size = _view_size(args[2], args, 3 if len(args) > 3 else None, 4 if len(args) > 4 else None)
        values.add(f"buffer_upload:{_size_class(size)}")
        values.add(f"buffer_target:{_enum(args[0])}")
    if method == "bufferData":
        values.add(f"buffer_data_overload:{'size' if isinstance(args[1], (int, float)) else 'data' if len(args) > 1 and isinstance(args[1], dict) else 'unknown'}")
    if method in ("texImage2D", "texImage3D", "texSubImage2D", "texSubImage3D"):
        target = _enum(args[0]) if args else "unknown"
        values.add(f"texture_target:{target}")
    return values


def _runtime_overload(method, args, surface, context_version):
    method_data = surface.get("methods", {}).get(method, {})
    overloads = [item for item in method_data.get("overloads", [])
                 if item.get("webgl_version", method_data.get("webgl_version", 1)) <= context_version
                 and item.get("arity", len(item.get("params", []))) <= len(args) <= len(item.get("params", []))]
    if method == "bufferData" and len(args) > 1:
        value = args[1]
        kind = "size" if isinstance(value, (int, float)) else "data" if isinstance(value, dict) else None
        if kind is None:
            return None
        overloads = [item for item in overloads if len(item.get("params", [])) > 1 and
                     item["params"][1].get("name") in (("size",) if kind == "size" else ("data", "srcData"))]
    if len(overloads) != 1:
        return None
    from .value_classes import overload_requirement
    return overload_requirement(method, overloads[0])


def _sampler_target(sampler_type):
    return {35678: "TEXTURE_2D", 35682: "TEXTURE_2D", 36298: "TEXTURE_2D", 36306: "TEXTURE_2D",
            35680: "TEXTURE_CUBE_MAP", 35683: "TEXTURE_CUBE_MAP", 36300: "TEXTURE_CUBE_MAP",
            36308: "TEXTURE_CUBE_MAP", 35679: "TEXTURE_3D", 36299: "TEXTURE_3D", 36307: "TEXTURE_3D",
            36289: "TEXTURE_2D_ARRAY", 36292: "TEXTURE_2D_ARRAY", 36303: "TEXTURE_2D_ARRAY",
            36311: "TEXTURE_2D_ARRAY"}.get(sampler_type)


def _semantic_sampler(reflection, program, generation, name):
    if (not isinstance(name, str) or not reflection or
            reflection.get("generation") != generation):
        return None
    for sampler in (reflection or {}).get("samplers", []):
        locations = sampler.get("locations", [sampler.get("location")])
        base = sampler.get("name", "")
        for index, location in enumerate(locations):
            if isinstance(location, dict) and name == location.get("name"):
                return (program, generation, base, index)
        if name == base or name == base.removesuffix("[0]"):
            return (program, generation, base, 0)
    return None


def reduce_trace(profile, surface=None):
    """Reduce a profile without guessing when object or state evidence is missing."""
    events = profile.get("events") or []
    methods, extension_methods, overloads, values = set(), defaultdict(set), set(), set()
    flows, unresolved = set(), set()
    flow_events = defaultdict(int)
    repetitions = Counter()
    states = {}
    program_reflections = {}
    uniform_programs = {}
    resource_storage = defaultdict(int)
    resource_sizes = {}
    context_versions = {item.get("id"): item.get("version") for item in profile.get("contexts", [])}
    resource_roles = {}
    role_counts = Counter()
    transitions = []

    def role(value):
        identifier = _id(value)
        if not identifier:
            return None
        if identifier not in resource_roles:
            kind = value.get("kind", "object") if isinstance(value, dict) else "object"
            prefix = {"buffer": "b", "vao": "v", "program": "p", "texture": "t",
                      "framebuffer": "f", "renderbuffer": "r", "sampler": "s"}.get(kind, "o")
            role_counts[prefix] += 1
            resource_roles[identifier] = f"{prefix}{role_counts[prefix]}"
        return resource_roles[identifier]

    def transition(*parts):
        item = list(parts)
        if not transitions or transitions[-1] != item:
            transitions.append(item)

    def context_state(cid):
        return states.setdefault(cid, {
        "buffers": {}, "vaos": {None: {"attributes": {}, "element": None}}, "vao": None,
        "program": None, "textures": {0: {}}, "active_texture": 0,
        "framebuffer": None, "read_framebuffer": None,
        "texture_attachments": defaultdict(dict), "last_draw": {}, "flow_counts": Counter(),
        "texture_generations": defaultdict(int), "uploaded_textures": set(), "rendered_textures": set(),
        "sampler_units": {},
        })

    def vao(st):
        return st["vaos"].setdefault(st["vao"], {"attributes": {}, "element": None})

    def target_buffer(st, target):
        target = _enum(target)
        if target == "ELEMENT_ARRAY_BUFFER":
            return vao(st).get("element")
        return st["buffers"].get(target)

    def framebuffer_for(st, target):
        target = _enum(target)
        if target in ("FRAMEBUFFER", "DRAW_FRAMEBUFFER"):
            return st.get("framebuffer")
        if target == "READ_FRAMEBUFFER":
            return st.get("read_framebuffer")
        return None

    positive_draw_count = 0
    blocking_outcomes = {"missing_completion", "context_lost", "seed_webgl_error",
                         "remaining_webgl_error", "error_drain_incomplete", "event_buffer_full",
                         "outcome_buffer_full", "profiler_error", "navigation_failed", "runner_error",
                         "no_positive_work_draw"}
    clean_profile = (not profile.get("truncated") and
                     not any(item.get("code") in blocking_outcomes for item in profile.get("outcomes", [])) and
                     all(not e.get("threw") for e in events))
    for event in events:
        cid = event.get("context")
        method, ext = event.get("method", ""), event.get("extension")
        if not cid or not method:
            unresolved.add("event_identity")
            continue
        (extension_methods[ext] if ext else methods).add(method)
        args = event.get("args") or []
        version = context_versions.get(cid)
        if not ext and surface and version:
            overload = _runtime_overload(method, args, surface, version)
            if overload:
                overloads.add(overload)
            elif method in surface.get("methods", {}):
                unresolved.add(f"overload:{method}")
        st = context_state(cid)
        pos = _positive_draws(event)
        if method.startswith("multiDraw") and pos is None:
            unresolved.add("multi_draw_selection")
        values.update(_value_classes(method, args, pos))

        if method == "bindBuffer":
            target, buffer = (_enum(_arg(event, 0)), _id(_arg(event, 1)))
            bound = vao(st).get("element") if target == "ELEMENT_ARRAY_BUFFER" else st["buffers"].get(target)
            if buffer is None and bound and st.get("last_draw") and any(item[1] == bound for item in st["last_draw"]["attrs"]):
                st["unbound_after_use"] = bound
            elif buffer and st.get("unbound_after_use") == buffer:
                flows.add("resource_unbind_rebind_after_use")
                flow_events[(cid, "resource_unbind_rebind_after_use")] += 1
                st.pop("unbound_after_use", None)
            if target == "ELEMENT_ARRAY_BUFFER":
                vao(st)["element"] = buffer
            elif target:
                st["buffers"][target] = buffer
            transition("bind_buffer", target, role(_arg(event, 1)))
        elif method == "bindVertexArray":
            st["vao"] = _id(_arg(event, 0))
            vao(st)
            transition("bind_vao", role(_arg(event, 0)))
        elif method == "vertexAttribPointer":
            index, buffer = _arg(event, 0), target_buffer(st, "ARRAY_BUFFER")
            if not isinstance(index, int) or not buffer:
                unresolved.add("attribute_pointer_binding")
            else:
                vao(st)["attributes"].setdefault(index, {"enabled": False, "divisor": 0}).update(
                    {"buffer": buffer, "storage": resource_storage[buffer]})
                transition("attribute_pointer", index, role({"id": buffer, "kind": "buffer"}),
                           _size_class(_arg(event, 4)), _size_class(_arg(event, 5)))
        elif method == "vertexAttribIPointer":
            index, buffer = _arg(event, 0), target_buffer(st, "ARRAY_BUFFER")
            if isinstance(index, int) and buffer:
                vao(st)["attributes"].setdefault(index, {"enabled": False, "divisor": 0}).update(
                    {"buffer": buffer, "storage": resource_storage[buffer]})
                transition("attribute_pointer", index, role({"id": buffer, "kind": "buffer"}),
                           _size_class(_arg(event, 4)), _size_class(_arg(event, 5)))
            else:
                unresolved.add("attribute_pointer_binding")
        elif method in ("enableVertexAttribArray", "disableVertexAttribArray"):
            index = _arg(event, 0)
            if isinstance(index, int):
                vao(st)["attributes"].setdefault(index, {"buffer": None, "divisor": 0})["enabled"] = method.startswith("enable")
                transition("attribute_enable" if method.startswith("enable") else "attribute_disable", index)
            else:
                unresolved.add("attribute_index")
        elif method == "vertexAttribDivisor" or method == "vertexAttribDivisorANGLE":
            index, divisor = _arg(event, 0), _arg(event, 1)
            if isinstance(index, int) and isinstance(divisor, (int, float)):
                vao(st)["attributes"].setdefault(index, {"buffer": None, "enabled": False})["divisor"] = divisor
                transition("attribute_divisor", index, _count_class(divisor))
        elif method == "bufferData":
            buffer = target_buffer(st, _arg(event, 0))
            if buffer:
                drawn_before = bool(st.get("last_draw") and any(item[1] == buffer for item in st["last_draw"]["attrs"]))
                resource_storage[buffer] += 1
                value = _arg(event, 1)
                size = _view_size(value, args, 3 if len(args) > 3 else None, 4 if len(args) > 4 else None)
                old_size = resource_sizes.get(buffer)
                if old_size is not None and size is not None:
                    values.add(f"buffer_replacement:{'shrink' if size < old_size else 'grow' if size > old_size else 'same'}")
                elif old_size is None:
                    values.add("buffer_replacement:initial")
                resource_sizes[buffer] = size
                transition("buffer_data", _enum(_arg(event, 0)), role({"id": buffer, "kind": "buffer"}),
                           resource_storage[buffer], _size_class(size))
                if drawn_before:
                    st["last_replacement"] = (buffer, resource_storage[buffer], _size_class(size))
            else:
                unresolved.add("buffer_data_binding")
        elif method == "bufferSubData":
            buffer = target_buffer(st, _arg(event, 0))
            offset = _arg(event, 1)
            size = _view_size(_arg(event, 2), args, 3 if len(args) > 3 else None,
                              4 if len(args) > 4 else None)
            allocation = resource_sizes.get(buffer)
            if (buffer and isinstance(offset, (int, float)) and isinstance(size, (int, float)) and
                    isinstance(allocation, (int, float))):
                if offset < 0 or size < 0 or offset + size > allocation:
                    offset_class = "out_of_bounds"
                elif offset == 0:
                    offset_class = "zero"
                elif offset + size == allocation:
                    offset_class = "end"
                else:
                    offset_class = "interior"
                values.add(f"buffer_subdata_offset:{offset_class}")
            else:
                values.add("buffer_subdata_offset:unknown")
                unresolved.add("buffer_subdata_bounds")
            transition("buffer_sub_data", _enum(_arg(event, 0)), role(_arg(event, 2)),
                       _size_class(offset), _size_class(size))
        elif method == "useProgram":
            st["program"] = _id(_arg(event, 0))
            transition("use_program", role(_arg(event, 0)))
        elif method == "linkProgram":
            program = _id(_arg(event, 0))
            reflection = event.get("reflection")
            for location, info in list(uniform_programs.items()):
                if info[0] == program:
                    del uniform_programs[location]
            st["sampler_units"] = {key: value for key, value in st["sampler_units"].items() if key[0] != program}
            program_reflections.pop(program, None)
            if program and isinstance(reflection, dict) and reflection.get("status") == "linked" and reflection.get("complete") is True:
                generation = reflection.get("generation")
                program_reflections[program] = {**reflection, "generation": generation}
                for sampler in reflection.get("samplers", []):
                    locations = sampler.get("locations", [sampler.get("location")])
                    for index, loc in enumerate(locations):
                        if _id(loc):
                            semantic = (program, generation, sampler.get("name"), index)
                            uniform_programs[_id(loc)] = (program, generation, sampler.get("name"), sampler.get("type"), semantic)
                            st["sampler_units"][semantic] = 0
                transition("link_program", role(_arg(event, 0)), generation, "linked")
            elif program:
                unresolved.add("program_link_reflection")
                if isinstance(reflection, dict):
                    unresolved.update(f"reflection:{item}" for item in reflection.get("unresolved", []))
                transition("link_program", role(_arg(event, 0)), "unknown")
        elif method == "getUniformLocation":
            loc = _id(event.get("result"))
            if loc:
                name = _arg(event, 1)
                program = _id(_arg(event, 0))
                generation = event.get("result", {}).get("generation") if isinstance(event.get("result"), dict) else None
                reflection = program_reflections.get(program)
                if reflection and generation == reflection.get("generation"):
                    semantic = _semantic_sampler(reflection, program, generation, name)
                    sampler = next((item for item in reflection.get("samplers", [])
                                    if semantic and item.get("name") == semantic[2]), None)
                    if sampler:
                        uniform_programs[loc] = (program, generation, sampler.get("name"), sampler.get("type"), semantic)
        elif method.startswith("uniform") and method.endswith(("i", "iv")):
            loc = _id(_arg(event, 0))
            if method == "uniform1i" and loc and len(args) > 1:
                info = uniform_programs.get(loc)
                if info and info[0] == st["program"]:
                    reflection = program_reflections.get(info[0])
                    location = _arg(event, 0)
                    generation = location.get("generation") if isinstance(location, dict) else info[1]
                    if reflection and generation == reflection.get("generation"):
                        st["sampler_units"][info[4]] = _arg(event, 1)
                    else:
                        unresolved.add("stale_uniform_location")
                elif loc:
                    location = _arg(event, 0)
                    program = location.get("program") if isinstance(location, dict) else st["program"]
                    reflection = program_reflections.get(program)
                    generation = location.get("generation") if isinstance(location, dict) else None
                    semantic = _semantic_sampler(reflection, program, generation,
                                                 location.get("name") if isinstance(location, dict) else None)
                    if semantic and program == st["program"]:
                        sampler = next(item for item in reflection["samplers"] if item.get("name") == semantic[2])
                        st["sampler_units"][semantic] = _arg(event, 1)
                        uniform_programs[loc] = (program, generation, semantic[2], sampler.get("type"), semantic)
                    else:
                        unresolved.add("stale_uniform_location" if reflection and isinstance(location, dict) and
                                       generation != reflection.get("generation") else "unknown_uniform_location")
            elif method == "uniform1iv":
                loc = _id(_arg(event, 0))
                info = uniform_programs.get(loc)
                view = _arg(event, 1)
                reflection = program_reflections.get(info[0]) if info else None
                upload_offset = _arg(event, 2, 0)
                upload_length = _arg(event, 3, None)
                if upload_length is None and isinstance(view, dict):
                    upload_length = view.get("length", len(view.get("values", []))) - upload_offset
                upload_values = _captured_slice(view, upload_offset, upload_length)
                if (info and info[0] == st["program"] and reflection and upload_values is not None):
                    sampler = next((sampler for sampler in reflection.get("samplers", [])
                                    if sampler.get("name") == info[2]), None)
                    locations = sampler.get("locations", []) if sampler else []
                    if (upload_offset == 0 and len(locations) == len(upload_values) and
                            all(isinstance(unit, int) and unit >= 0 for unit in upload_values)):
                        for index, unit in enumerate(upload_values):
                            semantic = (info[0], reflection.get("generation"), info[2], index)
                            st["sampler_units"][semantic] = unit
                        transition("sampler_array_units", info[2], [_count_class(unit) for unit in view["values"]])
                    else:
                        unresolved.add("sampler_array_assignment")
                        st["sampler_units"] = {key: unit for key, unit in st["sampler_units"].items()
                                                if key[0] != info[0]}
                else:
                    unresolved.add("sampler_array_assignment")
                    if info:
                        st["sampler_units"] = {key: unit for key, unit in st["sampler_units"].items() if key[0] != info[0]}
        if method == "uniform1i" and len(args) > 1:
            location = _arg(event, 0)
            transition("sampler_unit", role({"id": location.get("program"), "kind": "program"}) if isinstance(location, dict) else None,
                       location.get("name") if isinstance(location, dict) else None,
                       _count_class(_arg(event, 1)))
        elif method == "activeTexture":
            texture_unit = _arg(event, 0)
            st["active_texture"] = texture_unit - 33984 if isinstance(texture_unit, int) and texture_unit >= 33984 else texture_unit
            st["textures"].setdefault(st["active_texture"], {})
            transition("active_texture", st["active_texture"])
        elif method == "bindTexture":
            st["textures"].setdefault(st["active_texture"], {})[_enum(_arg(event, 0))] = _id(_arg(event, 1))
            transition("bind_texture", st["active_texture"], _enum(_arg(event, 0)), role(_arg(event, 1)))
        elif method in ("texImage2D", "texImage3D", "texSubImage2D", "texSubImage3D",
                        "compressedTexImage2D", "compressedTexImage3D",
                        "compressedTexSubImage2D", "compressedTexSubImage3D",
                        "copyTexImage2D", "copyTexSubImage2D", "copyTexSubImage3D",
                        "texStorage2D", "texStorage3D"):
            texture_target = _enum(_arg(event, 0))
            texture = st["textures"].get(st["active_texture"], {}).get(texture_target)
            if texture:
                full_redefinition = method in ("texImage2D", "texImage3D", "compressedTexImage2D",
                                               "compressedTexImage3D", "copyTexImage2D", "texStorage2D",
                                               "texStorage3D")
                if full_redefinition:
                    st["texture_generations"][texture] += 1
                generation = st["texture_generations"][texture]
                if method not in ("texStorage2D", "texStorage3D"):
                    st["uploaded_textures"].add((texture, generation))
                transition("texture_upload", texture_target, role({"id": texture, "kind": "texture"}),
                           generation, "redefine" if full_redefinition else "update")
            else:
                unresolved.add("texture_upload_binding")
        elif method == "bindFramebuffer":
            target = _enum(_arg(event, 0))
            if target in ("FRAMEBUFFER", "DRAW_FRAMEBUFFER"):
                st["framebuffer"] = _id(_arg(event, 1))
            if target in ("FRAMEBUFFER", "READ_FRAMEBUFFER"):
                st["read_framebuffer"] = _id(_arg(event, 1))
            transition("bind_framebuffer", role(_arg(event, 1)))
        elif method == "framebufferTexture2D":
            target = _enum(_arg(event, 0))
            framebuffer = framebuffer_for(st, target)
            attachment = _enum(_arg(event, 1))
            if framebuffer:
                texture = _id(_arg(event, 3))
                if texture:
                    level = _arg(event, 4)
                    st["texture_attachments"][framebuffer][attachment] = {
                        "texture": texture, "level": level, "layered": False}
                    if level != 0:
                        unresolved.add("texture_attachment_subresource")
                else:
                    st["texture_attachments"][framebuffer].pop(attachment, None)
                transition("framebuffer_texture", target, attachment, role(_arg(event, 3)))
            else:
                unresolved.add("framebuffer_attachment_state")
                st["texture_attachments"].clear()
        elif method == "framebufferTextureLayer":
            target = _enum(_arg(event, 0))
            framebuffer = framebuffer_for(st, target)
            attachment = _enum(_arg(event, 1))
            if framebuffer:
                texture = _id(_arg(event, 2))
                if texture:
                    st["texture_attachments"][framebuffer][attachment] = {
                        "texture": texture, "level": _arg(event, 3), "layered": True}
                    unresolved.add("texture_attachment_subresource")
                else:
                    st["texture_attachments"][framebuffer].pop(attachment, None)
                transition("framebuffer_texture_layer", target, attachment, role(_arg(event, 2)),
                           _size_class(_arg(event, 4)))
            else:
                unresolved.add("framebuffer_attachment_state")
                st["texture_attachments"].clear()
        elif method == "framebufferRenderbuffer":
            target = _enum(_arg(event, 0))
            framebuffer = framebuffer_for(st, target)
            attachment = _enum(_arg(event, 1))
            if framebuffer:
                st["texture_attachments"][framebuffer].pop(attachment, None)
                transition("framebuffer_renderbuffer", target, attachment, role(_arg(event, 3)))
            else:
                unresolved.add("framebuffer_attachment_state")
                st["texture_attachments"].clear()

        if method.startswith(("draw", "multiDraw")) and pos is not None:
            if "Elements" in method and not method.startswith("multiDraw"):
                count_index = 3 if "Range" in method else 1
                type_index, offset_index = ((4, 5) if "Range" in method else (2, 3))
                count, draw_type, offset = (_arg(event, count_index), _arg(event, type_index), _arg(event, offset_index))
                element_buffer = vao(st)["element"]
                width = {5121: 1, 5123: 2, 5125: 4}.get(draw_type)
                size = resource_sizes.get(element_buffer)
                if isinstance(offset, (int, float)):
                    values.add(f"element_offset:{'zero' if offset == 0 else 'nonzero'}")
                    if width and isinstance(count, (int, float)) and isinstance(size, (int, float)):
                        values.add(f"element_offset:{'in_bounds' if offset >= 0 and offset % width == 0 and offset + count * width <= size else 'out_of_bounds'}")
                    else:
                        values.add("element_offset:unknown")
            positive_draw_count += pos
            if pos:
                flow = set()
                program = st["program"]
                reflection = program_reflections.get(program)
                active_slots = set(reflection.get("attributes", [])) if reflection and reflection.get("status") == "linked" and reflection.get("complete") is True else None
                current_vao = vao(st)
                consumed = []
                if active_slots is not None:
                    for index, attr in current_vao["attributes"].items():
                        if index in active_slots and attr.get("enabled") and attr.get("buffer"):
                            consumed.append((index, attr["buffer"], resource_storage[attr["buffer"]], attr.get("divisor", 0)))
                if active_slots is None:
                    unresolved.add("active_attribute_slots")
                elif not consumed and active_slots:
                    unresolved.add("attribute_consumption")
                element = current_vao.get("element") if "Elements" in method else None
                if "Elements" in method and element is None:
                    unresolved.add("element_buffer_binding")
                signature = {"attrs": sorted(consumed), "element": (element, resource_storage[element]) if element else None,
                             "program": program, "vao": st["vao"]}
                prior = st["last_draw"]
                if prior:
                    buffers_now = {item[1] for item in consumed}
                    buffers_before = {item[1] for item in prior["attrs"]}
                    if active_slots is not None and buffers_now & buffers_before:
                        flow.add("buffer_attribute_draw")
                        if any(buffer == old_buffer and generation != old_generation
                               for _, buffer, generation, _ in consumed
                               for _, old_buffer, old_generation, _ in prior["attrs"]):
                            flow.add("buffer_attribute_draw_replace_draw")
                    if st["vao"] != prior["vao"]:
                        flow.add("vao_switch_draw")
                    if program != prior["program"]:
                        flow.add("program_switch_draw")
                    if active_slots is not None and prior.get("enabled") != tuple(sorted((i, a.get("enabled")) for i, a in current_vao["attributes"].items())):
                        flow.add("attribute_toggle_draw")
                    if prior.get("element") != signature["element"] and element:
                        flow.add("element_buffer_switch_draw")
                st["last_draw"] = {**signature, "enabled": tuple(sorted((i, a.get("enabled")) for i, a in current_vao["attributes"].items()))}
                if (prior and st.get("last_replacement") and
                        st["last_replacement"][0] in {item[1] for item in consumed} and
                        st["last_replacement"][0] in {item[1] for item in prior["attrs"]}):
                    flow.add("buffer_attribute_draw_replace_draw")
                st.pop("last_replacement", None)
                if "Elements" in method and element:
                    flow.add("element_buffer_draw")
                if "Instanced" in method and any(divisor for _, _, _, divisor in consumed):
                    flow.add("instanced_attribute_draw")
                attachments = st["texture_attachments"].get(st["framebuffer"], {}).values() if st["framebuffer"] else ()
                attached = {(item["texture"], st["texture_generations"][item["texture"]])
                            for item in attachments if not item.get("layered") and item.get("level") == 0}
                sampled = set()
                if reflection and reflection.get("status") == "linked" and reflection.get("complete") is True:
                    for sampler in reflection.get("samplers", []):
                        texture_target = _sampler_target(sampler.get("type"))
                        if not texture_target:
                            unresolved.add("sampler_type")
                            continue
                        locations = sampler.get("locations", [sampler.get("location")])
                        for index, _location in enumerate(locations):
                            semantic = (program, reflection.get("generation"), sampler.get("name"), index)
                            unit = st["sampler_units"].get(semantic, 0)
                            texture = st["textures"].get(unit, {}).get(texture_target)
                            if texture:
                                sampled.add((texture, st["texture_generations"][texture]))
                st.setdefault("used_textures", set()).update(sampled)
                rendered = attached & st["uploaded_textures"]
                if rendered:
                    flow.add("texture_upload_attach_render")
                    st["rendered_textures"].update(rendered)
                if st["rendered_textures"] & sampled and not st["rendered_textures"] & attached:
                    flow.add("texture_upload_attach_render_sample")
                transition("draw", method, "positive", role(_arg(event, 0)) if "Elements" not in method else None,
                           role({"id": program, "kind": "program"}), role({"id": st["vao"], "kind": "vao"}) if st["vao"] else None,
                           [[index, role({"id": buffer, "kind": "buffer"}), generation, _count_class(divisor)]
                            for index, buffer, generation, divisor in consumed],
                           [role({"id": element, "kind": "buffer"}), resource_storage[element]] if element else None,
                           sorted(role({"id": texture, "kind": "texture"}) for texture in sampled))
                for pattern in flow:
                    flows.add(pattern)
                    flow_events[(cid, pattern)] += pos

        if method == "deleteBuffer":
            buffer = _id(_arg(event, 0))
            if buffer and st.get("last_draw"):
                if any(item[1] == buffer for item in st["last_draw"]["attrs"]):
                    flows.add("resource_delete_after_use")
                    flow_events[(cid, "resource_delete_after_use")] += 1
                    transition("delete_buffer_after_use", role(_arg(event, 0)))
        if method == "deleteTexture":
            texture = _id(_arg(event, 0))
            if texture and any(item[0] == texture for item in st.get("used_textures", set())):
                flows.add("resource_delete_after_use")
                flow_events[(cid, "resource_delete_after_use")] += 1
                transition("delete_texture_after_use", role(_arg(event, 0)))

    for (cid, pattern), count in flow_events.items():
        repetitions[pattern] = "one" if count <= 1 else "few" if count <= 4 else "many"

    if not events:
        unresolved.add("no_events")
    output = {
        "methods": sorted(methods),
        "extension_methods": {key: sorted(value) for key, value in sorted(extension_methods.items())},
        "overloads": sorted(overloads),
        "value_classes": sorted(values),
        "flow_patterns": sorted(flows),
        "transitions": transitions,
        "flow_signature": json.dumps({"transitions": transitions, "flows": sorted(flows),
                                       "values": sorted(values), "repetitions": dict(sorted(repetitions.items()))},
                                      separators=(",", ":")),
        "positive_draws": positive_draw_count,
        "unresolved": sorted(unresolved),
        "repetitions": dict(sorted(repetitions.items())),
        "context_identities": profile.get("contexts", []),
        "profile_clean": clean_profile,
        "reducer_version": REDUCER_VERSION,
    }
    return output

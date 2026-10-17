from api_audit.flow_reducer import _sampler_target, reduce_trace


def e(method, args=(), result=None, reflection=None, context="c0", extension=None):
    event = {"seq": 0, "context": context, "method": method, "extension": extension,
             "args": list(args)}
    if result is not None:
        event["result"] = result
    if reflection is not None:
        event["reflection"] = reflection
    return event


def profile(*events):
    return {"contexts": [{"id": "c0", "version": 2, "extensions": []}], "events": list(events),
            "outcomes": [], "truncated": False}


def test_range_draw_count_uses_fourth_argument_and_zero_is_not_positive():
    zero = reduce_trace(profile(e("drawRangeElements", [4, 0, 20, 0, 5123, 0])))
    positive = reduce_trace(profile(e("drawRangeElements", [4, 0, 20, 3, 5123, 0])))
    assert zero["positive_draws"] == 0
    assert "draw_count:zero" in zero["value_classes"]
    assert positive["positive_draws"] == 1


def test_instanced_multidraw_requires_positive_count_and_instance_count():
    counts = {"kind": "array", "type": "Array", "length": 3, "truncated": False, "values": [3, 0, 2]}
    instances = {"kind": "view", "type": "Int32Array", "length": 3, "truncated": False, "values": [0, 5, 2]}
    event = e("multiDrawArraysInstancedWEBGL", [4, [0, 3, 6], 0, counts, 0, instances, 0, 3],
              extension="WEBGL_multi_draw")
    assert reduce_trace(profile(event))["positive_draws"] == 1
    instances["values"] = [0, 0, 0]
    assert reduce_trace(profile(event))["positive_draws"] == 0
    instances["truncated"] = True
    result = reduce_trace(profile(event))
    assert result["positive_draws"] == 0
    assert "multi_draw_selection" in result["unresolved"]


def test_multidraw_selected_offsets_apply_before_positive_work_classification():
    counts = {"kind": "array", "type": "Array", "length": 4, "truncated": False,
              "values": [0, 3, 0, 0]}
    instances = {"kind": "array", "type": "Array", "length": 4, "truncated": False,
                 "values": [0, 0, 2, 3]}
    event = e("multiDrawArraysInstancedWEBGL", [4, [0, 0, 0, 0], 0, counts, 0,
                                                   instances, 1, 2], extension="WEBGL_multi_draw")
    result = reduce_trace(profile(event))
    assert result["positive_draws"] == 1
    assert "positive_subdraws:one" in result["value_classes"]


def test_vertex_attrib_pointer_preserves_enabled_and_divisor():
    events = [e("enableVertexAttribArray", [0]), e("vertexAttribDivisor", [0, 1]),
              e("bindBuffer", [34962, {"id": "b1", "kind": "buffer"}]),
              e("vertexAttribPointer", [0, 3, 5126, False, 0, 0])]
    reflection = {"status": "linked", "complete": True, "generation": 1, "attributes": [0], "samplers": []}
    events.extend([e("linkProgram", [{"id": "p1", "kind": "program"}], reflection=reflection),
                   e("useProgram", [{"id": "p1", "kind": "program"}]),
                   e("drawArraysInstanced", [4, 0, 3, 2])])
    result = reduce_trace(profile(*events))
    assert "instanced_attribute_draw" in result["flow_patterns"]
    assert "active_attribute_slots" not in result["unresolved"]


def test_flow_signature_normalizes_object_ids_but_keeps_ordered_state():
    def trace(buffer, program):
        reflection = {"status": "linked", "complete": True, "generation": 1,
                      "attributes": [0], "samplers": []}
        return profile(e("bindBuffer", [34962, {"id": buffer, "kind": "buffer"}]),
                       e("bufferData", [34962, 64, 35044]),
                       e("enableVertexAttribArray", [0]),
                       e("vertexAttribPointer", [0, 3, 5126, False, 0, 0]),
                       e("linkProgram", [{"id": program, "kind": "program"}], reflection=reflection),
                       e("useProgram", [{"id": program, "kind": "program"}]),
                       e("drawArrays", [4, 0, 3]))
    a = reduce_trace(trace("bufferA", "programA"))
    b = reduce_trace(trace("bufferB", "programB"))
    assert a["flow_signature"] == b["flow_signature"]


def test_sampler_assignment_uses_semantics_across_distinct_wrappers_and_unit():
    program = {"id": "p", "kind": "program"}
    texture = {"id": "t1", "kind": "texture"}
    reflection = {"generation": 4, "status": "linked", "complete": True, "attributes": [],
                  "samplers": [{"name": "image", "type": 35678, "size": 1,
                                "locations": [{"id": "o6", "kind": "location", "program": "p",
                                               "generation": 4, "name": "image"}]}]}
    seed_location = {"id": "o7", "kind": "location", "program": "p", "generation": 4, "name": "image"}
    events = [e("linkProgram", [program], reflection=reflection), e("useProgram", [program]),
              e("getUniformLocation", [program, "image"], seed_location), e("uniform1i", [seed_location, 1]),
              e("activeTexture", [33985]), e("bindTexture", [3553, texture]),
              e("texImage2D", [3553, 0, 6408, 1, 1, 0, 6408, 5121, None]),
              e("bindFramebuffer", [36160, {"id": "f", "kind": "framebuffer"}]),
              e("framebufferTexture2D", [36160, 36064, 3553, texture, 0]), e("drawArrays", [4, 0, 3]),
              e("bindFramebuffer", [36160, None]), e("drawArrays", [4, 0, 3])]
    result = reduce_trace(profile(*events))
    assert "texture_upload_attach_render_sample" in result["flow_patterns"]


def test_sampler_array_offsets_that_cannot_be_proven_are_unresolved():
    program = {"id": "p", "kind": "program"}
    loc = {"id": "o1", "kind": "location", "program": "p", "generation": 1, "name": "tex[0]"}
    reflection = {"generation": 1, "status": "linked", "complete": True, "attributes": [],
                  "samplers": [{"name": "tex[0]", "type": 35678, "size": 2,
                                "locations": [loc, {**loc, "id": "o2", "name": "tex[1]"}]}]}
    values = {"kind": "array", "type": "Array", "length": 2, "truncated": False, "values": [0, 1]}
    result = reduce_trace(profile(e("linkProgram", [program], reflection=reflection), e("useProgram", [program]),
                                  e("uniform1iv", [loc, values, 1, 1])))
    assert "sampler_array_assignment" in result["unresolved"]


def test_sampler_types_map_to_their_actual_texture_targets():
    assert _sampler_target(36299) == "TEXTURE_3D"
    assert _sampler_target(36300) == "TEXTURE_CUBE_MAP"
    assert _sampler_target(36303) == "TEXTURE_2D_ARRAY"
    assert _sampler_target(36307) == "TEXTURE_3D"
    assert _sampler_target(36308) == "TEXTURE_CUBE_MAP"
    assert _sampler_target(36311) == "TEXTURE_2D_ARRAY"


def test_storage_replacement_and_subdata_classes_use_effective_slice_bytes():
    buffer = {"id": "b", "kind": "buffer"}
    large_view = {"kind": "view", "type": "Uint8Array", "length": 65536,
                  "byte_length": 65536, "truncated": False}
    one_byte = {"kind": "view", "type": "Uint8Array", "length": 65536,
                "byte_length": 65536, "truncated": False}
    result = reduce_trace(profile(e("bindBuffer", [34962, buffer]),
                                  e("bufferData", [34962, 64, 35044]),
                                  e("bufferData", [34962, 1024, 35044]),
                                  e("bufferData", [34962, large_view, 35044, 65535, 1]),
                                  e("bufferData", [34962, 65536, 35044]),
                                  e("bufferSubData", [34962, 65535, one_byte, 65535, 1]),
                                  e("drawArrays", [4, 0, 3])))
    assert "buffer_replacement:shrink" in result["value_classes"]
    assert "buffer_replacement:grow" in result["value_classes"]
    assert "buffer_allocation:tiny" in result["value_classes"]
    assert "buffer_upload:tiny" in result["value_classes"]
    assert "buffer_subdata_offset:end" in result["value_classes"]
    assert "draw_mode:TRIANGLES" in result["value_classes"]
    assert "buffer_usage:STATIC_DRAW" in result["value_classes"]
    assert "buffer_subdata_offset:out_of_bounds" not in result["value_classes"]


def test_element_array_buffer_storage_uses_active_vao_binding():
    buffer = {"id": "indices", "kind": "buffer"}
    vao = {"id": "vao", "kind": "vao"}
    events = [e("bindVertexArray", [vao]), e("bindBuffer", [34963, buffer]),
              e("bufferData", [34963, 12, 35044]), e("bufferData", [34963, 6, 35044]),
              e("drawElements", [4, 3, 5123, 0])]
    result = reduce_trace(profile(*events))
    assert "buffer_data_binding" not in result["unresolved"]
    assert "buffer_replacement:shrink" in result["value_classes"]
    assert "element_offset:in_bounds" in result["value_classes"]
    assert "element_buffer_draw" in result["flow_patterns"]


def test_framebuffer_layer_is_unresolved_and_unmodeled_target_cannot_reuse_attachment():
    first = {"id": "texture1", "kind": "texture"}
    second = {"id": "texture2", "kind": "texture"}
    framebuffer = {"id": "fbo", "kind": "framebuffer"}
    program = {"id": "program", "kind": "program"}
    reflection = {"generation": 1, "status": "linked", "complete": True,
                  "attributes": [], "samplers": []}
    events = [e("bindFramebuffer", [36160, framebuffer]),
              e("bindTexture", [35866, first]), e("texImage3D", [35866]),
              e("framebufferTextureLayer", [36160, 36064, first, 0, 0]),
              e("bindTexture", [35866, second]), e("texImage3D", [35866]),
              e("framebufferTextureLayer", [36160, 36064, second, 0, 1]),
              e("linkProgram", [program], reflection=reflection), e("useProgram", [program]),
              e("drawArrays", [4, 0, 3])]
    result = reduce_trace(profile(*events))
    assert "texture_attachment_subresource" in result["unresolved"]
    assert "texture_upload_attach_render" not in result["flow_patterns"]
    events.insert(-1, e("framebufferTextureLayer", [999999, 36064, first, 0, 0]))
    invalidated = reduce_trace(profile(*events))
    assert "framebuffer_attachment_state" in invalidated["unresolved"]
    assert "texture_upload_attach_render" not in invalidated["flow_patterns"]


def test_texture_redefinition_invalidates_old_render_proof_until_new_generation_renders():
    texture = {"id": "texture", "kind": "texture"}
    framebuffer = {"id": "fbo", "kind": "framebuffer"}
    program = {"id": "program", "kind": "program"}
    location = {"id": "sampler", "kind": "location", "program": "program",
                "generation": 1, "name": "image"}
    reflection = {"generation": 1, "status": "linked", "complete": True, "attributes": [],
                  "samplers": [{"name": "image", "type": 35678, "size": 1,
                                "locations": [location]}]}
    upload = [3553, 0, 6408, 1, 1, 0, 6408, 5121, None]
    base = [e("bindTexture", [3553, texture]), e("texImage2D", upload),
            e("bindFramebuffer", [36160, framebuffer]),
            e("framebufferTexture2D", [36160, 36064, 3553, texture, 0]),
            e("linkProgram", [program], reflection=reflection), e("useProgram", [program]),
            e("drawArrays", [4, 0, 3]), e("bindFramebuffer", [36160, None]),
            e("texImage2D", upload), e("drawArrays", [4, 0, 3])]
    after_redefinition_only = reduce_trace(profile(*base))
    assert "texture_upload_attach_render" in after_redefinition_only["flow_patterns"]
    assert "texture_upload_attach_render_sample" not in after_redefinition_only["flow_patterns"]
    rerendered = base[:-1] + [e("bindFramebuffer", [36160, framebuffer]), e("drawArrays", [4, 0, 3]),
                               e("bindFramebuffer", [36160, None]), e("drawArrays", [4, 0, 3])]
    after_new_generation_render = reduce_trace(profile(*rerendered))
    assert "texture_upload_attach_render_sample" in after_new_generation_render["flow_patterns"]


def test_navigation_and_runner_failures_block_partial_profile_credit():
    result = reduce_trace({"contexts": [{"id": "c0", "version": 2, "extensions": []}],
                           "events": [e("drawArrays", [4, 0, 3])], "truncated": False,
                           "outcomes": [{"code": "navigation_failed"}]})
    assert result["positive_draws"] == 1
    assert result["profile_clean"] is False

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import webgl_mutator as mutator


@pytest.mark.parametrize('initializer', [
    'canvas.getContext("webgl2")',
    'canvas.getContext("webgl2") || canvas.getContext("webgl")',
])
def test_webgl_context_initializers_accept_direct_calls_and_fallback(initializer):
    root = mutator.parse_js(f'const gl = {initializer};')
    assert mutator._context_names(root) == {'gl'}


@pytest.mark.parametrize('initializer', [
    'canvas.getContext("webgl2") || canvas.getContext("2d")',
    'canvas.getContext("webgl2") || fallback',
    'canvas.getContext("webgl2") || other.getContext("webgl")',
])
def test_webgl_context_initializers_reject_mixed_or_fake_branches(initializer):
    root = mutator.parse_js(f'const gl = {initializer};')
    assert not mutator._context_names(root)


def test_webgl_context_initializers_reject_side_effectful_fallback_receivers():
    root = mutator.parse_js(
        'const gl = makeCanvas().getContext("webgl2") || makeCanvas().getContext("webgl");')
    assert not mutator._context_names(root)


def test_webgl_context_initializers_reject_reassignment_and_shadowing():
    reassigned = mutator.parse_js(
        'let gl = canvas.getContext("webgl2") || canvas.getContext("webgl"); gl = {};')
    shadowed = mutator.parse_js(
        'const gl = canvas.getContext("webgl2") || canvas.getContext("webgl"); function f(gl) {}')
    assert not mutator._context_names(reassigned)
    assert not mutator._context_names(shadowed)


def test_deterministic_replay_and_html_preservation(tmp_path):
    source = b'<!doctype html><title>x</title><canvas></canvas><script>const gl = canvas.getContext("webgl2"); gl.drawArrays(gl.TRIANGLES, 0, 3);</script><footer>ok</footer>'
    changed, edit = mutator.mutate_bytes(source, __import__('random').Random(7))
    metadata = {'edits': edit}
    assert mutator.replay(source, metadata) == changed
    assert changed.startswith(source[:source.index(b'<script>')])
    assert changed.endswith(b'</script><footer>ok</footer>')


def test_no_change_rejected():
    with pytest.raises(ValueError, match='no applicable'):
        mutator.mutate_bytes(b'<script>const gl = canvas.getContext("webgl2"); const x = 1;</script>', __import__('random').Random(0))


def test_storage_matches_bound_target_and_respects_bound():
    js = 'const gl = canvas.getContext("webgl2"); gl.bindBuffer(gl.ARRAY_BUFFER, a); gl.bufferData(gl.ARRAY_BUFFER, 32, gl.STATIC_DRAW); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, 64, gl.STATIC_DRAW);'
    options = mutator._edits(js)
    assert len([e for e in options if e[0] == 'resource_storage']) == 4
    assert {e[3] for e in options if e[0] == 'resource_storage'} == {'64', '128', '256'}
    assert not [e for e in mutator._edits('const gl = canvas.getContext("webgl2"); gl.bufferData(gl.ARRAY_BUFFER, 32, gl.STATIC_DRAW);') if e[0] == 'resource_storage']


def test_wrong_receiver_and_reordered_binding_are_rejected():
    assert not mutator._edits('const gl = {}; gl.drawArrays(gl.TRIANGLES, 0, 3);')
    js = 'const gl = canvas.getContext("webgl2"); gl.bufferData(gl.ARRAY_BUFFER, 32, gl.STATIC_DRAW); gl.bindBuffer(gl.ARRAY_BUFFER, later);'
    assert not [e for e in mutator._edits(js) if e[0] == 'resource_storage']


def validation_seed(target='gl.ARRAY_BUFFER', offset='0', data='new Uint8Array(4)', allocation='16', suffix=''):
    return (f'<script>const gl = canvas.getContext("webgl2"); const buffer = gl.createBuffer(); '
            f'gl.bindBuffer({target}, buffer); gl.bufferData({target}, {allocation}, gl.STATIC_DRAW); '
            f'{suffix}gl.bufferSubData({target}, {offset}, {data});</script>').encode()


def test_validation_arm_is_separate_single_edit_and_replays_deterministically():
    source = validation_seed()
    assert not [e for e in mutator._edits(mutator._script(source)[1])
                if e[0] == 'buffer_subdata_boundary_validation']
    first, edits = mutator.mutate_bytes(source, __import__('random').Random(45), max_edits=3, arm='validation')
    second, again = mutator.mutate_bytes(source, __import__('random').Random(45), max_edits=3, arm='validation')
    assert first == second and edits == again and len(edits) == 1
    assert edits[0]['operator'] == 'buffer_subdata_boundary_validation'
    assert b'gl.bufferSubData(gl.ARRAY_BUFFER, 16, new Uint8Array(4)); window.__validationError = gl.getError();' in first
    metadata = {'edits': edits, 'arm': 'validation', 'expected_error': 'INVALID_VALUE'}
    assert mutator.replay(source, metadata) == first


def test_validation_arm_accepts_same_canvas_context_fallback():
    source = validation_seed().replace(
        b'canvas.getContext("webgl2")',
        b'canvas.getContext("webgl2") || canvas.getContext("webgl")')
    assert len(mutator._validation_edits(mutator._script(source)[1])) == 1


def test_validation_arm_proves_nonempty_direct_numeric_array_length():
    source = validation_seed(data='new Float32Array([7, -0.8, 1e-2])', allocation='24')
    edits = mutator._validation_edits(mutator._script(source)[1])
    assert len(edits) == 1
    changed, metadata = mutator.mutate_bytes(source, __import__('random').Random(8), arm='validation')
    assert len(metadata) == 1
    assert b'gl.bufferSubData(gl.ARRAY_BUFFER, 24, new Float32Array([7, -0.8, 1e-2]));' in changed


@pytest.mark.parametrize('data', [
    'new Uint8Array([1,,2])',
    'new Uint8Array([1, ...[2]])',
    'new Uint8Array([])',
    'new Uint8Array([1, value])',
])
def test_validation_arm_rejects_unknown_or_empty_array_literal_lengths(data):
    source = validation_seed(data=data)
    assert not mutator._validation_edits(mutator._script(source)[1])


def test_validation_arm_rejects_prior_direct_gl_call_with_possible_error():
    source = validation_seed(suffix='gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 8, 0); ')
    assert not mutator._validation_edits(mutator._script(source)[1])


def test_validation_arm_fallback_still_rejects_opaque_prior_call():
    source = validation_seed(suffix='helper(); ').replace(
        b'canvas.getContext("webgl2")',
        b'canvas.getContext("webgl2") || canvas.getContext("webgl")')
    assert not mutator._validation_edits(mutator._script(source)[1])


def texture_switch_seed(other_size='16,16', other_format='gl.RGBA8', bind_other='textureB',
                       helper='', subimage='2,3,4,5', delete='', active=''):
    return ("const gl = canvas.getContext('webgl2'); const textureA = gl.createTexture(); "
            "const textureB = gl.createTexture(); "
            "gl.bindTexture(gl.TEXTURE_2D, textureA); "
            "gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 16, 16, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(1024)); "
            f"gl.bindTexture(gl.TEXTURE_2D, {bind_other}); "
            f"gl.texImage2D(gl.TEXTURE_2D, 0, {other_format}, {other_size}, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(1024)); "
            f"{delete}{helper}{active}gl.bindTexture(gl.TEXTURE_2D, textureA); "
            f"gl.texSubImage2D(gl.TEXTURE_2D, 0, {subimage}, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(80));")


def test_compatible_texture_update_switch_restores_original_binding():
    js = texture_switch_seed()
    candidates = [edit for edit in mutator._edits(js) if edit[0] == 'compatible_texture_update_switch']
    assert len(candidates) == 1
    assert candidates[0][3].startswith('gl.bindTexture(gl.TEXTURE_2D, textureB); gl.texSubImage2D(')
    assert candidates[0][3].endswith('gl.bindTexture(gl.TEXTURE_2D, textureA);')


def test_compatible_texture_update_switch_accepts_same_canvas_context_fallback():
    js = texture_switch_seed().replace(
        "canvas.getContext('webgl2')",
        "canvas.getContext('webgl2') || canvas.getContext('webgl')").replace('gl.RGBA8', 'gl.RGBA')
    assert len([edit for edit in mutator._edits(js)
                if edit[0] == 'compatible_texture_update_switch']) == 1


def test_compatible_texture_update_fallback_still_rejects_opaque_call():
    js = texture_switch_seed(helper='helper();').replace(
        "canvas.getContext('webgl2')",
        "canvas.getContext('webgl2') || canvas.getContext('webgl')")
    assert not [edit for edit in mutator._edits(js)
                if edit[0] == 'compatible_texture_update_switch']


@pytest.mark.parametrize('js', [
    texture_switch_seed(other_size='8,16'),
    texture_switch_seed(other_format='gl.RGB8'),
    texture_switch_seed(bind_other='unknownTexture'),
    texture_switch_seed(delete='gl.deleteTexture(textureB); '),
    texture_switch_seed(helper='helper(); '),
    texture_switch_seed(active='gl.activeTexture(gl.TEXTURE1); '),
    texture_switch_seed(subimage='14,0,4,5'),
])
def test_compatible_texture_update_switch_rejects_unproven_or_unsafe_storage(js):
    assert not [edit for edit in mutator._edits(js)
                if edit[0] == 'compatible_texture_update_switch']


def texture_resize_seed(middle='', context='gl', texture='texture', allocation_context='gl',
                        update_context='gl', dimensions='8,8', before_allocation='', after_update=''):
    return (f'const {context} = canvas.getContext("webgl2"); const other = canvas.getContext("webgl2"); '
            f'const textureOther = {context}.createTexture(); '
            f'const {texture} = {allocation_context}.createTexture(); '
            f'{context}.bindTexture({context}.TEXTURE_2D, {texture}); '
            f'{before_allocation}'
            f'{context}.texImage2D({context}.TEXTURE_2D, 0, {context}.RGBA8, 8, 8, 0, {context}.RGBA, '
            f'{context}.UNSIGNED_BYTE, new Uint8Array(256)); {middle}'
            f'{update_context}.texSubImage2D({context}.TEXTURE_2D, 0, 0, 0, {dimensions}, {context}.RGBA, '
            f'{context}.UNSIGNED_BYTE, new Uint8Array(256)); {after_update}')


def test_texture_allocation_and_full_update_dimensions_are_one_replayable_group():
    js = texture_resize_seed()
    edits = [edit for edit in mutator._edits(js) if edit[0] == 'texture_allocation_update_dimensions']
    assert len(edits) == 1 and len(edits[0][1]) == 4
    html = f'<script>{js}</script>'.encode()
    changed, metadata = mutator.mutate_bytes(html, __import__('random').Random(91))
    assert any(edit.get('operator') == 'texture_allocation_update_dimensions'
               and len(edit['spans']) == 4 for edit in metadata)
    assert mutator.replay(html, {'edits': metadata}) == changed
    assert b'texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 4, 4' in changed
    assert b'texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 4,4' in changed


@pytest.mark.parametrize('js', [
    texture_resize_seed(middle='gl.bindTexture(gl.TEXTURE_2D, textureOther); '),
    texture_resize_seed(middle='gl.activeTexture(gl.TEXTURE1); '),
    texture_resize_seed(before_allocation='gl.activeTexture(gl.TEXTURE1); '),
    texture_resize_seed(middle='gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0); '),
    texture_resize_seed(middle='gl.framebufferTextureLayer(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, texture, 0, 0); '),
    texture_resize_seed(middle='const alias = texture; '),
    texture_resize_seed(middle='const holder = { texture }; '),
    texture_resize_seed(after_update='gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 8, 8, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(256));'),
    texture_resize_seed(after_update='gl.copyTexSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 0, 0, 8, 8);'),
    texture_resize_seed(after_update='helper();'),
    texture_resize_seed(middle='if (ready) gl.drawArrays(gl.TRIANGLES, 0, 3); '),
    texture_resize_seed(middle='helper(); '),
    texture_resize_seed(dimensions='8,7'),
    texture_resize_seed(allocation_context='other'),
    texture_resize_seed(update_context='other'),
])
def test_texture_allocation_update_dimensions_rejects_unproven_flow(js):
    assert not [edit for edit in mutator._edits(js)
                if edit[0] == 'texture_allocation_update_dimensions']


def test_program_relink_duplicate_accepts_stable_same_context_program():
    js = ('const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); '
          'gl.linkProgram(program);')
    edits = [edit for edit in mutator._edits(js) if edit[0] == 'program_relink_duplicate']
    assert len(edits) == 1
    assert edits[0][3] == 'gl.linkProgram(program); gl.linkProgram(program);'


@pytest.mark.parametrize('js', [
    'const gl = canvas.getContext("webgl2"); const other = canvas.getContext("webgl2"); const program = other.createProgram(); gl.linkProgram(program);',
    'const gl = canvas.getContext("webgl2"); let program = gl.createProgram(); program = gl.createProgram(); gl.linkProgram(program);',
    'const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); function f(program) { gl.linkProgram(program); }',
    'const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); { const { program } = { program: null }; gl.linkProgram(program); }',
    'const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); if (ready) gl.linkProgram(program);',
    'const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); gl.linkProgram(program, extra);',
    'const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); gl.linkProgram(getProgram());',
])
def test_program_relink_duplicate_rejects_unproven_calls(js):
    assert not [edit for edit in mutator._edits(js) if edit[0] == 'program_relink_duplicate']


def framebuffer_seed(setup=('gl.bindTexture(gl.TEXTURE_2D, texture); '
                             'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(4)); '),
                     call='gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);'):
    return ('const gl = canvas.getContext("webgl2"); const framebuffer = gl.createFramebuffer(); '
            'const texture = gl.createTexture(); gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer); '
            f'{setup}{call}')


def test_framebuffer_attachment_cycle_detaches_and_restores_attachment():
    js = framebuffer_seed(setup='const target = gl.FRAMEBUFFER; const attachment = gl.COLOR_ATTACHMENT0; '
                          'const textureTarget = gl.TEXTURE_2D; gl.bindTexture(textureTarget, texture); '
                          'gl.texImage2D(textureTarget, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(4)); ',
                          call='gl.framebufferTexture2D(target, attachment, textureTarget, texture, 0);')
    edits = [edit for edit in mutator._edits(js) if edit[0] == 'framebuffer_attachment_cycle']
    assert len(edits) == 1
    assert edits[0][3] == ('gl.framebufferTexture2D(target, attachment, textureTarget, texture, 0); '
                           'gl.framebufferTexture2D(target, attachment, textureTarget, null, 0); '
                           'gl.framebufferTexture2D(target, attachment, textureTarget, texture, 0);')


def test_framebuffer_attachment_cycle_accepts_same_canvas_context_fallback():
    js = framebuffer_seed().replace(
        'canvas.getContext("webgl2")',
        'canvas.getContext("webgl2") || canvas.getContext("webgl")')
    assert len([edit for edit in mutator._edits(js)
                if edit[0] == 'framebuffer_attachment_cycle']) == 1


@pytest.mark.parametrize('setup', [
    '',
    'gl.bindTexture(gl.TEXTURE_3D, texture); ',
])
def test_framebuffer_attachment_cycle_rejects_unbound_or_wrong_target_texture(setup):
    js = framebuffer_seed(setup=setup)
    assert not [edit for edit in mutator._edits(js)
                if edit[0] == 'framebuffer_attachment_cycle']


def test_framebuffer_attachment_cycle_rejects_bind_inside_unused_function():
    js = framebuffer_seed(setup='function bindElsewhere() { gl.bindTexture(gl.TEXTURE_2D, texture); } ')
    assert not [edit for edit in mutator._edits(js)
                if edit[0] == 'framebuffer_attachment_cycle']


def test_framebuffer_attachment_cycle_rejects_short_circuit_texture_bind():
    js = framebuffer_seed(setup='false && gl.bindTexture(gl.TEXTURE_2D, texture); ')
    assert not [edit for edit in mutator._edits(js)
                if edit[0] == 'framebuffer_attachment_cycle']


def test_framebuffer_attachment_cycle_rejects_same_name_texture_in_nested_function():
    js = framebuffer_seed(setup=('function bindElsewhere() { const texture = gl.createTexture(); '
                                 'gl.bindTexture(gl.TEXTURE_2D, texture); } '))
    assert not [edit for edit in mutator._edits(js)
                if edit[0] == 'framebuffer_attachment_cycle']


def test_framebuffer_attachment_fallback_still_rejects_opaque_call():
    js = framebuffer_seed(setup=('gl.bindTexture(gl.TEXTURE_2D, texture); '
                                 'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, '
                                 'gl.UNSIGNED_BYTE, new Uint8Array(4)); helper(); ')).replace(
        'canvas.getContext("webgl2")',
        'canvas.getContext("webgl2") || canvas.getContext("webgl")')
    assert not [edit for edit in mutator._edits(js)
                if edit[0] == 'framebuffer_attachment_cycle']


@pytest.mark.parametrize('js', [
    'const gl = canvas.getContext("webgl2"); const gl2 = other.getContext("webgl2"); const framebuffer = gl2.createFramebuffer(); const texture = gl.createTexture(); gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);',
    'const gl = canvas.getContext("webgl2"); const gl2 = other.getContext("webgl2"); const framebuffer = gl.createFramebuffer(); const texture = gl2.createTexture(); gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);',
    'const gl = canvas.getContext("webgl2"); const framebuffer = gl.createFramebuffer(); const texture = {}; gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);',
    'const gl = canvas.getContext("webgl2"); const framebuffer = gl.createFramebuffer(); const texture = gl.createTexture(); gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);',
    framebuffer_seed(setup='helper(); '),
    framebuffer_seed(setup='const other = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, other); '),
    framebuffer_seed(setup='gl.deleteFramebuffer(framebuffer); '),
    framebuffer_seed(call='if (ready) gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);'),
    framebuffer_seed(call='gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 1);'),
    framebuffer_seed(call='gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0, extra);'),
])
def test_framebuffer_attachment_cycle_rejects_unproven_or_unsafe_sites(js):
    assert not [edit for edit in mutator._edits(js)
                if edit[0] == 'framebuffer_attachment_cycle']


def test_framebuffer_retire_appends_delete_after_final_unbind_and_replays():
    source = b'<script>const gl = canvas.getContext("webgl2"); const target = gl.FRAMEBUFFER; const framebuffer = gl.createFramebuffer(); gl.bindFramebuffer(target, framebuffer); gl.bindFramebuffer(target, null);</script>'
    js = mutator._script(source)[1]
    edits = [edit for edit in mutator._edits(js) if edit[0] == 'framebuffer_retire']
    assert len(edits) == 1
    edit = {'operator': edits[0][0], 'start': edits[0][1], 'end': edits[0][2], 'replacement': edits[0][3]}
    changed = mutator._apply_edits(js.encode(), [edit])
    assert b'gl.bindFramebuffer(target, null); gl.deleteFramebuffer(framebuffer);' in changed
    assert mutator.replay(source, {'edits': [edit]}) == source[:source.index(b'<script>') + 8] + changed + source[source.index(b'</script>'):]
    assert mutator._valid(changed.decode())


def test_texture_retire_appends_delete_after_final_unbind_and_replays():
    source = b'<script>const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, null); gl.drawArrays(gl.TRIANGLES, 0, 3); gl.bindTexture(gl.TEXTURE_2D, null);</script>'
    js = mutator._script(source)[1]
    edits = [edit for edit in mutator._edits(js) if edit[0] == 'texture_retire']
    assert len(edits) == 1
    edit = {'operator': edits[0][0], 'start': edits[0][1], 'end': edits[0][2], 'replacement': edits[0][3]}
    changed = mutator._apply_edits(js.encode(), [edit])
    assert b'gl.bindTexture(gl.TEXTURE_2D, null); gl.deleteTexture(texture);' in changed
    assert mutator.replay(source, {'edits': [edit]}) == source[:source.index(b'<script>') + 8] + changed + source[source.index(b'</script>'):]
    assert mutator._valid(changed.decode())


def test_texture_retire_allows_rebinding_the_same_texture_before_final_bind():
    js = ('const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); '
          'const pixels = new Uint8Array(4); gl.bindTexture(gl.TEXTURE_2D, texture); '
          'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, pixels); '
          'gl.bindTexture(gl.TEXTURE_2D, texture); gl.bindTexture(gl.TEXTURE_2D, null);')
    assert len([edit for edit in mutator._edits(js) if edit[0] == 'texture_retire']) == 1


def test_texture_retire_allows_later_bind_of_another_texture():
    js = ('const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); '
          'const nextTexture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); '
          'gl.bindTexture(gl.TEXTURE_2D, null); gl.bindTexture(gl.TEXTURE_2D, nextTexture); '
          'gl.drawArrays(gl.TRIANGLES, 0, 3);')
    assert len([edit for edit in mutator._edits(js) if edit[0] == 'texture_retire']) == 1


@pytest.mark.parametrize('js', [
    'const gl = canvas.getContext("webgl2"); const gl2 = other.getContext("webgl2"); const texture = gl2.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); gl.bindTexture(gl.TEXTURE_2D, null);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, texture); gl.bindTexture(gl.TEXTURE_2D, null);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); const alias = gl.getParameter(gl.TEXTURE_BINDING_2D); gl.bindTexture(gl.TEXTURE_2D, null);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); const alias = texture; gl.bindTexture(gl.TEXTURE_2D, texture); gl.bindTexture(gl.TEXTURE_2D, null);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); gl.bindFramebuffer(gl.FRAMEBUFFER, gl.createFramebuffer()); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0); gl.bindTexture(gl.TEXTURE_2D, null);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); gl.bindTexture(gl.TEXTURE_2D, null); use(texture);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); gl.bindTexture(gl.TEXTURE_2D, null); gl.bindTexture(gl.TEXTURE_2D, texture);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); gl.bindTexture(gl.TEXTURE_2D, {}); gl.bindTexture(gl.TEXTURE_2D, null);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); gl.bindTexture(gl.TEXTURE_2D, null); gl.bindTexture(gl.TEXTURE_2D, null);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); { gl.activeTexture(gl.TEXTURE1); } gl.bindTexture(gl.TEXTURE_2D, null);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); if (ready) gl.bindTexture(gl.TEXTURE_2D, null);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); { gl.bindTexture(gl.TEXTURE_2D, null); }',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, texture); helper(); gl.bindTexture(gl.TEXTURE_2D, null);',
    'const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); helper(gl.bindTexture(gl.TEXTURE_2D, texture)); gl.bindTexture(gl.TEXTURE_2D, null);',
])
def test_texture_retire_rejects_unproven_or_unsafe_sites(js):
    assert not [edit for edit in mutator._edits(js) if edit[0] == 'texture_retire']


@pytest.mark.parametrize('js', [
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f); gl.bindFramebuffer(gl.READ_FRAMEBUFFER, null);',
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f); helper(); gl.bindFramebuffer(gl.FRAMEBUFFER, null);',
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f); gl.bindFramebuffer(gl.FRAMEBUFFER, null); use(f);',
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); const closure = () => f; gl.bindFramebuffer(gl.FRAMEBUFFER, f); gl.bindFramebuffer(gl.FRAMEBUFFER, null);',
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); const alias = f; gl.bindFramebuffer(gl.FRAMEBUFFER, f); gl.bindFramebuffer(gl.FRAMEBUFFER, null);',
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); const holder = {f}; gl.bindFramebuffer(gl.FRAMEBUFFER, f); gl.bindFramebuffer(gl.FRAMEBUFFER, null);',
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f); if (ready) gl.bindFramebuffer(gl.FRAMEBUFFER, null);',
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f); gl.deleteFramebuffer(f); gl.bindFramebuffer(gl.FRAMEBUFFER, null);',
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f, extra); gl.bindFramebuffer(gl.FRAMEBUFFER, null);',
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f); { gl.bindFramebuffer(gl.FRAMEBUFFER, null); }',
    'const gl = canvas.getContext("webgl2"); const f = gl.createFramebuffer(); const other = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f); { gl.bindFramebuffer(gl.FRAMEBUFFER, other); } gl.bindFramebuffer(gl.FRAMEBUFFER, null);',
    'const gl = canvas.getContext("webgl2"); const gl2 = other.getContext("webgl2"); const f = gl2.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f); gl.bindFramebuffer(gl.FRAMEBUFFER, null);',
])
def test_framebuffer_retire_rejects_unproven_or_unsafe_sites(js):
    assert not [edit for edit in mutator._edits(js) if edit[0] == 'framebuffer_retire']


def paired_varying_seed(vertex_source=None, fragment_source=None, setup='', link='gl.linkProgram(program);'):
    vertex_source = vertex_source or ("#version 300 es\nin vec2 position;\nout vec2 uv;\n"
                                      "// uv remains in this comment\n"
                                      "void main() { gl_Position = vec4(position, 0.0, 1.0); uv = position; }\n")
    fragment_source = fragment_source or ("#version 300 es\nprecision mediump float;\nin vec2 uv;\n"
                                          "out vec4 color;\n"
                                          "void main() { color = vec4(uv * 0.5 + 0.5, 0.0, 1.0); }\n")
    js = ('const gl = canvas.getContext("webgl2"); '
          'const vertex = gl.createShader(gl.VERTEX_SHADER); '
          'const fragment = gl.createShader(gl.FRAGMENT_SHADER); '
          f'gl.shaderSource(vertex, `{vertex_source}`); '
          f'gl.shaderSource(fragment, `{fragment_source}`); '
          'gl.compileShader(vertex); gl.compileShader(fragment); '
          'const program = gl.createProgram(); '
          f'{setup}gl.attachShader(program, vertex); gl.attachShader(program, fragment); {link}')
    return f'<script>{js}</script>'.encode()


@pytest.mark.skipif(not mutator.GLSLANG, reason='glslangValidator is unavailable')
def test_linked_varying_rename_edits_both_stages_and_replays_exactly():
    source = paired_varying_seed()
    js = mutator._script(source)[1]
    candidates = [edit for edit in mutator._edits(js) if edit[0] == 'glsl_linked_varying_rename']
    assert len(candidates) == 1 and len(candidates[0][1]) == 4
    output, edits = mutator.mutate_bytes(source, __import__('random').Random(0), max_edits=1)
    again, same = mutator.mutate_bytes(source, __import__('random').Random(0), max_edits=1)
    assert output == again and edits == same
    assert edits[0]['operator'] == 'glsl_linked_varying_rename'
    assert len(edits[0]['spans']) == 4
    assert b'// uv remains in this comment' in output
    assert output.count(b'mut_varying_0') == 4
    generated = {span['replacement'] for span in edits[0]['spans']}
    assert generated == {'mut_varying_0'}
    assert all(not name.startswith(('webgl_', 'gl_')) for name in generated)
    assert mutator.replay(source, {'edits': edits}) == output


@pytest.mark.skipif(not mutator.GLSLANG, reason='glslangValidator is unavailable')
def test_linked_varying_rename_coexists_with_disjoint_edit_and_replays():
    source = paired_varying_seed()
    output, edits = mutator.mutate_bytes(source, __import__('random').Random(0), max_edits=3)
    assert 'glsl_linked_varying_rename' in {edit['operator'] for edit in edits}
    spans = [span for edit in edits for span in mutator._edit_spans(edit)]
    assert all(not (left['start'] < right['end'] and right['start'] < left['end'])
               for index, left in enumerate(spans) for right in spans[index + 1:])
    assert mutator.replay(source, {'edits': edits}) == output


@pytest.mark.skipif(not mutator.GLSLANG, reason='glslangValidator is unavailable')
@pytest.mark.parametrize('source', [
    paired_varying_seed(setup='helper(); '),
    paired_varying_seed(link=''),
    paired_varying_seed(link='gl.linkProgram(program); gl.linkProgram(program);'),
    paired_varying_seed(fragment_source='#version 300 es\nprecision mediump float; in vec3 uv; out vec4 color; void main(){color=vec4(uv,1.0);}\n'),
    paired_varying_seed(vertex_source='#version 300 es\n#define SCALE 1.0\nin vec2 position; out vec2 uv; void main(){gl_Position=vec4(position,0.0,1.0);uv=position*SCALE;}\n'),
    paired_varying_seed(vertex_source='#version 300 es\nin vec2 position; out vec2 uv; void main(){gl_Position=vec4(position,0.0,1.0);uv=position+${offset};}\n'),
    paired_varying_seed(setup='gl.attachShader(program, vertex); '),
    paired_varying_seed(setup='gl.shaderSource(vertex, `#version 300 es\\nvoid main(){gl_Position=vec4(0.0);}`); '),
])
def test_linked_varying_rename_rejects_ambiguous_or_unproven_pairs(source):
    assert not [edit for edit in mutator._edits(mutator._script(source)[1])
                if edit[0] == 'glsl_linked_varying_rename']


@pytest.mark.skipif(not mutator.GLSLANG, reason='glslangValidator is unavailable')
def test_linked_varying_rename_rejects_wrong_context_shader():
    source = paired_varying_seed().decode().replace(
        'const gl = canvas.getContext("webgl2");',
        'const gl = canvas.getContext("webgl2"); const other = canvas2.getContext("webgl2");')
    source = source.replace('const fragment = gl.createShader(gl.FRAGMENT_SHADER);',
                            'const fragment = other.createShader(other.FRAGMENT_SHADER);')
    assert not [edit for edit in mutator._edits(mutator._script(source.encode())[1])
                if edit[0] == 'glsl_linked_varying_rename']


def test_linked_varying_rename_rejects_reassigned_and_shadowed_resources():
    source = paired_varying_seed().decode()
    reassigned_program = source.replace('const program = gl.createProgram();',
                                         'let program = gl.createProgram(); program = gl.createProgram();')
    shadowed_program = source.replace('gl.linkProgram(program);',
                                      'function f({program}) { gl.linkProgram(program); }')
    assert not [edit for edit in mutator._edits(mutator._script(reassigned_program.encode())[1])
                if edit[0] == 'glsl_linked_varying_rename']
    assert not [edit for edit in mutator._edits(mutator._script(shadowed_program.encode())[1])
                if edit[0] == 'glsl_linked_varying_rename']


@pytest.mark.parametrize('source', [
    validation_seed(target='gl.ELEMENT_ARRAY_BUFFER'),
    validation_seed(data='new Uint8Array(0)'),
    validation_seed(offset='13'),
    validation_seed(allocation='0'),
    validation_seed(suffix='helper(); '),
    validation_seed(suffix='gl.viewport(0, 0, 64, 64); '),
    b'<script>const gl = canvas.getContext("webgl2"); gl.bindBuffer(gl.ARRAY_BUFFER, buffer); '
    b'gl.bufferData(gl.ARRAY_BUFFER, 16, gl.STATIC_DRAW); '
    b'gl.bufferSubData(gl.ARRAY_BUFFER, 0, new Uint8Array(4));</script>',
])
def test_validation_arm_rejects_unproven_or_invalid_boundary_sites(source):
    with pytest.raises(ValueError, match='validation mutation'):
        mutator.mutate_bytes(source, __import__('random').Random(3), arm='validation')


def test_context_shadowing_and_cross_context_binding_are_rejected():
    shadowed = 'const gl = canvas.getContext("webgl2"); function f({gl}) { gl.drawArrays(gl.TRIANGLES, 0, 3); }'
    assert not mutator._edits(shadowed)
    crossed = ('const first = a.getContext("webgl2"); const second = b.getContext("webgl2"); '
               'first.bindBuffer(first.ARRAY_BUFFER, buffer); '
               'second.bufferData(first.ARRAY_BUFFER, 32, second.STATIC_DRAW);')
    assert not [e for e in mutator._edits(crossed) if e[0] == 'resource_storage']


def test_const_counts_and_draw_elements_use_count_argument():
    js = 'const gl = canvas.getContext("webgl2"); const count = 7; gl.drawElements(gl.TRIANGLES, count, gl.UNSIGNED_SHORT, 0);'
    call_count = js.rindex('count')
    assert ('bounded_parameter', call_count, call_count + 5, '6') in mutator._edits(js)


@pytest.mark.parametrize(('call', 'count_name'), [
    ('gl.drawArraysInstanced(gl.TRIANGLES, 0, 3, instances)', 'instances'),
    ('gl.drawElementsInstanced(gl.TRIANGLES, 3, gl.UNSIGNED_SHORT, 0, instances)', 'instances'),
])
def test_instanced_draw_instance_count_shrinks(call, count_name):
    js = f'const gl = canvas.getContext("webgl2"); const instances = 9; {call};'
    pos = js.rindex(count_name)
    edits = [e for e in mutator._edits(js) if e[0] == 'bounded_parameter' and e[1:3] == (pos, pos + len(count_name))]
    assert {e[3] for e in edits} == {'0', '4', '8'}


@pytest.mark.parametrize(('call', 'name'), [
    ('gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 12, 8);', 'vertexAttribPointer'),
    ('gl.vertexAttribIPointer(0, 2, gl.SHORT, 8, 4);', 'vertexAttribIPointer'),
])
def test_vertex_attrib_pointer_shrinks_offset_and_safe_stride(call, name):
    js = 'const gl = canvas.getContext("webgl2"); ' + call
    edits = [e for e in mutator._edits(js) if e[0] in ('vertex_attrib_offset', 'vertex_attrib_stride')]
    assert {e[0] for e in edits} == {'vertex_attrib_offset', 'vertex_attrib_stride'}
    assert {e[3] for e in edits} == {'0'}


@pytest.mark.parametrize('call', [
    'gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 8, 4);',
    'gl.vertexAttribPointer(0, 4, gl.UNSIGNED_INT_2_10_10_10_REV, true, 16, 4);',
    'gl.vertexAttribIPointer(0, 2, gl.UNSIGNED_INT, 4, 4);',
    'gl.vertexAttribPointer(0, 0, gl.FLOAT, false, 0, 4, extra);',
])
def test_vertex_attrib_pointer_does_not_shrink_unsafe_stride(call):
    js = 'const gl = canvas.getContext("webgl2"); ' + call
    edits = [e for e in mutator._edits(js) if e[0] == 'vertex_attrib_stride']
    assert not edits


def test_vertex_attrib_pointer_offset_shrinks_independent_of_stride():
    js = 'const gl = canvas.getContext("webgl2"); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 8, 4);'
    edits = [e for e in mutator._edits(js) if e[0] == 'vertex_attrib_offset']
    assert len(edits) == 1 and edits[0][3] == '0'


def test_tex_sub_image_dimensions_shrink_at_width_and_height_positions():
    js = ('const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); '
          'const width = 7; const height = 4; gl.bindTexture(gl.TEXTURE_2D, texture); '
          'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 16, 16, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(1024)); '
          'gl.texSubImage2D(gl.TEXTURE_2D, 0, 2, 3, width, height, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(256));')
    expected = {'width': '3', 'height': '2'}
    for name, replacement in expected.items():
        start = js.index(name, js.index('gl.texSubImage2D'))
        assert ('texture_subimage_dimension', start, start + len(name), replacement) in mutator._edits(js)


def test_tex_sub_image_requires_prior_full_non_null_initialization():
    prefix = ('const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); '
              'gl.bindTexture(gl.TEXTURE_2D, texture); ')
    allocation = 'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 16, 16, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(1024)); '
    update = 'gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 8, 8, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(256));'
    assert any(e[0] == 'texture_subimage_dimension' for e in mutator._edits(prefix + allocation + update))
    null_allocation = allocation.replace('new Uint8Array(1024)', 'null')
    assert not [e for e in mutator._edits(prefix + null_allocation + update)
                if e[0] == 'texture_subimage_dimension']
    other_level = update.replace('TEXTURE_2D, 0,', 'TEXTURE_2D, 1,')
    assert not [e for e in mutator._edits(prefix + allocation + other_level)
                if e[0] == 'texture_subimage_dimension']


def test_tex_sub_image_rejects_non_null_alias_without_non_null_proof():
    js = ('const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); '
          'const pixels = null; gl.bindTexture(gl.TEXTURE_2D, texture); '
          'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 16, 16, 0, gl.RGBA, gl.UNSIGNED_BYTE, pixels); '
          'gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 8, 8, gl.RGBA, gl.UNSIGNED_BYTE, pixels);')
    assert not [e for e in mutator._edits(js) if e[0] == 'texture_subimage_dimension']


@pytest.mark.parametrize('intervening', [
    'gl.bindTexture(gl.TEXTURE_2D, other); ',
    'gl.activeTexture(gl.TEXTURE1); ',
    'replaceTexture(); ',
])
def test_tex_sub_image_initialization_proof_is_invalidated_by_state_changes(intervening):
    js = ('const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); '
          'gl.bindTexture(gl.TEXTURE_2D, texture); '
          'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 16, 16, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(1024)); '
          + intervening +
          'gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 8, 8, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(256));')
    assert not [e for e in mutator._edits(js) if e[0] == 'texture_subimage_dimension']


@pytest.mark.parametrize('nested', [
    'gl.bindTexture(gl.TEXTURE_2D, other);',
    'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 16, 16, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);',
])
def test_nested_texture_state_changes_invalidate_outer_initialization(nested):
    js = ('const gl = canvas.getContext("webgl2"); const texture = gl.createTexture(); '
          'gl.bindTexture(gl.TEXTURE_2D, texture); '
          'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 16, 16, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(1024)); '
          '{ ' + nested + ' } '
          'gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 8, 8, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(256));')
    assert not [e for e in mutator._edits(js) if e[0] == 'texture_subimage_dimension']


def test_tex_sub_image_requires_nine_argument_overload():
    js = 'const gl = canvas.getContext("webgl2"); gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 4, 4, gl.RGBA, gl.UNSIGNED_BYTE, pixels, extra);'
    assert not [e for e in mutator._edits(js) if e[0] == 'texture_subimage_dimension']


def test_draw_range_and_instanced_vertex_counts_shrink():
    js = ('const gl = canvas.getContext("webgl2"); const count = 9; const instances = 5; '
          'gl.drawRangeElements(gl.TRIANGLES, 0, 8, count, gl.UNSIGNED_SHORT, 0); '
          'gl.drawArraysInstanced(gl.TRIANGLES, 0, count, instances); '
          'gl.drawElementsInstanced(gl.TRIANGLES, count, gl.UNSIGNED_SHORT, 0, instances);')
    edits = [e for e in mutator._edits(js) if e[0] == 'bounded_parameter']
    positions = {e[1] for e in edits}
    draw_range_count = js.index('count, gl.UNSIGNED_SHORT')
    assert draw_range_count in positions
    assert js.index('count, instances') in positions
    assert js.index('instances);') in positions
    draw_arrays_count = js.index('count, instances')
    draw_elements_count = js.rindex('count, gl.UNSIGNED_SHORT')
    assert draw_elements_count != draw_range_count
    assert {e[3] for e in edits if e[1] == draw_range_count} == {'0', '4', '8'}
    assert {e[3] for e in edits if e[1] == draw_arrays_count} == {'0', '4', '8'}
    assert {e[3] for e in edits if e[1] == draw_elements_count} == {'0', '4', '8'}


def test_draw_range_elements_requires_exact_arity():
    js = 'const gl = canvas.getContext("webgl2"); gl.drawRangeElements(gl.TRIANGLES, 0, 8, 9, gl.UNSIGNED_SHORT, 0, extra);'
    assert not [e for e in mutator._edits(js) if e[0] == 'bounded_parameter']


@pytest.mark.parametrize('call', [
    'gl.drawArrays(gl.TRIANGLES, 0, 3);',
    'gl.drawElements(gl.TRIANGLES, 3, gl.UNSIGNED_SHORT, 0);',
    'gl.drawRangeElements(gl.TRIANGLES, 0, 2, 3, gl.UNSIGNED_SHORT, 0);',
    'gl.drawArraysInstanced(gl.TRIANGLES, 0, 3, 2);',
    'gl.drawElementsInstanced(gl.TRIANGLES, 3, gl.UNSIGNED_SHORT, 0, 2);',
])
def test_draw_mode_operator_covers_exact_draw_signatures(call):
    js = 'const gl = canvas.getContext("webgl2"); ' + call
    edits = [e for e in mutator._edits(js) if e[0] == 'draw_mode']
    assert len(edits) == 6
    assert all(e[1:3] == (js.index('gl.TRIANGLES'), js.index('gl.TRIANGLES') + len('gl.TRIANGLES'))
               for e in edits)
    assert {e[3] for e in edits} == {f'gl.{name}' for name in (
        'POINTS', 'LINES', 'LINE_LOOP', 'LINE_STRIP', 'TRIANGLE_STRIP', 'TRIANGLE_FAN')}


def test_draw_mode_operator_resolves_safe_const_alias():
    js = ('const gl = canvas.getContext("webgl2"); const mode = gl.TRIANGLES; '
          'gl.drawArrays(mode, 0, 3);')
    edits = [e for e in mutator._edits(js) if e[0] == 'draw_mode']
    assert len(edits) == 6
    assert all(e[1:3] == (js.rindex('mode'), js.rindex('mode') + len('mode')) for e in edits)


@pytest.mark.parametrize('js', [
    'const gl = {}; gl.drawArrays(gl.TRIANGLES, 0, 3);',
    'const gl = canvas.getContext("webgl2"); gl.drawArrays(gl.UNKNOWN, 0, 3);',
    'const gl = canvas.getContext("webgl2"); gl.drawArrays(gl.TRIANGLES, 0, 3, 4);',
])
def test_draw_mode_operator_rejects_unknown_receiver_mode_or_arity(js):
    assert not [e for e in mutator._edits(js) if e[0] == 'draw_mode']


@pytest.mark.parametrize('feedback', [
    'gl.beginTransformFeedback(gl.TRIANGLES);',
    'gl.pauseTransformFeedback();',
    'gl.resumeTransformFeedback();',
    'gl.endTransformFeedback();',
])
def test_draw_mode_operator_skips_uncertain_transform_feedback_state(feedback):
    js = ('const gl = canvas.getContext("webgl2"); ' + feedback +
          ' gl.drawArrays(gl.TRIANGLES, 0, 3);')
    assert not [e for e in mutator._edits(js) if e[0] == 'draw_mode']


def test_draw_mode_operator_skips_nested_or_opaque_transform_feedback_changes():
    nested = ('const gl = canvas.getContext("webgl2"); { gl.beginTransformFeedback(gl.TRIANGLES); } '
              'gl.drawArrays(gl.TRIANGLES, 0, 3);')
    opaque = ('const gl = canvas.getContext("webgl2"); const begin = gl.beginTransformFeedback; '
              'gl.drawArrays(gl.TRIANGLES, 0, 3);')
    assert not [e for e in mutator._edits(nested) if e[0] == 'draw_mode']
    assert not [e for e in mutator._edits(opaque) if e[0] == 'draw_mode']


def test_draw_mode_ignores_ordinary_dom_lookup_and_entrypoint_calls():
    js = ('const gl = canvas.getContext("webgl2"); document.getElementById("canvas"); '
          'function main() { gl.drawArrays(gl.TRIANGLES, 0, 3); } main();')
    assert [e for e in mutator._edits(js) if e[0] == 'draw_mode']


def test_use_program_temporarily_unbinds_and_restores_declared_program():
    js = ('const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); '
          'gl.useProgram(program);')
    edit = next(e for e in mutator._edits(js) if e[0] == 'state_transition')
    assert edit[3] == 'gl.useProgram(null); gl.useProgram(program);'


def test_use_program_transition_skips_when_program_deletion_is_present():
    js = ('const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); '
          'gl.useProgram(program); gl.deleteProgram(program); gl.useProgram(program);')
    assert not [e for e in mutator._edits(js)
                if e[0] == 'state_transition' and 'useProgram' in e[3]]


@pytest.mark.parametrize('js', [
    'const gl = canvas.getContext("webgl2"); gl.useProgram(program);',
    'const gl = canvas.getContext("webgl2"); gl.useProgram(gl.createProgram());',
    'const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); gl.useProgram(program, extra);',
    ('const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); '
     'gl.beginTransformFeedback(gl.TRIANGLES); gl.useProgram(program);'),
])
def test_use_program_transition_rejects_undeclared_expression_arity_or_feedback(js):
    assert not [e for e in mutator._edits(js) if e[0] == 'state_transition']


def test_sync_placement_wraps_only_standalone_unconditional_draw_statements():
    js = ('const gl = canvas.getContext("webgl2"); gl.drawArrays(gl.TRIANGLES, 0, 3); '
          'if (ready) gl.drawArrays(gl.TRIANGLES, 0, 3);')
    edits = [e for e in mutator._edits(js) if e[0] == 'sync_placement']
    assert len(edits) == 2
    assert {e[3] for e in edits} == {
        'gl.flush(); gl.drawArrays(gl.TRIANGLES, 0, 3);',
        'gl.drawArrays(gl.TRIANGLES, 0, 3); gl.flush();',
    }


@pytest.mark.parametrize(('target', 'subdata', 'draw'), [
    ('ARRAY_BUFFER', 'gl.bufferSubData(gl.ARRAY_BUFFER, 0, new Uint8Array(4));',
     'gl.drawArrays(gl.TRIANGLES, 0, 3);'),
    ('ELEMENT_ARRAY_BUFFER', 'gl.bufferSubData(gl.ELEMENT_ARRAY_BUFFER, 0, new Uint16Array(3));',
     'gl.drawElements(gl.TRIANGLES, 3, gl.UNSIGNED_SHORT, 0);'),
])
def test_buffer_redefine_after_upload_requires_later_draw(target, subdata, draw):
    js = ('const gl = canvas.getContext("webgl2"); const buffer = gl.createBuffer(); '
          f'gl.bindBuffer(gl.{target}, buffer); const size = 64; const usage = gl.STATIC_DRAW; '
          f'gl.bufferData(gl.{target}, size, usage); {subdata} {draw}')
    edit = next(e for e in mutator._edits(js) if e[0] == 'buffer_redefine_after_upload')
    assert edit[3] == f'{subdata} gl.bufferData(gl.{target}, size, usage);'


def test_unrelated_buffer_target_bind_preserves_array_buffer_proof():
    js = ('const gl = canvas.getContext("webgl2"); const geometry = gl.createBuffer(); '
          'const scratch = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, geometry); '
          'gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'gl.bufferSubData(gl.ARRAY_BUFFER, 0, new Uint8Array(4)); '
          'gl.bindBuffer(gl.UNIFORM_BUFFER, scratch); gl.drawArrays(gl.TRIANGLES, 0, 3);')
    assert any(e[0] == 'buffer_redefine_after_upload' for e in mutator._edits(js))


@pytest.mark.parametrize('sequence', [
    ('gl.bindBuffer(gl.ARRAY_BUFFER, first); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
     'gl.bindBuffer(gl.ARRAY_BUFFER, second); gl.bufferSubData(gl.ARRAY_BUFFER, 0, new Uint8Array(4)); '
     'gl.drawArrays(gl.TRIANGLES, 0, 3);'),
    ('gl.bindBuffer(gl.ARRAY_BUFFER, first); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
     'gl.bufferSubData(gl.ELEMENT_ARRAY_BUFFER, 0, new Uint16Array(3)); gl.drawArrays(gl.TRIANGLES, 0, 3);'),
    ('gl.bindBuffer(gl.ARRAY_BUFFER, first); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
     'gl.bufferSubData(gl.ARRAY_BUFFER, 0, new Uint8Array(4)); gl.bindBuffer(gl.ARRAY_BUFFER, second); '
     'gl.drawArrays(gl.TRIANGLES, 0, 3);'),
])
def test_buffer_redefine_after_upload_rejects_resource_target_or_rebind_mismatch(sequence):
    js = 'const gl = canvas.getContext("webgl2"); const first = gl.createBuffer(); const second = gl.createBuffer(); ' + sequence
    assert not [e for e in mutator._edits(js) if e[0] == 'buffer_redefine_after_upload']


@pytest.mark.parametrize('after_upload', [
    'mutateBuffer();',
    'gl.deleteBuffer(buffer);',
    'gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW);',
])
def test_buffer_redefine_after_upload_rejects_intervening_state_changes(after_upload):
    js = ('const gl = canvas.getContext("webgl2"); const buffer = gl.createBuffer(); '
          'gl.bindBuffer(gl.ARRAY_BUFFER, buffer); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'gl.bufferSubData(gl.ARRAY_BUFFER, 0, new Uint8Array(4)); ' + after_upload +
          ' gl.drawArrays(gl.TRIANGLES, 0, 3);')
    assert not [e for e in mutator._edits(js) if e[0] == 'buffer_redefine_after_upload']


def glsl_seed(source, stage='VERTEX_SHADER'):
    return (f'<script>const gl = canvas.getContext("webgl2"); '
            f'const shader = gl.createShader(gl.{stage}); '
            f'gl.shaderSource(shader, `{source}`);</script>').encode()


def glsl_edits(source, stage='VERTEX_SHADER'):
    return mutator._edits(mutator._script(glsl_seed(source, stage))[1])


@pytest.mark.skipif(not mutator.GLSLANG, reason='glslangValidator is unavailable')
@pytest.mark.parametrize(('source', 'operator', 'replacement'), [
    ('#version 300 es\nvoid main(){mat2 m=mat2(0.0); gl_Position=vec4(m[0],0.0,0.0);}',
     'glsl_matrix_scalar', '1.0'),
    ('#version 300 es\nvoid main(){float x=sin(1.0); gl_Position=vec4(x);}',
     'glsl_trig_function', 'cos'),
    ('#version 300 es\nvoid main(){float values[4]=float[4](0.0,1.0,2.0,3.0); float x=values[2]; gl_Position=vec4(x);}',
     'glsl_array_index', '1'),
    ('#version 300 es\nvoid main(){float x=0.0; for(int i=0;i<4;i++){x+=1.0;} gl_Position=vec4(x);}',
     'glsl_loop_bound', '3'),
])
def test_glsl_source_operators_compile_each_supported_subtype(source, operator, replacement):
    edits = [e for e in glsl_edits(source) if e[0] == operator]
    assert edits and all(e[3] == replacement for e in edits)


@pytest.mark.skipif(not mutator.GLSLANG, reason='glslangValidator is unavailable')
def test_glsl_source_skips_comments_interpolation_wrong_stage_and_compile_failures(monkeypatch):
    commented = glsl_seed('#version 300 es\nvoid main(){/* sin(1.0); mat2(0.0); */ gl_Position=vec4(0.0);}')
    assert not [e for e in mutator._edits(mutator._script(commented)[1]) if e[0].startswith('glsl_')]
    interpolated = glsl_seed('#version 300 es\nvoid main(){float x=sin(${angle}); gl_Position=vec4(x);}')
    assert not [e for e in mutator._edits(mutator._script(interpolated)[1]) if e[0].startswith('glsl_')]
    wrong_stage = glsl_seed('#version 300 es\nvoid main(){gl_Position=vec4(sin(1.0));}', 'FRAGMENT_SHADER')
    assert not [e for e in mutator._edits(mutator._script(wrong_stage)[1]) if e[0].startswith('glsl_')]
    monkeypatch.setattr(mutator, '_glsl_compiles', lambda stage, source: False)
    candidate = glsl_seed('#version 300 es\nvoid main(){float x=sin(1.0); gl_Position=vec4(x);}')
    assert not [e for e in mutator._edits(mutator._script(candidate)[1]) if e[0].startswith('glsl_')]


@pytest.mark.skipif(not mutator.GLSLANG, reason='glslangValidator is unavailable')
def test_glsl_loop_bound_skips_array_initialization_loops():
    source = ('#version 300 es\nvoid main(){float values[4]; '
              'for(int i=0;i<4;i++){values[i]=float(i);} '
              'gl_Position=vec4(values[3]);}')
    assert not [e for e in glsl_edits(source) if e[0] == 'glsl_loop_bound']


@pytest.mark.skipif(not mutator.GLSLANG, reason='glslangValidator is unavailable')
def test_glsl_source_edits_replay_deterministically():
    source = glsl_seed('#version 300 es\nvoid main(){float x=sin(1.0); mat2 m=mat2(0.0); gl_Position=vec4(x+m[0],0.0,0.0);}')
    first, edits = mutator.mutate_bytes(source, __import__('random').Random(918))
    second, again = mutator.mutate_bytes(source, __import__('random').Random(918))
    assert (first, edits) == (second, again)
    assert mutator.replay(source, {'edits': edits}) == first


def test_vertex_array_switch_invalidates_element_buffer_proof():
    js = ('const gl = canvas.getContext("webgl2"); const first = gl.createBuffer(); '
          'const vaoA = gl.createVertexArray(); const vaoB = gl.createVertexArray(); '
          'gl.bindVertexArray(vaoA); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, first); '
          'gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'gl.bufferSubData(gl.ELEMENT_ARRAY_BUFFER, 0, new Uint16Array(3)); '
          'gl.bindVertexArray(vaoB); gl.bufferSubData(gl.ELEMENT_ARRAY_BUFFER, 0, new Uint16Array(3)); '
          'gl.drawElements(gl.TRIANGLES, 3, gl.UNSIGNED_SHORT, 0);')
    assert not [e for e in mutator._edits(js) if e[0] == 'buffer_redefine_after_upload']


def test_compatible_buffer_switch_preserves_array_storage_capacity():
    js = ('const gl = canvas.getContext("webgl2"); const first = gl.createBuffer(); '
          'const second = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, first); '
          'gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'gl.bindBuffer(gl.ARRAY_BUFFER, second); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'gl.bindBuffer(gl.ARRAY_BUFFER, first); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);')
    edit = next(e for e in mutator._edits(js) if e[0] == 'compatible_buffer_switch')
    assert edit == ('compatible_buffer_switch', js.rindex('first'), js.rindex('first') + len('first'), 'second')


@pytest.mark.parametrize('setup', [
    'gl.bufferData(gl.ARRAY_BUFFER, 32, gl.STATIC_DRAW);',
    'gl.deleteBuffer(second);',
])
def test_compatible_buffer_switch_rejects_wrong_size_deleted_or_intervening_reallocation(setup):
    js = ('const gl = canvas.getContext("webgl2"); const first = gl.createBuffer(); '
          'const second = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, first); '
          'gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'gl.bindBuffer(gl.ARRAY_BUFFER, second); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          + setup + ' gl.bindBuffer(gl.ARRAY_BUFFER, first); '
          'gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);')
    assert not [e for e in mutator._edits(js) if e[0] == 'compatible_buffer_switch']


def test_compatible_buffer_switch_rejects_wrong_context_and_array_mutation_before_capture():
    wrong_context = ('const gl = canvas.getContext("webgl2"); const other = canvas2.getContext("webgl2"); '
                     'const first = gl.createBuffer(); const second = gl.createBuffer(); '
                     'gl.bindBuffer(gl.ARRAY_BUFFER, first); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
                     'gl.bindBuffer(gl.ARRAY_BUFFER, second); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
                     'other.bindBuffer(other.ARRAY_BUFFER, first); other.vertexAttribPointer(0, 3, other.FLOAT, false, 0, 0);')
    intervening = ('const gl = canvas.getContext("webgl2"); const first = gl.createBuffer(); '
                   'const second = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, first); '
                   'gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
                   'gl.bindBuffer(gl.ARRAY_BUFFER, second); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
                   'gl.bindBuffer(gl.ARRAY_BUFFER, first); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
                   'gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);')
    for js in (wrong_context, intervening):
        assert not [e for e in mutator._edits(js) if e[0] == 'compatible_buffer_switch']


def test_compatible_buffer_switch_rejects_opaque_helper_between_proofs_and_rebind():
    js = ('const gl = canvas.getContext("webgl2"); const first = gl.createBuffer(); '
          'const second = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, first); '
          'gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'gl.bindBuffer(gl.ARRAY_BUFFER, second); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'helper(); gl.bindBuffer(gl.ARRAY_BUFFER, first); '
          'gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);')
    assert not [e for e in mutator._edits(js) if e[0] == 'compatible_buffer_switch']


def test_compatible_buffer_switch_invalidates_outer_caps_after_nested_reallocation():
    js = ('const gl = canvas.getContext("webgl2"); const first = gl.createBuffer(); '
          'const second = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, first); '
          'gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'gl.bindBuffer(gl.ARRAY_BUFFER, second); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          '{ gl.bindBuffer(gl.ARRAY_BUFFER, second); gl.bufferData(gl.ARRAY_BUFFER, 4, gl.STATIC_DRAW); } '
          'gl.bindBuffer(gl.ARRAY_BUFFER, first); '
          'gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0); gl.drawArrays(gl.TRIANGLES, 0, 12);')
    assert not [e for e in mutator._edits(js) if e[0] == 'compatible_buffer_switch']


@pytest.mark.parametrize('intervening', [
    'gl.bufferSubData(gl.ARRAY_BUFFER, 0, new Uint8Array(4));',
    'gl.bindBuffer(gl.ARRAY_BUFFER, third);',
    'gl.deleteBuffer(second);',
])
def test_compatible_buffer_switch_rejects_array_changes_before_attribute_capture(intervening):
    js = ('const gl = canvas.getContext("webgl2"); const first = gl.createBuffer(); '
          'const second = gl.createBuffer(); const third = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, first); '
          'gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'gl.bindBuffer(gl.ARRAY_BUFFER, second); gl.bufferData(gl.ARRAY_BUFFER, 64, gl.STATIC_DRAW); '
          'gl.bindBuffer(gl.ARRAY_BUFFER, first); ' + intervening +
          ' gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);')
    assert not [e for e in mutator._edits(js) if e[0] == 'compatible_buffer_switch']


def test_instanced_draw_requires_exact_arity():
    js = 'const gl = canvas.getContext("webgl2"); gl.drawArraysInstanced(gl.TRIANGLES, 0, 3, 9, extra);'
    assert not [e for e in mutator._edits(js) if e[0] == 'bounded_parameter']


def test_numeric_const_is_not_used_through_shadowing_parameters():
    arrow = ('const gl = canvas.getContext("webgl2"); const instances = 2; '
             'const draw = instances => gl.drawArraysInstanced(gl.TRIANGLES, 0, 3, instances);')
    catch = ('const gl = canvas.getContext("webgl2"); const instances = 2; '
             'try {} catch (instances) { gl.drawArraysInstanced(gl.TRIANGLES, 0, 3, instances); }')
    assert not [e for e in mutator._edits(arrow) if e[0] == 'bounded_parameter' and e[1] == arrow.rindex('instances')]
    assert not [e for e in mutator._edits(catch) if e[0] == 'bounded_parameter' and e[1] == catch.rindex('instances')]


def test_shadowed_storage_size_cannot_bypass_duplication_cap():
    arrow = ('const gl = canvas.getContext("webgl2"); const size = 32; '
             'gl.bindBuffer(gl.ARRAY_BUFFER, buffer); const upload = size => '
             'gl.bufferData(gl.ARRAY_BUFFER, size, gl.STATIC_DRAW);')
    catch = ('const gl = canvas.getContext("webgl2"); const size = 32; '
             'gl.bindBuffer(gl.ARRAY_BUFFER, buffer); try {} catch (size) '
             '{ gl.bufferData(gl.ARRAY_BUFFER, size, gl.STATIC_DRAW); }')
    assert not [e for e in mutator._edits(arrow) if e[0] == 'storage_duplicate']
    assert not [e for e in mutator._edits(catch) if e[0] == 'storage_duplicate']


def test_enum_alias_is_not_used_through_shadowing_parameter():
    js = ('const gl = canvas.getContext("webgl2"); const target = gl.ARRAY_BUFFER; '
          'const upload = target => { gl.bindBuffer(target, buffer); '
          'gl.bufferData(target, 32, gl.STATIC_DRAW); };')
    assert not [e for e in mutator._edits(js) if e[0] == 'storage_duplicate']


def test_destructured_numeric_bindings_shadow_outer_constants():
    draw = ('const gl = canvas.getContext("webgl2"); const instances = 9; '
            '{ const {instances} = {instances: 1}; '
            'gl.drawArraysInstanced(gl.TRIANGLES, 0, 3, instances); }')
    storage = ('const gl = canvas.getContext("webgl2"); const size = 128; '
               '{ const {size} = {size: 100000000}; gl.bindBuffer(gl.ARRAY_BUFFER, buffer); '
               'gl.bufferData(gl.ARRAY_BUFFER, size, gl.STATIC_DRAW); }')
    assert not [e for e in mutator._edits(draw) if e[0] == 'bounded_parameter' and e[1] == draw.rindex('instances')]
    assert not [e for e in mutator._edits(storage) if e[0] == 'storage_duplicate']


def test_destructured_enum_alias_shadows_outer_alias():
    js = ('const gl = canvas.getContext("webgl2"); const target = gl.ARRAY_BUFFER; '
          '{ const {target} = values; gl.bindBuffer(target, buffer); '
          'gl.bufferData(target, 32, gl.STATIC_DRAW); }')
    assert not [e for e in mutator._edits(js) if e[0] == 'storage_duplicate']


def test_function_scoped_var_shadows_outer_numeric_constant():
    js = ('const gl = canvas.getContext("webgl2"); const instances = 9; '
          'function draw(flag) { if (flag) { var instances = 1; } '
          'gl.drawArraysInstanced(gl.TRIANGLES, 0, 3, instances); }')
    assert not [e for e in mutator._edits(js) if e[0] == 'bounded_parameter' and e[1] == js.rindex('instances')]


def test_buffer_storage_can_be_duplicated_after_matching_safe_bind():
    js = ('const gl = canvas.getContext("webgl2"); const target = gl.ARRAY_BUFFER; '
          'const usage = gl.STATIC_DRAW; const size = 128; gl.bindBuffer(target, buffer); '
          'gl.bufferData(target, size, usage);')
    edit = next(e for e in mutator._edits(js) if e[0] == 'storage_duplicate')
    assert edit[3] == 'gl.bufferData(target, size, usage); gl.bufferData(target, size, usage);'


def test_texture_storage_can_be_duplicated_for_bounded_null_pixels_overload():
    js = ('const gl = canvas.getContext("webgl2"); const target = gl.TEXTURE_2D; '
          'const internalformat = gl.RGBA8; const format = gl.RGBA; const type = gl.UNSIGNED_BYTE; '
          'const level = 0; const width = 64; const height = 32; '
          'gl.bindTexture(target, texture); '
          'gl.texImage2D(target, level, internalformat, width, height, 0, format, type, null);')
    edit = next(e for e in mutator._edits(js) if e[0] == 'texture_storage_duplicate')
    assert edit[3] == ('gl.texImage2D(target, level, internalformat, width, height, 0, format, type, null); '
                       'gl.texImage2D(target, level, internalformat, width, height, 0, format, type, null);')


@pytest.mark.parametrize('call', [
    'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 4, 4, 0, gl.RGBA, gl.UNSIGNED_BYTE, pixels);',
    'gl.texImage2D(gl.TEXTURE_CUBE_MAP, 0, gl.RGBA8, 4, 4, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);',
    'gl.texImage2D(gl.TEXTURE_2D, -1, gl.RGBA8, 4, 4, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);',
    'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 4, 4, 1, gl.RGBA, gl.UNSIGNED_BYTE, null);',
    'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 0, 4, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);',
    'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 1025, 1024, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);',
    'gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 4, 4, 0, getFormat(), gl.UNSIGNED_BYTE, null);',
])
def test_texture_storage_duplication_rejects_unproven_or_out_of_bounds_calls(call):
    js = 'const gl = canvas.getContext("webgl2"); gl.bindTexture(gl.TEXTURE_2D, texture); ' + call
    assert not [e for e in mutator._edits(js) if e[0] == 'texture_storage_duplicate']


def test_texture_storage_duplication_requires_prior_same_block_binding():
    js = ('const gl = canvas.getContext("webgl2"); gl.bindTexture(gl.TEXTURE_2D, texture); '
          '{ gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 4, 4, 0, gl.RGBA, gl.UNSIGNED_BYTE, null); }')
    assert not [e for e in mutator._edits(js) if e[0] == 'texture_storage_duplicate']


@pytest.mark.parametrize('js', [
    'const gl = canvas.getContext("webgl2"); gl.bufferData(gl.ARRAY_BUFFER, 32, gl.STATIC_DRAW);',
    'const gl = canvas.getContext("webgl2"); gl.bindBuffer(gl.ARRAY_BUFFER, buffer); if (ok) gl.bufferData(gl.ARRAY_BUFFER, 32, gl.STATIC_DRAW);',
    'const gl = canvas.getContext("webgl2"); gl.bindBuffer(gl.ARRAY_BUFFER, buffer); gl.bufferData(gl.ARRAY_BUFFER, size(), gl.STATIC_DRAW);',
    'const gl = canvas.getContext("webgl2"); gl.bindBuffer(gl.ARRAY_BUFFER, buffer); gl.bufferData(gl.ARRAY_BUFFER, 32, usage());',
    'const gl = canvas.getContext("webgl2"); gl.bindBuffer(gl.ARRAY_BUFFER, buffer); gl.bufferData(gl.ARRAY_BUFFER, 16777217, gl.STATIC_DRAW);',
])
def test_buffer_storage_duplication_rejects_unsafe_or_unmatched_calls(js):
    assert not [e for e in mutator._edits(js) if e[0] == 'storage_duplicate']


def test_buffer_storage_only_grows_for_later_subdata_safety():
    js = 'const gl = canvas.getContext("webgl2"); const size = 9000000; gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, size, gl.STATIC_DRAW); gl.bufferSubData(gl.ARRAY_BUFFER, 8999999, new Uint8Array(1));'
    edits = [e for e in mutator._edits(js) if e[0] == 'resource_storage']
    assert {e[3] for e in edits} == {'9000192', '16777216'}
    assert all(9000000 < int(e[3]) <= 16 * 1024 * 1024 for e in edits)


def test_positive_draw_counts_can_shrink_to_zero_or_smaller():
    js = 'const gl = canvas.getContext("webgl2"); const count = 9; gl.drawArrays(gl.TRIANGLES, 0, count);'
    call_count = js.rindex('count')
    edits = [e for e in mutator._edits(js) if e[0] == 'bounded_parameter']
    assert {e[3] for e in edits} == {'0', '4', '8'}
    assert all(e[1:3] == (call_count, call_count + len('count')) for e in edits)


def test_viewport_and_scissor_dimensions_only_shrink_positively():
    js = ('const gl = canvas.getContext("webgl2"); const width = 512; '
          'gl.viewport(0, 0, width, 256); gl.scissor(0, 0, 128, 64);')
    edits = [e for e in mutator._edits(js) if e[0] == 'viewport_dimension']
    assert {e[3] for e in edits} == {'256', '128', '64', '32'}
    assert all(int(e[3]) > 0 for e in edits)


def test_operator_families_are_sampled_evenly_despite_site_counts():
    binds = ' '.join('gl.bindBuffer(gl.ARRAY_BUFFER, buffer);' for _ in range(30))
    source = f'<script>const gl = canvas.getContext("webgl2"); let buffer; {binds} gl.drawArrays(gl.TRIANGLES, 0, 3);</script>'.encode()
    outcomes = [mutator.mutate_bytes(source, __import__('random').Random(seed))[1][0]['operator']
                for seed in range(100)]
    state_count = outcomes.count('state_transition')
    assert 15 <= state_count <= 75


def test_state_edit_temporarily_unbinds_created_resource_and_restores_it():
    js = 'const gl = canvas.getContext("webgl2"); const buffer = gl.createBuffer(); if (!buffer) throw new Error("buffer"); gl.bindBuffer(gl.ARRAY_BUFFER, buffer);'
    edit = next(e for e in mutator._edits(js) if e[0] == 'state_transition')
    assert edit[3] == 'gl.bindBuffer(gl.ARRAY_BUFFER, null); gl.bindBuffer(gl.ARRAY_BUFFER, buffer);'
    output, _ = mutator.mutate_bytes(f'<script>{js}</script>'.encode(), __import__('random').Random(0))
    assert b'gl.bindBuffer(gl.ARRAY_BUFFER, null); gl.bindBuffer(gl.ARRAY_BUFFER, buffer);' in output


def test_state_operator_matches_texture_resources_too():
    js = 'const gl = canvas.getContext("webgl2"); const textureTarget = gl.TEXTURE_2D; let tex; gl.bindTexture(textureTarget, tex);'
    edit = next(e for e in mutator._edits(js) if e[0] == 'state_transition')
    assert 'gl.bindTexture(textureTarget, null); gl.bindTexture(textureTarget, tex);' == edit[3]


def test_state_operator_needs_no_resource_null_guard():
    js = 'const gl = canvas.getContext("webgl2"); let buffer; gl.bindBuffer(gl.ARRAY_BUFFER, buffer);'
    assert any(e[0] == 'state_transition' for e in mutator._edits(js))


def test_state_operator_skips_null_binding_and_program_switch():
    js = ('const gl = canvas.getContext("webgl2"); const program = gl.createProgram(); '
          'gl.bindBuffer(gl.ARRAY_BUFFER, null); gl.useProgram(program);')
    edits = [e for e in mutator._edits(js) if e[0] == 'state_transition']
    assert len(edits) == 1 and edits[0][3] == 'gl.useProgram(null); gl.useProgram(program);'


def test_state_operator_rejects_conditional_binding_and_mutable_enum_alias():
    js = 'const gl = canvas.getContext("webgl2"); let target = gl.ARRAY_BUFFER; target = gl.ELEMENT_ARRAY_BUFFER; if (ok) gl.bindBuffer(target, buffer);'
    assert not any(e[0] == 'state_transition' for e in mutator._edits(js))


def test_numeric_bounds_require_immutable_non_reassigned_const():
    mutable = 'const gl = canvas.getContext("webgl2"); let count = 9; count = 3; gl.drawArrays(gl.TRIANGLES, count, count);'
    assert not [e for e in mutator._edits(mutable) if e[0] == 'bounded_parameter']
    immutable = 'const gl = canvas.getContext("webgl2"); const count = 9; gl.drawArrays(gl.TRIANGLES, 0, count);'
    assert any(e[0] == 'bounded_parameter' for e in mutator._edits(immutable))
    nested = 'const gl = canvas.getContext("webgl2"); const count = 9; try { const count = 0; gl.drawArrays(gl.TRIANGLES, 0, count); } catch (e) {}'
    assert not [e for e in mutator._edits(nested) if e[0] == 'bounded_parameter']


@pytest.mark.parametrize(('view', 'size', 'offset', 'length'), [
    ('Uint8Array', 64, 8, 12),
    ('Uint16Array', 64, 6, 8),
])
def test_typed_array_view_offset_uses_proven_bounds(view, size, offset, length):
    js = (f'const backing = new ArrayBuffer({size}); '
          f'const view = new {view}(backing, {offset}, {length});')
    edits = [e for e in mutator._edits(js) if e[0] == 'typed_array_view_offset']
    start = js.index(f'backing, {offset}') + len('backing, ')
    assert edits == [('typed_array_view_offset', start, start + len(str(offset)), '0')]


@pytest.mark.parametrize('js', [
    'const backing = new Uint8Array(64).buffer; new Uint8Array(backing, 4, 8);',
    'const backing = new ArrayBuffer(64); const alias = backing; new Uint8Array(alias, 4, 8);',
    'const backing = new ArrayBuffer(64); backing = new ArrayBuffer(128); new Uint8Array(backing, 4, 8);',
    'const backing = new ArrayBuffer(64); new Uint16Array(backing, 3, 8);',
    'const backing = new ArrayBuffer(64); new Uint32Array(backing, 60, 2);',
    'const backing = new ArrayBuffer(64); new Uint8Array(backing, 4);',
    'function f(backing) { new Uint8Array(backing, 4, 8); }',
    'const backing = new ArrayBuffer(64); function f() { const backing = unknown; new Uint8Array(backing, 4, 8); }',
    'const backing = new ArrayBuffer(64); { const {backing} = {backing: null}; new Uint8Array(backing, 4, 8); }',
])
def test_typed_array_view_offset_rejects_unproven_or_invalid_views(js):
    assert not [e for e in mutator._edits(js) if e[0] == 'typed_array_view_offset']


def test_outer_constant_resolves_in_nested_try_block():
    js = 'const gl = canvas.getContext("webgl2"); const vertexCount = 9; try { gl.drawArrays(gl.TRIANGLES, 0, vertexCount); } catch (e) {}'
    assert any(e[0] == 'bounded_parameter' for e in mutator._edits(js))


def test_parameter_shadow_blocks_outer_constant():
    js = 'const gl = canvas.getContext("webgl2"); const vertexCount = 9; function draw(vertexCount) { gl.drawArrays(gl.TRIANGLES, 0, vertexCount); }'
    assert not [e for e in mutator._edits(js) if e[0] == 'bounded_parameter']


@pytest.mark.parametrize('html', [
    '<scripture>gl.drawArrays(gl.TRIANGLES, 0, 3);</scripture>',
    '<!-- <script>ignored</script> --><script>const gl = canvas.getContext("webgl2");</script>',
    '<script type=module>const gl = canvas.getContext("webgl2");</script>',
])
def test_ambiguous_or_nonclassic_script_rejected(html):
    with pytest.raises(ValueError):
        mutator._script(html.encode())


def test_closed_html_comment_before_script_is_preserved():
    html = b'<!-- note --><script>const gl = canvas.getContext("webgl2"); gl.drawArrays(gl.TRIANGLES, 0, 3);</script>'
    assert mutator._script(html)[0].start() > 0


def test_state_mutation_is_omitted_without_safe_restoration():
    js = 'const gl = canvas.getContext("webgl2"); gl.disable(gl.DEPTH_TEST); gl.drawArrays(gl.TRIANGLES, 0, 3);'
    assert not any(e[0] == 'state_transition' for e in mutator._edits(js))


def test_utf8_offsets_are_script_byte_offsets():
    data = '<script>const gl = canvas.getContext("webgl2"); const label = "雪"; gl.drawArrays(gl.TRIANGLES, 0, 3);</script>'.encode()
    changed, edit = mutator.mutate_bytes(data, __import__('random').Random(2))
    match, _ = mutator._script(data)
    js_start = match.start('body')
    original = data[js_start + edit[0]['start']:js_start + edit[0]['end']]
    assert original in (b'3', b'gl.TRIANGLES')
    assert original != edit[0]['replacement'].encode()
    assert changed.decode('utf-8')


def test_output_collision(tmp_path):
    seed = tmp_path / 'seed.html'
    seed.write_text('<script>const gl = canvas.getContext("webgl2"); gl.drawArrays(gl.TRIANGLES, 0, 3);</script>')
    dest = tmp_path / 'out'
    dest.mkdir()
    assert mutator.main([str(seed), '-o', str(dest), '-s', '1']) == 0
    with pytest.raises(FileExistsError):
        mutator.main([str(seed), '-o', str(dest), '-s', '1'])


def test_sidecar_contains_hashes_and_operator(tmp_path):
    seed = tmp_path / 'seed.html'
    seed.write_text('<script>const gl = canvas.getContext("webgl2"); gl.drawArrays(gl.TRIANGLES, 0, 3);</script>')
    dest = tmp_path / 'out'
    dest.mkdir()
    mutator.main([str(seed), '-o', str(dest), '-s', '4'])
    metadata = json.loads((dest / 'seed_0.mutation.json').read_text())
    assert metadata['source_sha256']
    assert metadata['output_sha256']
    assert isinstance(metadata['edits'][0]['operator'], str)


def test_validation_cli_sidecar_records_arm_and_expected_error(tmp_path):
    seed = tmp_path / 'seed.html'
    seed.write_bytes(validation_seed())
    dest = tmp_path / 'out'
    dest.mkdir()
    mutator.main([str(seed), '-o', str(dest), '--arm', 'validation', '--max-edits', '3'])
    output = (dest / 'seed_0.html').read_bytes()
    metadata = json.loads((dest / 'seed_0.mutation.json').read_text())
    assert metadata['arm'] == 'validation'
    assert metadata['expected_error'] == 'INVALID_VALUE'
    assert len(metadata['edits']) == 1
    assert mutator.replay(seed.read_bytes(), metadata) == output


def test_multi_seed_collision_preflight_writes_nothing(tmp_path):
    first = tmp_path / 'a' / 'seed.html'
    second = tmp_path / 'b' / 'seed.html'
    first.parent.mkdir()
    second.parent.mkdir()
    body = '<script>const gl = canvas.getContext("webgl2"); gl.drawArrays(gl.TRIANGLES, 0, 3);</script>'
    first.write_text(body)
    second.write_text(body)
    out = tmp_path / 'out'
    second_output = out / 'seed_1.html'
    second_output.parent.mkdir()
    second_output.with_suffix('.mutation.json').write_text('occupied')
    with pytest.raises(FileExistsError):
        mutator.main([str(first), str(second), '-o', str(out), '-s', '3'])
    assert not (out / 'seed_0.html').exists()




def test_multi_edit_selection_is_nonoverlapping_and_replays_deterministically():
    source = (b'<script>const gl = canvas.getContext("webgl2"); '
              b'gl.viewport(0, 0, 128, 64); gl.drawArrays(gl.TRIANGLES, 0, 9); gl.scissor(0, 0, 64, 32);</script>')
    first, edits = mutator.mutate_bytes(source, __import__('random').Random(12), max_edits=3)
    second, again = mutator.mutate_bytes(source, __import__('random').Random(12), max_edits=3)
    assert first == second and edits == again
    assert len(edits) == 3
    assert all(a['end'] <= b['start'] or b['end'] <= a['start']
               for i, a in enumerate(edits) for b in edits[i + 1:])
    assert mutator.replay(source, {'edits': edits}) == first


def test_multi_edit_does_not_mutate_same_statement_twice():
    source = b'<script>const gl = canvas.getContext("webgl2"); gl.viewport(0, 0, 128, 64);</script>'
    _, edits = mutator.mutate_bytes(source, __import__('random').Random(4), max_edits=3)
    assert len(edits) == 1


def test_max_edits_is_limited_to_one_through_three():
    source = b'<script>const gl = canvas.getContext("webgl2"); gl.drawArrays(gl.TRIANGLES, 0, 9);</script>'
    with pytest.raises(ValueError, match='between 1 and 3'):
        mutator.mutate_bytes(source, __import__('random').Random(1), max_edits=4)

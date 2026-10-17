import json
from pathlib import Path

from api_audit.site_coverage import analyze_sites


ROOT = Path(__file__).resolve().parents[3]


def surface():
    return json.loads((ROOT / "docs/webgl_api_surface.json").read_text())


def _call(records, method):
    return next(call for call in records if call["method"] == method)


def test_extension_alias_without_candidates_is_reported_with_no_direct_edits():
    body = """
const gl = canvas.getContext('webgl2');
const ext = gl.getExtension('WEBGL_multi_draw');
ext.multiDrawArraysWEBGL(gl.TRIANGLES, firsts, 0, counts, 0, 1);
"""
    records = analyze_sites(f"<script>{body}</script>", {}, surface())
    call = _call(records, "multiDrawArraysWEBGL")
    assert call["kind"] == "extension"
    assert call["extension"] == "WEBGL_multi_draw"
    assert len(call["args"]) == 6
    assert all(arg["status"] == "no_direct_edits" for arg in call["args"])


def test_extension_argument_can_have_direct_edit_span_when_candidate_targets_it():
    body = "const gl = canvas.getContext('webgl2'); const ext = gl.getExtension('WEBGL_multi_draw'); ext.multiDrawArraysWEBGL(gl.TRIANGLES, firsts, 0, counts, 0, 1);"
    encoded = body.encode("utf-8")
    start = encoded.index(b"counts")
    records = analyze_sites(f"<script>{body}</script>", {
        "array_boundary": [{"start": start, "end": start + len(b"counts"), "replacement": "otherCounts"}],
    }, surface())
    call = _call(records, "multiDrawArraysWEBGL")
    count_arg = call["args"][3]
    assert call["extension"] == "WEBGL_multi_draw"
    assert count_arg["status"] == "eligible"
    assert count_arg["direct_edit_families"] == ["array_boundary"]
    assert count_arg["eligible_edits"] == 1


def test_bufferdata_size_argument_counts_only_its_direct_edit():
    body = "\nconst gl = canvas.getContext('webgl2'); gl.bufferData(gl.ARRAY_BUFFER, 4096, gl.STATIC_DRAW);\n"
    encoded = body.encode("utf-8")
    start = encoded.index(b"4096")
    records = analyze_sites(f"<script>{body}</script>", {
        "buffer_storage_size": [{"start": start, "end": start + 4,
                                 "replacement": "2048"}],
    }, surface())
    call = _call(records, "bufferData")
    size_arg = call["args"][1]
    assert size_arg["status"] == "eligible"
    assert size_arg["direct_edit_families"] == ["buffer_storage_size"]
    assert size_arg["eligible_edits"] == 1
    assert all(arg["status"] == "no_direct_edits"
               for index, arg in enumerate(call["args"]) if index != 1)


def test_statement_wrapper_is_reported_separately_from_direct_argument_edits():
    body = "const gl = canvas.getContext('webgl2'); gl.bufferData(gl.ARRAY_BUFFER, 4096, gl.STATIC_DRAW);"
    encoded = body.encode("utf-8")
    start = encoded.index(b"gl.bufferData")
    end = encoded.index(b";", start) + 1
    records = analyze_sites(f"<script>{body}</script>", {
        "statement_wrapper": [{"start": start, "end": end,
                               "replacement": "if (true) { " + body[start:end] + " }"}],
    }, surface())
    call = _call(records, "bufferData")
    assert all(arg["status"] == "no_direct_edits" for arg in call["args"])
    assert all(arg["eligible_edits"] == 0 for arg in call["args"])
    assert all(arg["wrapper_only_families"] == ["statement_wrapper"] for arg in call["args"])


def test_call_and_argument_offsets_are_utf8_bytes_in_raw_script_body():
    body = '\nconst gl = canvas.getContext("webgl2"); const note = "🦊"; gl.drawArrays(gl.TRIANGLES, 0, 3);\n'
    records = analyze_sites(f"<script>{body}</script>", {}, surface())
    call = _call(records, "drawArrays")
    source = body.encode("utf-8")
    assert call["start"] == source.index(b"gl.drawArrays")
    assert call["args"][2]["start"] == source.index(b"3);")


def test_chained_extension_receiver_is_resolved():
    body = "const gl = canvas.getContext('webgl2'); gl.getExtension('WEBGL_multi_draw').multiDrawArraysWEBGL(gl.TRIANGLES, firsts, 0, counts, 0, 1);"
    records = analyze_sites(f"<script>{body}</script>", {}, surface())
    call = _call(records, "multiDrawArraysWEBGL")
    assert call["kind"] == "extension"
    assert call["extension"] == "WEBGL_multi_draw"

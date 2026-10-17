import json
import shutil
import subprocess
from pathlib import Path

import pytest


TRACE = Path(__file__).parents[1] / 'api_audit' / 'webgl_trace.js'


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js is needed for the isolated tracer test')
def test_trace_preserves_calls_and_excludes_profiler_observations():
    source = TRACE.read_text().replace('__WEBGL_EVENT_CAP__', '200').replace('__WEBGL_OUTCOME_CAP__', '2048')
    harness = r'''
globalThis.window = globalThis;
class WebGLUniformLocation {}
class WebGLBuffer {}
class WebGLRenderingContext {
  constructor() {
    Object.assign(this, {VERSION: 1, RENDERER: 2, VENDOR: 3, NO_ERROR: 0,
      ARRAY_BUFFER: 4, LINK_STATUS: 5, ACTIVE_ATTRIBUTES: 6, ACTIVE_UNIFORMS: 7,
      SAMPLER_2D: 8, FLOAT_MAT4: 9, FLOAT_VEC4: 10, SAMPLER_2D_SHADOW: 11,
      ARRAY_BUFFER_BINDING: null, UNMASKED_RENDERER_WEBGL: 12, UNMASKED_VENDOR_WEBGL: 13});
    this.errors = [1280, 0];
    this.locations = new Map();
    this.buffer = new WebGLBuffer();
  }
  getParameter(p) { return p === this.VERSION ? 'WebGL 2.0' : p === this.UNMASKED_RENDERER_WEBGL ? 'test-renderer' : p === this.UNMASKED_VENDOR_WEBGL ? 'test-vendor' : 'masked'; }
  getSupportedExtensions() { return ['WEBGL_multi_draw']; }
  getExtension(name) { return name === 'WEBGL_multi_draw' ? this.ext : name === 'WEBGL_debug_renderer_info' ? {UNMASKED_RENDERER_WEBGL: this.UNMASKED_RENDERER_WEBGL, UNMASKED_VENDOR_WEBGL: this.UNMASKED_VENDOR_WEBGL} : null; }
  createBuffer() { return this.buffer; }
  bindBuffer() { return undefined; }
  bufferData() { return undefined; }
  drawArrays() { return undefined; }
  uniform1iv() { return undefined; }
  getError() { return this.errors.shift() ?? 0; }
  linkProgram() { return undefined; }
  getProgramParameter(p, key) { return key === this.LINK_STATUS ? true : key === this.ACTIVE_ATTRIBUTES ? 2 : p.singleSampler ? 1 : 1; }
  getActiveAttrib(p, i) { if (p.unknownReflection && i === 0) return {name: 'opaque', type: 99999, size: 1}; return i === 0 ? {name: 'transform', type: this.FLOAT_MAT4, size: 1} : {name: 'weights[0]', type: this.FLOAT_VEC4, size: 2}; }
  getAttribLocation(_p, name) { return name === 'transform' ? 3 : 8; }
  getActiveUniform(p) { return p.singleSampler ? {name: 'single[0]', type: this.SAMPLER_2D_SHADOW, size: 1} : {name: 'shadow[0]', type: this.SAMPLER_2D_SHADOW, size: 2}; }
  getUniformLocation(_p, name) { if (!this.locations.has(name)) this.locations.set(name, new WebGLUniformLocation()); return this.locations.get(name); }
}
class HTMLCanvasElement { getContext() { return this.gl; } }
globalThis.HTMLCanvasElement = HTMLCanvasElement;
const canvas = new HTMLCanvasElement();
canvas.gl = new WebGLRenderingContext();
canvas.gl.ext = {multiDrawArraysWEBGL() { return 17; }, multiDrawArraysInstancedWEBGL() { return 19; }};
''' + source + r'''
const gl = canvas.getContext('webgl2');
const buffer = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
gl.bufferData(gl.ARRAY_BUFFER, new Uint8Array([7, 8, 9]), 1);
gl.drawArrays(4, 0, 3);
const program = {};
gl.linkProgram(program);
const location = gl.getUniformLocation(program, 'shadow');
gl.uniform1iv(location, new Int32Array([1, 2]));
const singleSamplerProgram = {singleSampler: true};
gl.linkProgram(singleSamplerProgram);
gl.getUniformLocation(singleSamplerProgram, 'single');
gl.linkProgram({unknownReflection: true});
const ext = gl.getExtension('WEBGL_multi_draw');
const returned = ext.multiDrawArraysWEBGL(4, new Int32Array([0, 1]), 0, new Int32Array([0, 2]), 0, 2);
const instancedReturned = ext.multiDrawArraysInstancedWEBGL(4, new Int32Array([90, 91, 0, 1]), 2,
  new Int32Array([9, 0, 2, 9]), 1, new Int32Array([8, 1, 3, 8]), 1, 2);
const seedError = gl.getError();
const profile = window.__webglProfiler.finish();
process.stdout.write(JSON.stringify({profile, returned, instancedReturned, seedError,
  locationIsObject: location instanceof WebGLUniformLocation}));
'''
    completed = subprocess.run(['node', '-e', harness], capture_output=True, text=True, check=True)
    data = json.loads(completed.stdout)
    profile = data['profile']
    assert data['returned'] == 17
    assert data['seedError'] == 1280
    assert profile['contexts'] == [{'id': 'c1', 'version': 2, 'extensions': ['WEBGL_multi_draw'],
                                    'renderer': 'test-renderer', 'vendor': 'test-vendor', 'renderer_verified': True}]
    assert not any(event['method'] in {'getParameter', 'getSupportedExtensions'} for event in profile['events'])
    upload = next(event for event in profile['events'] if event['method'] == 'bufferData')
    assert upload['args'][1] == {'kind': 'view', 'type': 'Uint8Array', 'byte_length': 3,
                                 'length': 3, 'truncated': False}
    reflection = next(event['reflection'] for event in profile['events'] if event['method'] == 'linkProgram')
    assert reflection['status'] == 'linked'
    assert reflection['complete'] is True
    assert reflection['attributes'] == [3, 4, 5, 6, 8, 9]
    assert reflection['samplers'][0]['type'] == 11
    assert [location['kind'] for location in reflection['samplers'][0]['locations']] == ['location', 'location']
    reflected_location = reflection['samplers'][0]['locations'][0]
    seed_location = next(event['result'] for event in profile['events'] if event['method'] == 'getUniformLocation')
    assert reflected_location['program'] == seed_location['program']
    assert reflected_location['generation'] == seed_location['generation'] == 1
    assert reflected_location['name'] == seed_location['name'] == 'shadow[0]'
    single_location = [event['result'] for event in profile['events'] if event['method'] == 'getUniformLocation'][-1]
    assert single_location['name'] == 'single[0]'
    unresolved = [event['reflection'] for event in profile['events']
                  if event['method'] == 'linkProgram' and event['reflection']['complete'] is False]
    assert unresolved[0]['status'] == 'linked'
    assert unresolved[0]['unresolved'] == ['attribute_opaque_type_unknown']
    uniform = next(event for event in profile['events'] if event['method'] == 'uniform1iv')
    assert uniform['args'][1]['values'] == [1, 2]
    multi = next(event for event in profile['events'] if event['method'] == 'multiDrawArraysWEBGL')
    assert multi['extension'] == 'WEBGL_multi_draw'
    assert multi['args'][1]['values'] == [0, 1]
    assert multi['args'][3]['values'] == [0, 2]
    instanced = next(event for event in profile['events'] if event['method'] == 'multiDrawArraysInstancedWEBGL')
    assert instanced['args'][1]['values'] == [0, 1]
    assert instanced['args'][3]['values'] == [0, 2]
    assert instanced['args'][5]['values'] == [1, 3]
    assert data['instancedReturned'] == 19
    assert {'code': 'seed_webgl_error', 'context': 'c1', 'error': 1280, 'method': 'getError'} in profile['outcomes']
    assert sum(event['method'] == 'getError' for event in profile['events']) == 1


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js is needed for the isolated tracer test')
def test_event_cap_is_reported():
    source = TRACE.read_text().replace('__WEBGL_EVENT_CAP__', '1').replace('__WEBGL_OUTCOME_CAP__', '2048')
    harness = r'''
globalThis.window = globalThis;
class WebGLUniformLocation {}
class WebGLRenderingContext {
  constructor() { this.VERSION=1; this.RENDERER=2; this.VENDOR=3; this.NO_ERROR=0; }
  getParameter(p) { return p === this.VERSION ? 'WebGL 1.0' : 'renderer'; }
  getSupportedExtensions() { return []; }
  getExtension() { return null; }
  drawArrays() { return 5; }
  getError() { return 0; }
}
class HTMLCanvasElement { getContext() { return this.gl; } }
globalThis.HTMLCanvasElement = HTMLCanvasElement;
const canvas = new HTMLCanvasElement(); canvas.gl = new WebGLRenderingContext();
''' + source + r'''
const gl = canvas.getContext('webgl'); gl.drawArrays(4, 0, 1); gl.drawArrays(4, 0, 1);
process.stdout.write(JSON.stringify(window.__webglProfiler.finish()));
'''
    completed = subprocess.run(['node', '-e', harness], capture_output=True, text=True, check=True)
    profile = json.loads(completed.stdout)
    assert len(profile['events']) == 1
    assert profile['truncated'] is True
    assert {'code': 'event_buffer_full'} in profile['outcomes']


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js is needed for the isolated tracer test')
def test_outcome_cap_reports_overflow_for_repeated_optional_extensions():
    source = TRACE.read_text().replace('__WEBGL_EVENT_CAP__', '1').replace('__WEBGL_OUTCOME_CAP__', '3')
    harness = r'''
globalThis.window = globalThis;
class WebGLUniformLocation {}
class WebGLRenderingContext {
  constructor() { this.VERSION=1; this.RENDERER=2; this.VENDOR=3; this.NO_ERROR=0; }
  getParameter(p) { return p === this.VERSION ? 'WebGL 1.0' : 'renderer'; }
  getSupportedExtensions() { return []; }
  getExtension() { return null; }
  getError() { return 0; }
}
class HTMLCanvasElement { getContext() { return this.gl; } }
globalThis.HTMLCanvasElement = HTMLCanvasElement;
const canvas = new HTMLCanvasElement(); canvas.gl = new WebGLRenderingContext();
''' + source + r'''
const gl = canvas.getContext('webgl');
for (let i = 0; i < 20; i++) gl.getExtension(`MISSING_${i}`);
process.stdout.write(JSON.stringify(window.__webglProfiler.finish()));
'''
    completed = subprocess.run(['node', '-e', harness], capture_output=True, text=True, check=True)
    profile = json.loads(completed.stdout)
    assert profile['outcome_cap'] == 3
    assert len(profile['outcomes']) <= profile['outcome_cap']
    assert profile['outcomes'][-1] == {'code': 'outcome_buffer_full'}


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js is needed for the isolated tracer test')
def test_firefox_renderer_observation_does_not_request_deprecated_extension():
    source = TRACE.read_text().replace('__WEBGL_EVENT_CAP__', '10').replace('__WEBGL_OUTCOME_CAP__', '10')
    harness = r'''
globalThis.window = globalThis;
Object.defineProperty(globalThis, 'navigator', {value: {userAgent: 'Mozilla/5.0 Firefox/145.0'}, configurable: true});
class WebGLRenderingContext {
  constructor() { this.VERSION=1; this.RENDERER=2; this.VENDOR=3; this.debugRequests=0; }
  getParameter(p) { return p === this.VERSION ? 'WebGL 1.0' : p === this.RENDERER ? 'masked-renderer' : 'masked-vendor'; }
  getSupportedExtensions() { return []; }
  getExtension(name) { if (name === 'WEBGL_debug_renderer_info') this.debugRequests++; return null; }
}
class HTMLCanvasElement { getContext() { return this.gl; } }
globalThis.HTMLCanvasElement = HTMLCanvasElement;
const canvas = new HTMLCanvasElement(); canvas.gl = new WebGLRenderingContext();
''' + source + r'''
canvas.getContext('webgl');
process.stdout.write(JSON.stringify({profile: window.__webglProfiler.finish(), requests: canvas.gl.debugRequests}));
'''
    completed = subprocess.run(['node', '-e', harness], capture_output=True, text=True, check=True)
    data = json.loads(completed.stdout)
    assert data['requests'] == 0
    context = data['profile']['contexts'][0]
    assert context['renderer'] == 'masked-renderer'
    assert context['renderer_verified'] is False

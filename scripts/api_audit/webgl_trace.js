(() => {
    const cap = __WEBGL_EVENT_CAP__;
    const firefox = typeof navigator !== 'undefined' && /Firefox\//.test(navigator.userAgent || '');
    const outcomeCap = Math.max(2, __WEBGL_OUTCOME_CAP__);
    const outcomeDetailLimit = Math.max(0, outcomeCap - 3);
    const contexts = [];
    const states = [];
    const events = [];
    const outcomes = [];
    const objectIds = new WeakMap();
    const locationInfo = new WeakMap();
    const contextStates = new WeakMap();
    let nextObjectId = 1;
    let recording = true;
    let suppressed = 0;
    let truncated = false;
    let outcomeOverflow = false;

    const addOutcome = outcome => {
        if (outcomes.length < outcomeDetailLimit) outcomes.push(outcome);
        else if (!outcomeOverflow) {
            outcomes.push({code: 'outcome_buffer_full'});
            outcomeOverflow = true;
        }
    };

    const idFor = (value, kind) => {
        if (!value || (typeof value !== 'object' && typeof value !== 'function')) return null;
        let id = objectIds.get(value);
        if (!id) {
            id = `o${nextObjectId++}`;
            objectIds.set(value, id);
        }
        const name = kind || value.constructor?.name || 'Object';
        const kinds = {WebGLBuffer: 'buffer', WebGLVertexArrayObject: 'vao', WebGLVertexArrayObjectOES: 'vao', WebGLProgram: 'program',
            WebGLTexture: 'texture', WebGLFramebuffer: 'framebuffer', WebGLRenderbuffer: 'renderbuffer',
            WebGLSampler: 'sampler', WebGLShader: 'shader', WebGLUniformLocation: 'location'};
        return {id, kind: kinds[name] || name};
    };

    const typed = (value, context, selectedValues = null) => {
        if (value === null) return null;
        if (value === undefined) return {type: 'undefined'};
        if (typeof value === 'number' || typeof value === 'string' || typeof value === 'boolean') return value;
        if (typeof value === 'bigint') return {type: 'BigInt', value: String(value)};
        if (Array.isArray(value) && selectedValues) {
            return {kind: 'array', type: 'Array', length: value.length, truncated: selectedValues.truncated,
                values: selectedValues.values};
        }
        if (ArrayBuffer.isView(value)) {
            const values = selectedValues;
            const item = {kind: 'view', type: value.constructor.name, byte_length: value.byteLength,
                length: value.length ?? null, truncated: Boolean(values?.truncated)};
            if (values) item.values = values.values;
            return item;
        }
        if (value instanceof ArrayBuffer) return {type: 'ArrayBuffer', byte_length: value.byteLength};
        if (value instanceof WebGLUniformLocation) {
            const meta = locationInfo.get(value);
            return {...idFor(value, 'WebGLUniformLocation'), program: meta?.program || null,
                generation: meta?.generation ?? null, name: meta?.name ?? null};
        }
        if (value instanceof WebGLRenderingContext || (typeof WebGL2RenderingContext !== 'undefined' && value instanceof WebGL2RenderingContext)) {
            return idFor(value, 'WebGLRenderingContext');
        }
        return idFor(value);
    };

    const makeEvent = (state, method, args, result, reflection, extension) => {
        if (!recording || suppressed) return;
        if (events.length >= cap) { truncated = true; return; }
        const multi = method.startsWith('multiDraw');
        const elements = method.includes('Elements');
        const instanced = method.includes('Instanced');
        const arrayIndex = elements ? (instanced ? [1, 4, 6] : [1, 4]) : (instanced ? [1, 3, 5] : [1, 3]);
        const offsetIndex = elements ? (instanced ? [2, 5, 7] : [2, 5]) : (instanced ? [2, 4, 6] : [2, 4]);
        const drawCountIndex = elements ? (instanced ? 8 : 6) : (instanced ? 7 : 5);
        const drawCount = multi ? Math.max(0, Number(args[drawCountIndex]) || 0) : 0;
        let multiValuesTruncated = false;
        const selected = (arg, index) => {
            if (method === 'uniform1iv' && index === 1 && (ArrayBuffer.isView(arg) || Array.isArray(arg))) {
                const end = Math.min(arg.length, 64);
                return {values: Array.isArray(arg) ? arg.slice(0, end) : Array.from(arg.subarray(0, end)),
                    truncated: end < arg.length};
            }
            if (!multi || !arrayIndex.includes(index) || (!ArrayBuffer.isView(arg) && !Array.isArray(arg))) return null;
            const offset = Math.max(0, Number(args[offsetIndex[arrayIndex.indexOf(index)]]) || 0);
            const end = Math.min(arg.length, offset + drawCount, offset + 64);
            const truncated = end < offset + drawCount;
            multiValuesTruncated ||= truncated;
            return {values: Array.isArray(arg) ? arg.slice(offset, end) : Array.from(arg.subarray(offset, end)), truncated};
        };
        const convertedArgs = Array.from(args, (arg, index) => typed(arg, state, selected(arg, index)));
        if (multiValuesTruncated) addOutcome({code: 'multi_draw_values_truncated', context: state.id, method});
        const event = {seq: events.length, context: state.id, method,
            extension: extension || null, args: convertedArgs};
        if (result !== undefined) event.result = typed(result, state);
        if (reflection) event.reflection = reflection;
        events.push(event);
    };

    const reflectProgram = (gl, state, program) => {
        suppressed++;
        let generation = state.generations.get(program) || 0;
        try {
            generation++;
            state.generations.set(program, generation);
            if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
                state.reflections.delete(program);
                return {generation, status: 'failed', complete: false, unresolved: ['link_failed'], attributes: [], samplers: []};
            }
            const attributes = [];
            const samplers = [];
            const unresolved = [];
            const matrixColumns = new Map([
                [gl.FLOAT_MAT2, 2], [gl.FLOAT_MAT3, 3], [gl.FLOAT_MAT4, 4],
                [gl.FLOAT_MAT2x3, 2], [gl.FLOAT_MAT2x4, 2], [gl.FLOAT_MAT3x2, 3],
                [gl.FLOAT_MAT3x4, 3], [gl.FLOAT_MAT4x2, 4], [gl.FLOAT_MAT4x3, 4],
            ]);
            const singleSlotTypes = new Set([
                gl.FLOAT, gl.FLOAT_VEC2, gl.FLOAT_VEC3, gl.FLOAT_VEC4,
                gl.INT, gl.INT_VEC2, gl.INT_VEC3, gl.INT_VEC4,
                gl.UNSIGNED_INT, gl.UNSIGNED_INT_VEC2, gl.UNSIGNED_INT_VEC3, gl.UNSIGNED_INT_VEC4,
            ]);
            const attributeCount = gl.getProgramParameter(program, gl.ACTIVE_ATTRIBUTES) || 0;
            if (attributeCount > 256) unresolved.push('active_attribute_limit');
            for (let i = 0; i < Math.min(attributeCount, 256); i++) {
                const active = gl.getActiveAttrib(program, i);
                if (!active) { unresolved.push(`attribute_${i}_unknown`); continue; }
                if (active.type == null || !Number.isInteger(active.size) || active.size < 1) {
                    unresolved.push(`attribute_${active.name}_type_or_size_unknown`);
                    continue;
                }
                const columns = matrixColumns.get(active.type);
                if (columns === undefined && !singleSlotTypes.has(active.type)) {
                    unresolved.push(`attribute_${active.name}_type_unknown`);
                    continue;
                }
                const slotCount = (columns || 1) * active.size;
                if (slotCount > 256) { unresolved.push(`attribute_${active.name}_slot_limit`); continue; }
                const location = gl.getAttribLocation(program, active.name);
                if (location < 0) continue;
                for (let slot = location; slot < location + slotCount; slot++) attributes.push(slot);
            }
            const uniformCount = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS) || 0;
            if (uniformCount > 256) unresolved.push('active_uniform_limit');
            for (let i = 0; i < Math.min(uniformCount, 256); i++) {
                const active = gl.getActiveUniform(program, i);
                if (!active) { unresolved.push(`uniform_${i}_unknown`); continue; }
                const typeName = active.type;
                if (![gl.SAMPLER_2D, gl.SAMPLER_CUBE, gl.SAMPLER_3D, gl.SAMPLER_2D_ARRAY,
                    gl.SAMPLER_2D_SHADOW, gl.SAMPLER_CUBE_SHADOW, gl.SAMPLER_2D_ARRAY_SHADOW,
                    gl.INT_SAMPLER_2D, gl.INT_SAMPLER_3D, gl.INT_SAMPLER_CUBE, gl.INT_SAMPLER_2D_ARRAY,
                    gl.UNSIGNED_INT_SAMPLER_2D, gl.UNSIGNED_INT_SAMPLER_3D, gl.UNSIGNED_INT_SAMPLER_CUBE,
                    gl.UNSIGNED_INT_SAMPLER_2D_ARRAY, 0x8D66].includes(typeName)) continue;
                const size = Number(active.size);
                if (!Number.isInteger(size) || size < 1 || size > 64) {
                    unresolved.push(`sampler_${active.name}_array_limit`);
                    samplers.push({name: active.name, type: typeName, size: active.size, locations: [], complete: false});
                    continue;
                }
                const locations = [];
                const baseName = active.name.endsWith('[0]') ? active.name.slice(0, -3) : active.name;
                for (let element = 0; element < size; element++) {
                    const uniformName = size === 1 ? active.name : `${baseName}[${element}]`;
                    const location = gl.getUniformLocation(program, uniformName);
                    if (!location) { unresolved.push(`sampler_${uniformName}_location_unknown`); continue; }
                    locationInfo.set(location, {program: idFor(program, 'WebGLProgram').id, generation, name: uniformName});
                    locations.push({...idFor(location, 'WebGLUniformLocation'), program: idFor(program, 'WebGLProgram').id,
                        generation, name: uniformName});
                }
                samplers.push({name: active.name, type: typeName, size, locations, complete: locations.length === size});
            }
            const reflection = {generation, status: 'linked', complete: unresolved.length === 0 && samplers.every(item => item.complete),
                unresolved, attributes, samplers};
            state.reflections.set(program, reflection);
            return reflection;
        } catch (_) {
            state.reflections.delete(program);
            return {generation, status: 'unknown', complete: false, unresolved: ['reflection_exception'], attributes: [], samplers: []};
        } finally { suppressed--; }
    };

    const wrapMethod = (target, method, state, original, extension) => {
        if (typeof original !== 'function' || original.__webglProfileWrapped) return;
        const wrapped = function(...args) {
            let result;
            try {
                result = Reflect.apply(original, this, args);
            } catch (error) {
                const event = {seq: events.length, context: state.id, method, extension: extension || null,
                    args: Array.from(args, arg => typed(arg, state)), threw: {name: error?.name || 'Error', message: String(error?.message || error)}};
                if (recording && !suppressed && events.length < cap) events.push(event);
                else if (recording && !suppressed) truncated = true;
                throw error;
            }
            if (recording && !suppressed) {
                let reflection = null;
                if (method === 'getExtension' && result) {
                    instrument(result, state, String(args[0]));
                } else if (method === 'getExtension' && !result) {
                    addOutcome({code: 'unavailable_extension', context: state.id, extension: String(args[0])});
                } else if (method === 'getUniformLocation' && result) {
                    const program = args[0];
                    let name = String(args[1]);
                    const reflection = state.reflections.get(program);
                    const array = reflection?.samplers.find(item => item.name.endsWith('[0]') && item.name.replace(/\[0\]$/, '') === name);
                    if (array) name = `${array.name.replace(/\[0\]$/, '')}[0]`;
                    locationInfo.set(result, {program: idFor(program, 'WebGLProgram').id,
                        generation: state.generations.get(program) || 0, name});
                } else if (method === 'linkProgram') {
                    reflection = reflectProgram(this, state, args[0]);
                } else if (method === 'getError' && result !== this.NO_ERROR) {
                    addOutcome({code: 'seed_webgl_error', context: state.id, error: result, method: 'getError'});
                } else if (/draw/i.test(method)) {
                const elements = method.includes('Elements');
                const instanced = method.includes('Instanced');
                const positive = method.startsWith('multiDraw')
                    ? (() => {
                        const counts = args[elements ? 1 : 3];
                        const countOffset = Number(args[elements ? 2 : 4]) || 0;
                        const instanceCounts = instanced ? args[elements ? 6 : 5] : null;
                        const instanceOffset = instanced ? Number(args[elements ? 7 : 6]) || 0 : 0;
                        const drawCount = Number(args[elements ? (instanced ? 8 : 6) : (instanced ? 7 : 5)]) || 0;
                        for (let i = 0; i < Math.min(drawCount, 64); i++) {
                            if (Number(counts?.[countOffset + i]) > 0 &&
                                (!instanced || Number(instanceCounts?.[instanceOffset + i]) > 0)) return true;
                        }
                        return false;
                    })()
                    : (method.includes('Instanced') ? Number(args[elements ? 4 : 3]) > 0 && Number(args[elements ? 1 : 2]) > 0
                        : Number(args[method.includes('Range') ? 3 : (elements ? 1 : 2)]) > 0);
                    if (positive) state.positiveDraw = true;
                }
                makeEvent(state, method, args, result, reflection, extension);
            }
            return result;
        };
        Object.defineProperty(wrapped, '__webglProfileWrapped', {value: true});
        try { Object.defineProperty(target, method, {configurable: true, writable: true, value: wrapped}); } catch (_) {}
    };

    function instrument(target, state, extension = null) {
        if (!target || state.instrumented.has(target)) return;
        state.instrumented.add(target);
        const methods = new Set();
        for (let proto = target; proto && proto !== Object.prototype; proto = Object.getPrototypeOf(proto)) {
            for (const name of Object.getOwnPropertyNames(proto)) {
                if (name !== 'constructor' && typeof target[name] === 'function') methods.add(name);
            }
        }
        for (const name of methods) wrapMethod(target, name, state, target[name], extension);
    }

    const observeContext = gl => {
        if (!recording || contextStates.has(gl)) return;
        const id = `c${contexts.length + 1}`;
        const state = {id, gl, extension: null, extensions: new Set(), instrumented: new WeakSet(),
            generations: new WeakMap(), reflections: new WeakMap(), positiveDraw: false};
        contextStates.set(gl, state);
        states.push(state);
        suppressed++;
        try {
            const versionValue = gl.getParameter(gl.VERSION) || '';
            const version = /WebGL\s*2/i.test(versionValue) ? 2 : 1;
            const extensions = gl.getSupportedExtensions() || [];
            const debug = firefox ? null : gl.getExtension('WEBGL_debug_renderer_info');
            const renderer = gl.getParameter(debug ? debug.UNMASKED_RENDERER_WEBGL : gl.RENDERER);
            const vendor = gl.getParameter(debug ? debug.UNMASKED_VENDOR_WEBGL : gl.VENDOR);
            contexts.push({id, version, extensions, renderer: String(renderer || ''), vendor: String(vendor || ''),
                renderer_verified: Boolean(debug)});
        } catch (_) {
            contexts.push({id, version: 1, extensions: [], renderer: null, vendor: null, renderer_verified: false});
        } finally { suppressed--; }
        instrument(gl, state);
    };

    for (const ctorName of ['HTMLCanvasElement', 'OffscreenCanvas']) {
        const ctor = globalThis[ctorName];
        if (!ctor?.prototype) continue;
        const original = ctor.prototype.getContext;
        if (typeof original !== 'function') continue;
        Object.defineProperty(ctor.prototype, 'getContext', {configurable: true, writable: true,
            value: function(type, ...args) {
                const result = Reflect.apply(original, this, [type, ...args]);
                if (result && /^(webgl|experimental-webgl|webgl2)$/i.test(String(type))) observeContext(result);
                return result;
            }});
    }

    Object.defineProperty(window, '__webglProfiler', {configurable: false, value: {
        finish() {
            recording = false;
            const drained = [];
            for (const state of states) {
                suppressed++;
                let cleared = false;
                try {
                    for (let i = 0; i < 32; i++) {
                        const error = state.gl.getError();
                        if (error === state.gl.NO_ERROR) { cleared = true; break; }
                        drained.push({context: state.id, error});
                    }
                } catch (error) { drained.push({context: state.id, error: String(error)}); }
                finally { suppressed--; }
                if (!cleared) addOutcome({code: 'error_drain_incomplete', context: state.id});
            }
            for (const entry of drained) addOutcome({code: 'remaining_webgl_error', ...entry});
            for (const state of states) if (!state.positiveDraw) addOutcome({code: 'no_positive_work_draw', context: state.id});
            if (!states.length) addOutcome({code: 'no_seed_webgl_context'});
            if (truncated) addOutcome({code: 'event_buffer_full'});
            return {schema_version: 1, profiler_version: 'webgl-trace-2', outcome_cap: outcomeCap,
                contexts, events, truncated, outcomes};
        }
    }});

})();

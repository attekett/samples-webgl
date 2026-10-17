# Chrome WebGL crash report mutation reachability

Date: 2026-10-15

## Question and method

Could a mutation of a working WebGL seed reach the trigger class in the 50 downloaded reports under `~/git/dockerfiles/browser-fuzz/grizzly-modules/webgl/crash-data/blink-webgl/`? This is a static reading of each `issue.json` and relevant downloaded attachments. It does not establish that a historical bug remains in current Chrome, or that a call reaching the same code path reproduces the fault. Attachment names below are relative to `<bundle>/<issue-id>/`; every row also uses that directory's `issue.json`.

**Use these reports as evidence of failure mechanisms, not as mutation templates.** The mutator should not ingest the attached PoCs as seeds, encode issue IDs or their exact constants, or optimize toward their recorded crash stacks. The goal is to vary relationships and state transitions across many WebGL APIs and resources so it can expose faults at other sites. The ledger below explains why each report informs a mechanism or fails to do so; it is not an implementation recipe.

The distinction that matters for the mutator is:

- **V — valid WebGL route:** a clean seed can be changed into an API-valid flow that plausibly reaches the reported operation. Backend, shader acceptance, and reproduction still need testing.
- **I — invalid-call route:** a clean seed can reach the reported validation/error path only by making a call invalid, or the attached reproducer does so. This is useful for a separate validation campaign, but it cannot count toward the valid-flow mutator's success rate.
- **C — conditional or unproved:** there is a candidate operator, but validity, exact trigger, or required scheduling is not established by the bundle.
- **N — no demonstrated WebGL mutation:** there is no usable trigger, or the report is outside WebGL.

An API-valid mutation needs a linked program and matching resource state, in-range array views and offsets, legal enums, complete storage where required, and supported extensions. A JavaScript call that returns normally can still generate a WebGL error. Reports with a valid *initial* flow and an invalid final call are marked I.

Standards checks used for the shader/draw-buffer judgments: the [GLSL ES 3.00 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf) permits construction of one matrix shape from another, and [WEBGL_draw_buffers](https://registry.khronos.org/webgl/extensions/WEBGL_draw_buffers/) defines the WebGL1 extension and its gating.

## General mechanisms to mutate

| Mechanism | General mutation rule | Evidence examples, not target sequences |
| --- | --- | --- |
| Cached state and resource lifetime | Preserve a valid producer/consumer flow, then vary where a resource is bound, redefined, switched, or retired before a later draw, upload, readback, or presentation. Apply the rule to buffers, textures, VAOs, framebuffers, and programs where their dependencies can be tracked. | 40064044 and 40063051 show different resource families; 40058533 is only a weaker lifetime hint. |
| Coupled sizes and array views | Derive lengths, counts, strides, offsets, and allocation sizes from each other. Mutate one relation at a time around ordinary and limit-adjacent values, with separate valid and validation-error outcomes. Use the same rule across draw, uniform, texture, and extension APIs. | 40056214, 332939155, 40059380 and 40056920 expose different arithmetic surfaces. |
| Shader structure | Rewrite compilable GLSL syntax trees: matrix shapes, local-array sizes, indexing, function calls, and control-flow nesting. Keep interfaces and resource limits coherent, then check compile and link results. | 40063287, 357484640, 40074964 and 40074630 show compiler diversity. |
| Render and browser scheduling | Vary legal state changes around clear, draw, readback, presentation, context creation and destruction; keep the relevant extension and canvas path active. | 40064549, 40050541 and 40053883 show distinct observable paths. |

Do not specialize an operator to one report's magic value, exact call list, backend, or crash site. Sample multiple APIs and resource types per mechanism, then measure which operations actually execute and which new failure signatures appear. The repository's current ANGLE Vulkan lane cannot observe faults confined to D3D11, Metal, Mali, llvmpipe, or SwiftShader; backend diversity is part of evaluating a general mutator.

## Per-report ledger

| ID | Class | Observed trigger shape or evidence gap | Evidence beyond `issue.json` / environment |
| --- | --- | --- | --- |
| 328483401 | C | Change `bufferData` size versus typed-array overload; no testcase or argument values identify the crash. | Linux ASan, GLES2Implementation; no attachment. |
| 329271490 | C | Mutate nested struct-return/member-access GLSL and colliding names; attached shader may lack a function definition, so compile validity is uncertain. | `attachment_54551947`; ANGLE shader translator. |
| 332939155 | I | Change pixel-local-storage clear-value array offset to a huge value; attached draft-extension call uses out-of-range `srcOffset`. | `attachment_55253074`, `attachment_55639474`, `attachment_55253075`; Windows ASan. |
| 357484640 | C | Mutate nested loops/switch/phi merges in a WebGL2 vertex shader; the attached GLSL has possible uninitialized reads, so a valid equivalent needs compilation. | `attachment_58418053`; ANGLE Vulkan, Mesa Intel `hash_phi`. |
| 368205246 | C | Create many contexts, reload, then close Chrome; this needs browser lifecycle control and `--disable-gpu`, not an inline draw mutation. | `attachment_59489015`; unsymbolized fault. |
| 40050541 | V | Toggle context `alpha` to false and compare rendered frames. | `attachment_53414948`; Android Mali-400 visual flicker. |
| 40051021 | N | No testcase or useful stack; GraphicsFuzz UBSAN report does not identify an operator. | No attachment. |
| 40051513 | C | Iframe, AudioWorklet, context destruction, then an error path; external worklet/HTTPS and lifecycle scheduling exceed the current self-contained seed contract. | Report description and attachments; Chrome 79/82. |
| 40051639 | N | Context-creation MSAN finding without a testcase or controllable input. | No attachment. |
| 40052983 | N | QR-code service crash, not a WebGL trigger. | No attachment. |
| 40053265 | N | EXIF image-load report; its portrait JPEG is byte-identical to the image attached to 40053411, but this report supplies no independent WebGL route. | `attachment_53402481`; macOS. |
| 40053411 | C | Vary image format, orientation, dimensions and unpack state during `texSubImage2D`; the attachment calls it without demonstrated texture storage, so a valid trigger is unproved. | `attachment_52999724`; Blink image conversion. |
| 40053640 | I | Bind an indexed VAO, switch to a fresh VAO without element-array storage, then call `drawRangeElements`. The final draw is invalid, but historically passed stale validation to D3D. | `attachment_53362752`, patch `attachment_53362778`; Windows ANGLE D3D. |
| 40053883 | V | Toggle `xrCompatible` at OffscreenCanvas context creation. | `attachment_53413091`; Blink `MakeXrCompatibleSync`. |
| 40054092 | C | Increase a GLSL local array toward stack exhaustion. Legal source may still be rejected by compiler resource limits; use a bounded, isolated shader lane. | `attachment_52907149`; ANGLE GL / llvmpipe LLVM 10. |
| 40054858 | N | System freeze report has no downloaded reproducer. Avoid experimenting on the host from this description alone. | No attachment; Intel iGPU Ubuntu. |
| 40056214 | I | Increase a multi-draw typed-array offset or draw count beyond its array bounds; this is a validation arithmetic bug, not a valid draw. | `attachment_52891582`, `attachment_52891601`; `WEBGL_multi_draw`, Chrome 91/92. |
| 40056230 | N | UBSAN stack-trace metadata only; no WebGL trigger. | No attachment. |
| 40056306 | I | `releaseVideoFrame` with a fabricated handle targets validation of a draft video-frame extension. Valid imported-frame lifetime route is unproved. | `attachment_53294691`; Chrome 91. |
| 40056920 | C | Increase `texStorage3D` dimensions around supported limits with legal sized formats; the reported allocation approaches 4.8 GiB and may fail for ordinary resource reasons. | `attachment_53267309`, `attachment_53267330`; Windows ANGLE. |
| 40057230 | N | UBSAN stack-trace metadata only; no WebGL trigger. | No attachment. |
| 40058533 | C | Vulkan garbage-object lifetime suggests resource churn, but no testcase identifies the object or ordering. | No attachment; ANGLE Vulkan. |
| 40059043 | C | Pixel-store and image-conversion changes might exercise a statically flagged uninitialized value; there is no dynamic trigger. | No attachment; Blink static analyzer. |
| 40059380 | I | Increase a `uniform1iv` typed view to nearly 4 GiB. The attached call passes an integer setter to a `mat4` location and far exceeds its uniform count, so valid-WebGL reachability is unproved. The command-size overflow is in the renderer before an enormous copy. | `attachment_53240574`; WebAssembly 4 GiB memory, isolated resource-heavy lane. |
| 40059411 | I | Attached `compileShader` sequence begins with invalid shader enums and continues with undefined/unlinked objects. A valid compile/relink mutation reaches the API family, not the demonstrated path. | `attachment_53421707`, `attachment_53421708`; Windows ANGLE. |
| 40059664 | C | Destroy a context while XR-compatibility promise resolution is pending; no testcase supplies timing or a valid sequence. | No attachment; Blink promise/context lifetime. |
| 40059878 | N | GPU-process assertion follows EGL/startup or another crash; no WebGL call sequence is established. | `attachment_52910800`; Breakpad count assertion. |
| 40059929 | C | Change `UNPACK_IMAGE_HEIGHT` during extension-gated DXT3 compressed 2D-array upload with matching data; a later attached upload appears valid, but an earlier invalid-enum call may be part of the trigger. | `attachment_52979821`; macOS AMD GL. |
| 40060309 | C | Combine integer FBO, transform feedback, readback, and buffer replacement while drawing; attached sequence likely produces WebGL errors, so a clean equivalent is unproved. | `attachment_53182813`; SwiftShader `DrawCall::run`. |
| 40060714 | C | Skia asynchronous readback plus device loss is outside direct WebGL control; draws/snapshots can only influence scheduling. | Attachments in report; Vulkan Skia UAF. |
| 40061001 | C | Same Skia mapped-buffer UAF class as 40060714, without a reliable WebGL-only operator. | Attachments in report; Vulkan Skia UAF. |
| 40061057 | I | Attached draw uses missing/undersized vertex data and extreme indices. A bounded index/attribute mutation reaches SwiftShader draw code but does not demonstrate the same fault. | `attachment_53272550`, `attachment_53272551`; SwiftShader. |
| 40061667 | I | Attached 3D upload uses WebGL2-invalid `LUMINANCE` plus huge dimensions. Replacing it with a valid sized/format pair changes the path and leaves WARP copy fault unproved. | `attachment_53296711`; Windows WARP. |
| 40063051 | V | Repeated canvas-to-texture mip-zero redefinition with base level one, drawing, and presentation. | `attachment_53135456`; Windows ANGLE D3D11. |
| 40063287 | V | Replace or nest matrix constructors in otherwise valid WebGL2 GLSL, then compile/link. | `attachment_53312783`; Android Mali shader compiler. |
| 40063770 | C | Very large local GLSL arrays and dynamic access; report lacks a testcase and compiler acceptance is uncertain. | No attachment; SwiftShader. |
| 40064044 | V | Keep active instanced attribute backed, then mutate draw type or divisor to exercise non-instanced fetch. | `attachment_52963873`, patch `attachment_52963890`; Windows ANGLE D3D11. |
| 40064549 | V | Change default-framebuffer draw-buffer/clear/present order with `WEBGL_draw_buffers` gating. | `attachment_53024678`; macOS Chrome compositor. |
| 40066076 | I | Attached large `vertexAttribPointer` offset lacks matching storage and uses an invalid divisor argument. A valid offset plus buffer-size edit has not been shown to trigger the GL bug. | `attachment_53402725`; macOS ANGLE GL. |
| 40066392 | I | Attached Metal draw uses invalid mode/extension value and lacks valid vertex setup; no valid equivalent shown. | `attachment_52998457`; macOS ANGLE Metal. |
| 40067239 | C | Change GLSL array count, size and dynamic read together; thousands of arrays may fail compiler limits. | `attachment_52883161`; SwiftShader/ANGLE. |
| 40069408 | C | Program creation/deletion and GC might affect a statically identified raw-pointer LRU cache; no insertion/lifetime reproducer. | No attachment; Blink `WebGLProgram` cache. |
| 40071447 | N | Shadertoy navigation with an unsymbolized illegal-instruction crash, no shader in bundle. | Report attachments; VirtualBox/software GPU. |
| 40074630 | C | Mutate fragment shader loops, array indexing and constructors; clean compilation must be checked. | `attachment_53393790`; Apple Metal compiler. |
| 40074964 | C | Increase nesting of bounded shader loops; plausibly valid GLSL, but compiler stack overflow/hang requires timeout isolation. | `attachment_53192429`; AMD OpenGL compiler. |
| 40075394 | C | Repeated function calls and loops may reach Metal compiler; attached shader acceptance and even Chrome attribution are uncertain. | `attachment_53047311`; crash log names WebKit GPU process. |
| 408093267 | I | Attached texture/draw/reload sequence uses invalid arguments. A valid long-running shader might induce a GPU timeout, but the AMD kernel UAF needs the affected kernel/device and is not the same WebGL trigger. | `attachment_64545749`; AMD Linux 6.11.0-19. |
| 40947303 | C | Add `getProgramInfoLog` after link to reach `GetProgramiv`; no testcase and the reported crash was unreproducible. | No attachment; GLES2Implementation. |
| 41486565 | I | Attached index arrays exceed available vertices, or omit vertex buffer storage. Coordinated in-range index/buffer edits avoid the reported out-of-range condition. | `attachment_53374270`, `attachment_53374306`; Linux NVIDIA ANGLE GL. |
| 434369230 | C | Repeated legal `bufferData` allocations plausibly reach global GPU loss through resource exhaustion; allocation count and bytes need a separate capped resilience run. | `attachment_67947338`; Chrome 132/138. |

## What this changes in the mutator plan

The [custom-mutator plan](plans/2026-10-15-webgl-custom-mutators.md) should implement the four mechanism families above. Begin with common resource and parameter relationships that existing seeds already expose, then apply each operator wherever the dependency can be checked. A seed's historical similarity to an issue is not a selection criterion. Use the reports as a held-out sanity check that the operator families could traverse varied trigger shapes, and use new backend coverage and distinct findings to judge whether the mutator is useful.

The external `browser-fuzz` generator already has patterns named `generate_multi_draw_offset_overflow`, `generate_pixel_local_storage_overflow`, `generate_draw_range_elements_confusion`, `generate_vao_swap_during_draw_coercion`, `generate_buffer_orphaning_draw_race`, `generate_compressed_format_mismatch`, `generate_stride_boundary_instanced_draw`, and others. It guarantees one creative pattern per file by rotation and also samples them opportunistically. Those are **generated probes**, often with deliberately invalid calls; they do not show that the valid-seed mutation engine exists or that a backend reached an intended transition. Reuse their ideas and record per-mutant validity, backend, and observed work rather than counting source-text occurrence as coverage.

A text scan of the current `agent_outputs/` and `samples-webgl/` HTML files found 419 files: one mentions `WEBGL_multi_draw`, 58 call `vertexAttribDivisor`, four call `compressedTexImage3D`, and one calls `drawBuffersWEBGL`. These counts show source material for some operators and sparse seeds for others; they do not establish that the calls execute cleanly. The generator's round-robin index is process-local, so campaign coverage also depends on how many files each generator invocation creates.

Validation-path mutations should use generic relationship changes (for example, an offset crossing a view's bound or a consumer using a resource no longer bound) across eligible APIs. Keep them in a separately labeled error-path campaign, because an invalid final call fails the valid-flow criterion even if it historically exposed a memory-safety bug. Cap allocation and shader complexity independently of any old PoC values.

## Limits

No historical attachment was executed. The bundle mixes reproducible PoCs, static analyzer findings, duplicates, and incomplete reports. Current Chrome builds may have fixed the reported bugs. The proposed operators are meant to traverse **families of state and data relationships at new sites**, not to recreate historical faults.

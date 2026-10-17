# Reachability: ANGLE Vulkan destroyed-VkBuffer bind after an empty multi-draw and a program switch

2026-10-15. Question: could this corpus and the browser-fuzz WebGL producers have found the bug
behind the user's reproducer ("ANGLE Vulkan: destroyed VkBuffer bound after empty multi-draw +
program switch"; heap-use-after-free in `vkCmdBindVertexBuffers2` in the GPU process)?

Short answer: **no**, not with the current seeds or producers. The environment can probably
detect the bug class, but that is not demonstrated. Static checks only; see "What was and was
not run".

## Trigger shape (from the reproducer)

All of these, in one cycle, repeated a few times:

1. A WebGL2 context with `WEBGL_multi_draw`, running on ANGLE's Vulkan backend.
2. Program P1 uses attribute slot 0, read from buffer B with the array enabled. Draw, then
   `finish()`.
3. `disableVertexAttribArray(0)`, with default attribute values set by `vertexAttrib4f`.
4. An **empty** `multiDrawArraysWEBGL` (one draw, `count` 0). It syncs the VAO and draws nothing.
5. `useProgram(P2)`, where slot 0 is **inactive** but below the program's highest attribute
   location. ANGLE then drops the pending default-attribute update.
6. `bufferData` re-specifies B at a size **above ANGLE's 8 MiB suballocation limit**. B owns its
   own VkBuffer, which is destroyed on re-specification.
7. `drawArrays`: slot 0 is bound with the destroyed VkBuffer handle.

The use-after-free happens on the Vulkan driver's CPU side. It is visible only with an
ASan-built driver.

## This corpus (static, `samples-webgl/` + `agent_outputs/`, 537 HTML files)

| Ingredient | Seeds containing it |
|---|---:|
| request `WEBGL_multi_draw` | 17 |
| call `multiDrawArraysWEBGL` or `multiDrawElementsWEBGL` | 16 |
| multi-draw with a zero `count` | **0**; all 16 use `counts = new Int32Array([6, 6, 6, 6])` |
| `vertexAttrib*f` default values | 8 |
| `disableVertexAttribArray` | 50 |
| `bindAttribLocation` | 8 |
| more than one `useProgram` | 124 |
| `bufferData` at MiB scale | 2 (1 MiB and 2 MiB literals; none above 8 MiB) |

Closest seed: `agent_outputs/mutation_b78_s1_attributes_tf_multi_draw.html` (7.7 KB). It is the
only multi-draw seed that also disables an attribute (line 176), sets its default value
(line 177), switches programs (lines 182 and 205) and calls `bufferData` four times. Its order
is different, though:

- The multi-draw (line 211) comes *after* the last program switch.
- The multi-draw counts are 6.
- No buffer is re-specified after the multi-draw.
- Buffer sizes are tiny (`pointCount * 4 * 4`).
- Nothing loops with `finish()`.

Reaching the trigger needs at least four coordinated edits:

1. A zero count.
2. A program switch to a program with an inactive lower slot, placed after the multi-draw.
3. A `bufferData` larger than 8 MiB on the slot's buffer, placed after that switch.
4. A draw after that.

Plus repetition, because the reproducer's own comment says the release timing varies between
runs.

**Radamsa** (`num` and line operators, one mutation per output) produces one of these per mutant.
The `num` mutator can turn a 6 into 0, or a size into a large value. It does not move a
`bufferData` after a `useProgram` while also enlarging it past 8 MiB. Probability: effectively
zero (reasoning).

## browser-fuzz WebGL generator (`grizzly-modules/webgl/generator.py`)

- **Multi-draw is emitted only by `generate_multi_draw_offset_overflow()`** (around line 2125).
  That probe uses fixed `counts = [1, 1, 1, 1]` with overflowing offsets and draw counts, never a
  zero `count`, and runs inside `try/catch` blocks unrelated to attribute or program state.
- **`bufferData` sizes** are mostly 0 B-64 KiB. One near-limit probe (around line 586-588)
  picks from `[65536, 131072, 1048576, 16777216]` elements; at 16,777,216 floats that is 64 MiB,
  so one choice exceeds 8 MiB. Nothing ties that probe to a vertex-attribute slot that is
  disabled, used by one program and inactive in the next.
- **Default attribute values:** only `vertexAttrib4fv` with random attribute indices
  (around lines 3591 and 4998).

The generator emits the ingredients in isolation, never as the ordered chain. Its probability of
producing the chain is effectively zero (reasoning).

## Harness and environment (detection side)

- **ANGLE on Vulkan over ASan lavapipe was already the case before `--use-angle=vulkan`.**
  Chromium WebGL in the harness container runs ANGLE on Vulkan over the ASan-built Mesa
  lavapipe. The graphics-stack plan measured `WEBGL_debug_renderer_info` =
  `ANGLE (Mesa, Vulkan ... llvmpipe ...)`. Even in the earlier software fallback mode
  (`angle=swiftshader`), ANGLE's Vulkan backend did not find the SwiftShader ICD and fell back
  to the container's lavapipe ICD (measured in the samples-webgpu Chromium harness
  investigation). browser-fuzz `bf54068` (`--use-angle=vulkan`) makes that explicit and also
  moves the compositor onto Vulkan.
- **Detection itself is unverified.** An ASan lavapipe should catch the destroyed-buffer
  dereference in `vkCmdBindVertexBuffers2` if lavapipe touches the freed buffer object on the
  CPU, either when the command is recorded or when it executes. That is reasoning; nobody
  checked lavapipe's bind path or demonstrated it.
- **The harness corpus is a stale snapshot.** `~/samples/samples-webgl` has 465 files from
  2026-08-24, while this repo has 537 now. The finding above holds for both: neither has a
  zero-count multi-draw.

## What was and was not run

- One `grizzly-replay` of the reproducer (5 iterations) in `browser-fuzz-chromium:latest` with
  the current `config/chromium.flags` (including `--use-angle=vulkan`) and ASan Mesa:
  "No results detected".
- **This run is inconclusive.** It did not confirm in that run that the context was ANGLE
  Vulkan, that `WEBGL_multi_draw` was exposed, or that the cycles ran. A direct run with page
  logging was started and then stopped, because the work belonged to this project, not the
  WebGPU one.
- No producer was run against the trigger shape; all likelihood statements are reasoning from
  the code and seeds.

## If you want this class reachable

Ranked by cost:

1. **Confirm detection.** Run the reproducer in the harness container with a page log of the
   renderer string, the extension and the cycle results. If ASan lavapipe does not report,
   check lavapipe's bind path; detection may need an ASan RADV/ANV lane like the reporter's.
2. **Write one or two seeds** with the safe version of the chain, one edit away from the hazard.
   - The safe version: a multi-draw with `count` 1 or more, an attribute-switching program pair
     with an inactive lower slot, a re-specification of a vertex buffer larger than 8 MiB
     after the switch, a draw, and a loop of about 8 cycles with `finish()`.
   - One edit away: the count goes to 0, or the `bufferData` and `useProgram` lines swap.
   - Keep the large buffer to one or two allocations so ASan memory stays bounded.
3. **Generator:** let `generate_multi_draw_offset_overflow()` sometimes use valid zero counts
   (`counts = [0]`, `drawcount` 1) inside an attribute, program and buffer sequence instead of
   only the overflow probes. Add a re-specification above the suballocation limit for a
   buffer that is bound to a vertex attribute.

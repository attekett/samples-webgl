---
name: expand-webgl-coverage
description: Use when the WebGL fuzzing corpus needs more API coverage - identifies gaps via audit tool, selects missing features, creates mutation-optimized seeds, validates and verifies gap closure
---

# Expand WebGL Coverage

## Overview

Systematically close WebGL API coverage gaps by running the audit tool, selecting missing features, creating mutation-optimized fuzzing seeds, and verifying gap closure. Each seed targets 3-5 related missing methods using the three-zone architecture.

**Announce at start:** "I'm using the expand-webgl-coverage skill to close coverage gaps."

## Prerequisites

Read these files before starting (in order):
1. `docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md` - Three-zone architecture, variable tiers, line repetition patterns
2. `AGENTS.md` - Seed creation rules and validation workflow
3. `UNSUPPORTED.md` - Extensions and features to avoid

## The Workflow

### Step 1: Audit Current Coverage

Ensure the venv is available (`source venv/bin/activate` or use `./venv/bin/python`):

```bash
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --output /tmp/audit_report.json
```

Note current metrics: methods covered/total, Tier 1/2/3 gap counts.

### Step 2: Select Target Features

Read `/tmp/audit_report.json`. Prioritize:

1. **Tier 1 - Missing methods** (highest value): Group by category
   - Uniform setters: `uniform1f`, `uniform2fv`, `uniformMatrix3fv`, etc.
   - Getters/queries: `getBufferParameter`, `getTexParameter`, `getRenderbufferParameter`, etc.
   - Vertex attribs: `vertexAttrib1f`, `vertexAttrib4fv`, `getVertexAttrib`, etc.
   - Type checkers: `isBuffer`, `isTexture`, `isProgram`, `isShader`, etc.
   - Sampler/sync: `samplerParameterf`, `clientWaitSync`, `fenceSync`, etc.
2. **Tier 3 - GLSL builtins**: `smoothstep`, `refract`, `matrixCompMult`, `inversesqrt`, etc.
3. **Tier 2 - Missing constant roles**: Methods covered but missing key enum/parameter usage

**Per seed**: Target 3-5 related missing methods + 2-3 GLSL builtins in shaders. Combine with well-covered methods for realistic state machine context.

### Step 3: Create Seeds

Follow the **three-zone architecture** from `docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md`:

**Declaration Zone:**
- 5-8 Tier 1 amplification variables (cascading mutations)
- 4-6 Tier 3 enum constants

**Setup Zone (4-8 try-catch blocks):**
- Resource creation with line repetition patterns
- Use 3+ patterns from: bind ping-pong, creation redundancy, FBO attachment swapping, enable/disable thrashing, deletion and reuse

**Execution Zone (2-4 try-catch blocks):**
- State configuration, draw calls, resource cleanup
- Mix Tier 2 inline literals (20-40 total) with variable references

**Rules:**
- `catch(e) {}` in production (use `catch(e) { console.log(e); }` only during dev debugging)
- No comments, no console.log in final version
- 150-300 lines, 256x256 canvas, self-contained HTML
- File naming: `agent_outputs/mutation_bN_sN_<descriptive>.html`
- Check `UNSUPPORTED.md` before using any extension
- Extension gating via `REQUIRED_EXTENSIONS` array pattern (see AGENTS.md boilerplate)
- No defensive programming, no error checking, no clean abstractions (seeds are mutation targets, not programs)

### Step 4: Validate

```bash
# During development (with console.log in catch blocks):
./run_tests.sh --test-file agent_outputs/<file>.html --browsers firefox
```

Read the JSON output file (same name, `.json` extension). Fix iteratively until:
- `"passed": true`
- `"console_logs": []`
- `"javascript_errors": []`

**Then strip console.log** → `catch(e) {}`, re-validate. Never assume fixes work.

### Step 5: Verify Gap Closure

```bash
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --file agent_outputs/<file>.html
```

Delta report must show new method/constant coverage. If it shows "Redundant" entries with no new coverage, the seed is not closing gaps - redesign it.

### Step 6: Final Audit

After all seeds complete, re-run full audit (Step 1). Compare before/after metrics to confirm improvement.

## Quick Reference

| Step | Command | Success Check |
|------|---------|---------------|
| Audit | `PYTHONPATH=scripts ./venv/bin/python -m api_audit --surface docs/webgl_api_surface.json --corpus-dirs samples-webgl agent_outputs --output /tmp/audit.json` | Gap counts decrease |
| Validate | `./run_tests.sh --test-file <file> --browsers firefox` | JSON: passed=true, no errors |
| Delta | `PYTHONPATH=scripts ./venv/bin/python -m api_audit --surface docs/webgl_api_surface.json --file <file>` | Shows new coverage |

## Seed Design Checklist

Before committing a seed:
- [ ] 5-8 Tier 1 amplification variables
- [ ] 4-6 Tier 3 enum constants
- [ ] 20-40 Tier 2 inline numeric literals
- [ ] 6-10 try-catch blocks (4-8 setup + 2-4 execution)
- [ ] 3+ line repetition patterns used
- [ ] All `catch(e) {}` (no console.log)
- [ ] No comments in code
- [ ] `REQUIRED_EXTENSIONS` array populated (if using extensions)
- [ ] Deletion/reuse pattern in cleanup block
- [ ] 150-300 lines total
- [ ] Test passes with zero errors
- [ ] Delta report shows new coverage

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Seed only covers already-covered methods | Check delta report for NEW coverage before committing |
| Using unsupported extension | Read UNSUPPORTED.md first; Firefox-specific issues exist |
| console.log left in production | Strip all console.log before final validation |
| Only 1 new method per seed | Target 3-5 related missing methods per seed |
| Skipping validation after code changes | Always re-run run_tests.sh, never assume fixes work |
| Missing try-catch blocks | Need 6-10 blocks per seed |
| No line repetition patterns | Include 3+ patterns (bind ping-pong, thrashing, etc.) |
| Defensive programming in seeds | No validation, no error checking - seeds are mutation targets |
| Helper functions hiding API calls | Inline everything - expose all WebGL operations for mutation |
| Nested try-catch blocks | One try-catch per logical operation group, never nested |

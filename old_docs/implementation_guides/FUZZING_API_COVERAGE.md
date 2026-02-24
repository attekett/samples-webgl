# WebGPU API Surface Coverage Matrix

This document maps WebGPU API methods to corpus test flows, ensuring complete coverage.

## Legend
- ✅ Covered by existing flow
- 🔲 Not yet covered - needs flow
- ⚠️ Feature-gated (requires optional feature)

---

## GPUDevice Methods

| Method | Primary Flow | Additional Flows | Notes |
|--------|-------------|------------------|-------|
| `createBuffer` | FLOW-C-001 | All flows | Fundamental |
| `createTexture` | FLOW-R-001 | FLOW-MP-*, FLOW-TU-* | |
| `createSampler` | FLOW-SP-001 | FLOW-R-002, FLOW-MP-002 | |
| `createBindGroupLayout` | FLOW-BG-001 | Most flows | |
| `createBindGroup` | FLOW-BG-001 | Most flows | |
| `createPipelineLayout` | FLOW-BG-001 | Most flows | |
| `createShaderModule` | FLOW-C-001 | All flows | |
| `createComputePipeline` | FLOW-C-001 | FLOW-C-*, FLOW-CR-*, FLOW-MP-* | |
| `createRenderPipeline` | FLOW-R-001 | FLOW-R-*, FLOW-CR-*, FLOW-MP-* | |
| `createComputePipelineAsync` | FLOW-AP-001 | | Async variant |
| `createRenderPipelineAsync` | FLOW-AP-002 | | Async variant |
| `createCommandEncoder` | FLOW-C-001 | All flows | |
| `createRenderBundleEncoder` | FLOW-RB-001 | FLOW-RB-* | |
| `createQuerySet` | FLOW-QO-001 | FLOW-QO-* | |
| `importExternalTexture` | FLOW-EX-001 | | Video/canvas source |
| `pushErrorScope` | FLOW-DB-002 | Template | |
| `popErrorScope` | FLOW-DB-002 | Template | |
| `destroy` | FLOW-LC-003 | | |

---

## GPUBuffer Methods

| Method | Primary Flow | Additional Flows | Notes |
|--------|-------------|------------------|-------|
| `mapAsync` | FLOW-BU-004 | FLOW-CC-001 | Readback pattern |
| `getMappedRange` | FLOW-BU-004 | FLOW-CC-001 | After mapAsync |
| `unmap` | FLOW-BU-004 | FLOW-CC-001 | |
| `destroy` | FLOW-LC-001 | | |

---

## GPUTexture Methods

| Method | Primary Flow | Additional Flows | Notes |
|--------|-------------|------------------|-------|
| `createView` | FLOW-TU-002 | Most render flows | Multiple views |
| `destroy` | FLOW-LC-002 | | |

---

## GPUCommandEncoder Methods

| Method | Primary Flow | Additional Flows | Notes |
|--------|-------------|------------------|-------|
| `beginRenderPass` | FLOW-R-001 | All render flows | |
| `beginComputePass` | FLOW-C-001 | All compute flows | |
| `copyBufferToBuffer` | FLOW-CO-001 | FLOW-CC-001 | |
| `copyBufferToTexture` | FLOW-CO-002 | | |
| `copyTextureToBuffer` | FLOW-CO-003 | | |
| `copyTextureToTexture` | FLOW-CO-004 | FLOW-RC-004 | |
| `clearBuffer` | FLOW-CO-005 | | |
| `resolveQuerySet` | FLOW-QO-001 | FLOW-QO-* | |
| `finish` | FLOW-C-001 | All flows | |
| `pushDebugGroup` | FLOW-DB-001 | | Debug |
| `popDebugGroup` | FLOW-DB-001 | | Debug |
| `insertDebugMarker` | FLOW-DB-001 | | Debug |

---

## GPUComputePassEncoder Methods

| Method | Primary Flow | Additional Flows | Notes |
|--------|-------------|------------------|-------|
| `setPipeline` | FLOW-C-001 | All compute flows | |
| `setBindGroup` | FLOW-C-001 | All compute flows | Dynamic offsets in FLOW-BU-003 |
| `dispatchWorkgroups` | FLOW-C-001 | Most compute flows | |
| `dispatchWorkgroupsIndirect` | FLOW-C-004 | | |
| `end` | FLOW-C-001 | All compute flows | |
| `pushDebugGroup` | FLOW-DB-001 | | |
| `popDebugGroup` | FLOW-DB-001 | | |
| `insertDebugMarker` | FLOW-DB-001 | | |

---

## GPURenderPassEncoder Methods

| Method | Primary Flow | Additional Flows | Notes |
|--------|-------------|------------------|-------|
| `setPipeline` | FLOW-R-001 | All render flows | |
| `setBindGroup` | FLOW-R-001 | All render flows | Dynamic in FLOW-BU-002 |
| `setVertexBuffer` | FLOW-R-001 | All render flows | |
| `setIndexBuffer` | FLOW-R-002 | FLOW-CR-004 | |
| `draw` | FLOW-R-001 | Most render flows | |
| `drawIndexed` | FLOW-R-002 | FLOW-CR-004 | |
| `drawIndirect` | FLOW-R-010 | FLOW-CR-005 | |
| `drawIndexedIndirect` | FLOW-R-010 | | |
| `setViewport` | FLOW-R-007 | | |
| `setScissorRect` | FLOW-R-007 | | |
| `setBlendConstant` | FLOW-R-008 | | |
| `setStencilReference` | FLOW-R-009 | | |
| `beginOcclusionQuery` | FLOW-QO-001 | | |
| `endOcclusionQuery` | FLOW-QO-001 | | |
| `executeBundles` | FLOW-RB-001 | FLOW-RB-* | |
| `end` | FLOW-R-001 | All render flows | |
| `pushDebugGroup` | FLOW-DB-001 | | |
| `popDebugGroup` | FLOW-DB-001 | | |
| `insertDebugMarker` | FLOW-DB-001 | | |

---

## GPURenderBundleEncoder Methods

| Method | Primary Flow | Additional Flows | Notes |
|--------|-------------|------------------|-------|
| `setPipeline` | FLOW-RB-001 | FLOW-RB-* | |
| `setBindGroup` | FLOW-RB-002 | FLOW-RB-* | |
| `setVertexBuffer` | FLOW-RB-001 | FLOW-RB-* | |
| `setIndexBuffer` | FLOW-RB-001 | FLOW-RB-* | |
| `draw` | FLOW-RB-001 | FLOW-RB-* | |
| `drawIndexed` | FLOW-RB-001 | | |
| `drawIndirect` | FLOW-RB-001 | | |
| `drawIndexedIndirect` | FLOW-RB-001 | | |
| `finish` | FLOW-RB-001 | FLOW-RB-* | |

---

## GPUQueue Methods

| Method | Primary Flow | Additional Flows | Notes |
|--------|-------------|------------------|-------|
| `submit` | FLOW-C-001 | All flows | |
| `writeBuffer` | FLOW-C-003 | Many flows | Dynamic data |
| `writeTexture` | FLOW-TU-007 | | |
| `copyExternalImageToTexture` | FLOW-CO-006 | FLOW-EX-001 | |
| `onSubmittedWorkDone` | FLOW-BU-004 | | Sync point |

---

## GPUCanvasContext Methods

| Method | Primary Flow | Additional Flows | Notes |
|--------|-------------|------------------|-------|
| `configure` | FLOW-CV-001 | All canvas flows | |
| `unconfigure` | FLOW-CV-002 | | |
| `getCurrentTexture` | FLOW-CV-001 | All canvas flows | |
| `getConfiguration` | FLOW-CV-002 | | |

---

## Pipeline Descriptor Coverage

### GPURenderPipelineDescriptor Fields

| Field | Primary Flow | Notes |
|-------|-------------|-------|
| `vertex.module` | FLOW-R-001 | All render |
| `vertex.entryPoint` | FLOW-R-001 | |
| `vertex.buffers` | FLOW-R-001 | Attribute formats in FLOW-PS-006 |
| `vertex.constants` | FLOW-C-007 | Override constants |
| `primitive.topology` | FLOW-PS-001 | All topologies |
| `primitive.stripIndexFormat` | FLOW-R-012 | Strip topologies |
| `primitive.frontFace` | FLOW-R-014 | cw/ccw |
| `primitive.cullMode` | FLOW-R-014 | none/front/back |
| `primitive.unclippedDepth` | 🔲 | depth-clip-control feature |
| `depthStencil.format` | FLOW-R-005 | |
| `depthStencil.depthWriteEnabled` | FLOW-R-005 | |
| `depthStencil.depthCompare` | FLOW-PS-003 | All compare funcs |
| `depthStencil.stencilFront` | FLOW-PS-004 | All stencil ops |
| `depthStencil.stencilBack` | FLOW-PS-004 | |
| `depthStencil.depthBias` | FLOW-R-015 | |
| `depthStencil.depthBiasSlopeScale` | FLOW-R-015 | |
| `depthStencil.depthBiasClamp` | FLOW-R-015 | |
| `multisample.count` | FLOW-R-006 | 1 or 4 |
| `multisample.mask` | FLOW-R-006 | |
| `multisample.alphaToCoverageEnabled` | FLOW-R-013 | |
| `fragment.module` | FLOW-R-001 | |
| `fragment.entryPoint` | FLOW-R-001 | |
| `fragment.targets` | FLOW-R-001 | Multiple in FLOW-R-004 |
| `fragment.targets[].format` | FLOW-TF-001 | Format coverage |
| `fragment.targets[].blend` | FLOW-PS-002 | Blend modes |
| `fragment.targets[].writeMask` | FLOW-PS-005 | |

### GPUComputePipelineDescriptor Fields

| Field | Primary Flow | Notes |
|-------|-------------|-------|
| `compute.module` | FLOW-C-001 | All compute |
| `compute.entryPoint` | FLOW-C-001 | |
| `compute.constants` | FLOW-C-007 | Override constants |

---

## Render Pass Descriptor Coverage

### GPURenderPassDescriptor Fields

| Field | Primary Flow | Notes |
|-------|-------------|-------|
| `colorAttachments` | FLOW-R-001 | Multiple in FLOW-R-004 |
| `colorAttachments[].view` | FLOW-R-001 | |
| `colorAttachments[].depthSlice` | FLOW-RP-005 | 3D texture render |
| `colorAttachments[].resolveTarget` | FLOW-R-006 | MSAA resolve |
| `colorAttachments[].clearValue` | FLOW-RP-002 | |
| `colorAttachments[].loadOp` | FLOW-RP-001 | clear/load |
| `colorAttachments[].storeOp` | FLOW-RP-001 | store/discard |
| `depthStencilAttachment.view` | FLOW-R-005 | |
| `depthStencilAttachment.depthClearValue` | FLOW-RP-002 | |
| `depthStencilAttachment.depthLoadOp` | FLOW-RP-001 | |
| `depthStencilAttachment.depthStoreOp` | FLOW-RP-001 | |
| `depthStencilAttachment.depthReadOnly` | FLOW-RP-003 | |
| `depthStencilAttachment.stencilClearValue` | FLOW-RP-002 | |
| `depthStencilAttachment.stencilLoadOp` | FLOW-RP-001 | |
| `depthStencilAttachment.stencilStoreOp` | FLOW-RP-001 | |
| `depthStencilAttachment.stencilReadOnly` | FLOW-RP-003 | |
| `occlusionQuerySet` | FLOW-QO-001 | |
| `timestampWrites` | ⚠️ FLOW-QO-002 | timestamp-query feature |
| `maxDrawCount` | FLOW-R-001 | Default: 50000000 |

---

## Additional Flows Needed

Based on the coverage analysis, the following flows should be added:

### External Texture Flows

#### FLOW-EX-001: Import Video External Texture
- Create HTMLVideoElement
- importExternalTexture from video
- Sample in shader
- Note: Short-lived resource

#### FLOW-EX-002: Import Canvas External Texture
- Create 2D canvas
- importExternalTexture from canvas
- Sample in shader

### writeTexture Flow

#### FLOW-TU-007: Queue Write Texture
- Create texture
- Use queue.writeTexture() to populate
- Sample in render pass

### Additional Validation Flows

#### FLOW-VB-004: Texture Dimension Limits
- Create textures at dimension limits
- maxTextureDimension1D, maxTextureDimension2D, maxTextureDimension3D

#### FLOW-VB-005: Array Layer Limits
- Create 2D array texture at maxTextureArrayLayers

#### FLOW-VB-006: Bind Group Limits
- Use maxBindGroups bind groups
- Use maxBindingsPerBindGroup bindings

---

## Feature-Gated Flows

These require checking for feature support first:

| Feature | Flows Needed |
|---------|-------------|
| `timestamp-query` | FLOW-QO-002 |
| `depth-clip-control` | FLOW-DC-001 (unclippedDepth) |
| `depth32float-stencil8` | FLOW-TF-007 |
| `indirect-first-instance` | Already covered in FLOW-R-010 |
| `shader-f16` | FLOW-WS-006 (f16 shader type) |
| `rg11b10ufloat-renderable` | FLOW-TF-008 |
| `bgra8unorm-storage` | FLOW-TF-009 |
| `float32-filterable` | FLOW-TF-010 |
| `float32-blendable` | FLOW-TF-011 |
| `clip-distances` | FLOW-WS-007 |
| `dual-source-blending` | FLOW-PS-007 |

---

## Summary Statistics

- **Total API Methods to Cover:** ~80
- **Methods Covered by Plan:** ~75 (94%)
- **Remaining Methods:** External texture, some edge cases
- **Feature-Gated Methods:** 10+ (optional)

## Priority Order for Maximum Coverage

1. **Immediate:** FLOW-CR-001 through FLOW-CR-005 (covers most common patterns)
2. **High:** FLOW-MP-002, FLOW-MP-003 (complex multi-pass)
3. **Medium:** FLOW-BG-*, FLOW-SP-*, FLOW-RB-* (resource patterns)
4. **Lower:** FLOW-PS-*, FLOW-TF-* (state variations)
5. **Last:** Feature-gated flows (require feature detection)





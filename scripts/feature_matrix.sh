#!/bin/bash
echo "## 8. Feature Coverage Matrix"
echo ""
echo "| Feature Category | Seeds | Coverage |"
echo "|------------------|-------|----------|"

total=$(ls agent_outputs/mutation_b*.html 2>/dev/null | wc -l)

# Buffer Operations
buf_count=$(grep -l 'createBuffer\|bufferData\|bufferSubData' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Buffer Operations | $buf_count/$total | $((buf_count*100/total))% |"

# UBO
ubo_count=$(grep -l 'UNIFORM_BUFFER\|uniformBlockBinding\|bindBufferBase' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Uniform Buffer Objects | $ubo_count/$total | $((ubo_count*100/total))% |"

# Transform Feedback
tf_count=$(grep -l 'TRANSFORM_FEEDBACK\|transformFeedbackVaryings\|beginTransformFeedback' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Transform Feedback | $tf_count/$total | $((tf_count*100/total))% |"

# Textures
tex_count=$(grep -l 'createTexture\|texImage2D\|texImage3D\|texStorage' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Texture Operations | $tex_count/$total | $((tex_count*100/total))% |"

# 3D Textures
tex3d_count=$(grep -l 'TEXTURE_3D\|texImage3D\|texStorage3D' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| 3D Textures | $tex3d_count/$total | $((tex3d_count*100/total))% |"

# Texture Arrays
texarray_count=$(grep -l 'TEXTURE_2D_ARRAY\|texStorage3D' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Texture Arrays | $texarray_count/$total | $((texarray_count*100/total))% |"

# Framebuffers
fbo_count=$(grep -l 'createFramebuffer\|framebufferTexture2D\|drawBuffers' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Framebuffer Objects | $fbo_count/$total | $((fbo_count*100/total))% |"

# MRT
mrt_count=$(grep -l 'drawBuffers\|COLOR_ATTACHMENT[1-9]' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Multiple Render Targets | $mrt_count/$total | $((mrt_count*100/total))% |"

# Instancing
inst_count=$(grep -l 'drawArraysInstanced\|drawElementsInstanced\|vertexAttribDivisor' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Instanced Rendering | $inst_count/$total | $((inst_count*100/total))% |"

# VAO
vao_count=$(grep -l 'createVertexArray\|bindVertexArray' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Vertex Array Objects | $vao_count/$total | $((vao_count*100/total))% |"

# Sync
sync_count=$(grep -l 'fenceSync\|clientWaitSync\|waitSync' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Sync Objects | $sync_count/$total | $((sync_count*100/total))% |"

# Queries
query_count=$(grep -l 'createQuery\|beginQuery\|endQuery' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Query Objects | $query_count/$total | $((query_count*100/total))% |"

# Samplers
sampler_count=$(grep -l 'createSampler\|bindSampler\|samplerParameter' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Sampler Objects | $sampler_count/$total | $((sampler_count*100/total))% |"

# Integer textures
int_tex_count=$(grep -l 'R32I\|RGBA32I\|R32UI\|RGBA32UI' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Integer Textures | $int_tex_count/$total | $((int_tex_count*100/total))% |"

# Depth/Stencil
depth_count=$(grep -l 'DEPTH_TEST\|STENCIL_TEST\|depthFunc\|stencilOp' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Depth/Stencil Ops | $depth_count/$total | $((depth_count*100/total))% |"

# Blending
blend_count=$(grep -l 'BLEND\|blendFunc\|blendEquation' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Blending | $blend_count/$total | $((blend_count*100/total))% |"

echo ""

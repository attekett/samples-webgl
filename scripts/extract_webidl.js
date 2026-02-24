#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const webidl2 = require('webidl2');

const CACHE_DIR = path.join(__dirname, '.idl_cache');
const OUTPUT_PATH = path.join(__dirname, '..', 'docs', 'webgl_api_surface.json');

// ============================================================
// Tier A: Block comment role mapping (IDL /* RoleName */ comments)
// ============================================================

const ROLE_NAME_MAP = {
  'ClearBufferMask': 'buffer_bit',
  'BeginMode': 'draw_mode',
  'BlendingFactorDest': 'blend_factor',
  'BlendingFactorSrc': 'blend_factor',
  'BlendEquationSeparate': 'blend_equation',
  'BlendEquationMode': 'blend_equation',
  'BlendSubtract': 'blend_equation',
  'Separate Blend Functions': 'blend_parameter',
  'Buffer Objects': 'buffer_object',
  'Buffer objects': 'buffer_object',
  'CullFaceMode': 'cull_face',
  'DepthFunction': 'depth_func',
  'EnableCap': 'capability',
  'ErrorCode': 'error_code',
  'FrontFaceDirection': 'front_face',
  'GetPName': 'get_parameter',
  'GetTextureParameter': 'get_parameter',
  'PixelFormat': 'format',
  'PixelType': 'pixel_type',
  'Shaders': 'shader',
  'StencilFunction': 'stencil_func',
  'StencilOp': 'stencil_op',
  'StringName': 'string_name',
  'TextureMagFilter': 'texture_filter',
  'TextureMinFilter': 'texture_filter',
  'TextureParameterName': 'texture_parameter',
  'TextureTarget': 'texture_target',
  'TextureUnit': 'texture_unit',
  'TextureWrapMode': 'texture_wrap',
  'Uniform Types': 'uniform_type',
  'Vertex Arrays': 'vertex_attrib',
  'Vertex attrib': 'vertex_attrib',
  'VertexArrays': 'vertex_attrib',
  'Read Format': 'read_format',
  'Shader Source': 'shader',
  'Shader Precision-Specified Types': 'shader_precision',
  'Framebuffer Object.': 'framebuffer_object',
  'Framebuffer Object': 'framebuffer_object',
  'WebGL-specific enums': 'webgl_specific',
  'HintMode': 'hint_mode',
  'HintTarget': 'hint_target',
  'DataType': 'data_type',
  'AlphaFunction (not supported in ES20)': null,
};

function extractConstantsWithContext(idlText, webglVersion) {
  const lines = idlText.split('\n');
  let currentRole = 'General';
  const results = [];
  let insideRelevantInterface = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (line.includes('interface mixin WebGLRenderingContextBase') ||
        line.includes('interface mixin WebGL2RenderingContextBase')) {
      insideRelevantInterface = true;
    }
    if (insideRelevantInterface && line === '};') {
      insideRelevantInterface = false;
    }

    if (!insideRelevantInterface) continue;

    const roleMatch = line.match(/^\/\*\s*([^*\/]+?)\s*\*\//);
    if (roleMatch && !line.includes('const')) {
      const potentialRole = roleMatch[1].trim();
      // Filter out noise: back-references to constants (ALL_CAPS), unsupported notes, etc.
      if (!potentialRole.toLowerCase().includes('supported') &&
          !potentialRole.toLowerCase().includes('ideally') &&
          !potentialRole.startsWith('Same as') &&
          !potentialRole.startsWith('same as') &&
          !/^[A-Z][A-Z0-9_]+$/.test(potentialRole)) {
        currentRole = potentialRole;
      }
    }

    const constMatch = line.match(/const\s+(?:GLenum|GLint64)\s+([A-Z0-9_]+)\s*=\s*(-?(?:0x[0-9A-Fa-f]+|[0-9]+))/i);
    if (constMatch) {
      results.push({
        name: constMatch[1],
        value: constMatch[2],
        blockRole: currentRole,
        webgl_version: webglVersion
      });
    }
  }
  return results;
}

function normalizeRole(blockRole) {
  if (ROLE_NAME_MAP.hasOwnProperty(blockRole)) {
    return ROLE_NAME_MAP[blockRole];
  }
  return blockRole
    .replace(/[^a-zA-Z0-9\s]/g, '')
    .trim()
    .replace(/\s+/g, '_')
    .toLowerCase();
}

// ============================================================
// Tier B: Manual mapping table for WebGL2 constants
// ============================================================

const TIER_B_ROLES = {
  'STREAM_READ': ['buffer_usage'], 'STREAM_COPY': ['buffer_usage'],
  'STATIC_READ': ['buffer_usage'], 'STATIC_COPY': ['buffer_usage'],
  'DYNAMIC_READ': ['buffer_usage'], 'DYNAMIC_COPY': ['buffer_usage'],
  'STREAM_DRAW': ['buffer_usage'], 'STATIC_DRAW': ['buffer_usage'], 'DYNAMIC_DRAW': ['buffer_usage'],
  'ARRAY_BUFFER': ['buffer_target'], 'ELEMENT_ARRAY_BUFFER': ['buffer_target'],
  'COPY_READ_BUFFER': ['buffer_target'], 'COPY_WRITE_BUFFER': ['buffer_target'],
  'COPY_READ_BUFFER_BINDING': ['get_parameter'], 'COPY_WRITE_BUFFER_BINDING': ['get_parameter'],
  'PIXEL_PACK_BUFFER': ['buffer_target'], 'PIXEL_UNPACK_BUFFER': ['buffer_target'],
  'PIXEL_PACK_BUFFER_BINDING': ['get_parameter'], 'PIXEL_UNPACK_BUFFER_BINDING': ['get_parameter'],
  'UNIFORM_BUFFER': ['buffer_target'], 'TRANSFORM_FEEDBACK_BUFFER': ['buffer_target'],
  'ARRAY_BUFFER_BINDING': ['get_parameter'], 'ELEMENT_ARRAY_BUFFER_BINDING': ['get_parameter'],
  'BUFFER_SIZE': ['buffer_parameter'], 'BUFFER_USAGE': ['buffer_parameter'],
  'READ_FRAMEBUFFER': ['framebuffer_target'], 'DRAW_FRAMEBUFFER': ['framebuffer_target'],
  'FRAMEBUFFER': ['framebuffer_target'], 'RENDERBUFFER': ['renderbuffer_target'],
  'READ_FRAMEBUFFER_BINDING': ['get_parameter'], 'DRAW_FRAMEBUFFER_BINDING': ['get_parameter'],
  'FRAMEBUFFER_BINDING': ['get_parameter'], 'RENDERBUFFER_BINDING': ['get_parameter'],
  'RENDERBUFFER_SAMPLES': ['get_parameter'],
  'SAMPLER_BINDING': ['get_parameter'],
  'TEXTURE_COMPARE_MODE': ['sampler_parameter', 'texture_parameter'],
  'TEXTURE_COMPARE_FUNC': ['sampler_parameter', 'texture_parameter'],
  'COMPARE_REF_TO_TEXTURE': ['sampler_parameter'],
  'TEXTURE_3D': ['texture_target'], 'TEXTURE_2D_ARRAY': ['texture_target'],
  'TEXTURE_2D': ['texture_target'], 'TEXTURE_CUBE_MAP': ['texture_target'],
  'TEXTURE_BASE_LEVEL': ['texture_parameter'], 'TEXTURE_MAX_LEVEL': ['texture_parameter'],
  'TEXTURE_WRAP_R': ['texture_parameter'],
  'TEXTURE_MIN_LOD': ['texture_parameter'], 'TEXTURE_MAX_LOD': ['texture_parameter'],
  'TEXTURE_IMMUTABLE_FORMAT': ['get_parameter'], 'TEXTURE_IMMUTABLE_LEVELS': ['get_parameter'],
  'TEXTURE_BINDING_3D': ['get_parameter'], 'TEXTURE_BINDING_2D': ['get_parameter'],
  'TEXTURE_BINDING_2D_ARRAY': ['get_parameter'], 'TEXTURE_BINDING_CUBE_MAP': ['get_parameter'],
  'TEXTURE_MAG_FILTER': ['texture_parameter'], 'TEXTURE_MIN_FILTER': ['texture_parameter'],
  'TEXTURE_WRAP_S': ['texture_parameter'], 'TEXTURE_WRAP_T': ['texture_parameter'],
  'UNPACK_ROW_LENGTH': ['pixel_store'], 'UNPACK_SKIP_ROWS': ['pixel_store'],
  'UNPACK_SKIP_PIXELS': ['pixel_store'], 'UNPACK_IMAGE_HEIGHT': ['pixel_store'],
  'UNPACK_SKIP_IMAGES': ['pixel_store'], 'PACK_ROW_LENGTH': ['pixel_store'],
  'PACK_SKIP_ROWS': ['pixel_store'], 'PACK_SKIP_PIXELS': ['pixel_store'],
  'UNPACK_ALIGNMENT': ['pixel_store'], 'PACK_ALIGNMENT': ['pixel_store'],
  'UNPACK_FLIP_Y_WEBGL': ['pixel_store'], 'UNPACK_PREMULTIPLY_ALPHA_WEBGL': ['pixel_store'],
  'UNPACK_COLORSPACE_CONVERSION_WEBGL': ['pixel_store'],
  'R8': ['sized_internalformat'], 'R16F': ['sized_internalformat'], 'R32F': ['sized_internalformat'],
  'R8UI': ['sized_internalformat'], 'R8I': ['sized_internalformat'],
  'R16UI': ['sized_internalformat'], 'R16I': ['sized_internalformat'],
  'R32UI': ['sized_internalformat'], 'R32I': ['sized_internalformat'],
  'RG8': ['sized_internalformat'], 'RG16F': ['sized_internalformat'], 'RG32F': ['sized_internalformat'],
  'RG8UI': ['sized_internalformat'], 'RG8I': ['sized_internalformat'],
  'RG16UI': ['sized_internalformat'], 'RG16I': ['sized_internalformat'],
  'RG32UI': ['sized_internalformat'], 'RG32I': ['sized_internalformat'],
  'RGB8': ['sized_internalformat'], 'SRGB8': ['sized_internalformat'], 'SRGB': ['sized_internalformat'],
  'RGB565': ['sized_internalformat'], 'R11F_G11F_B10F': ['sized_internalformat'],
  'RGB9_E5': ['sized_internalformat'], 'RGB16F': ['sized_internalformat'],
  'RGB32F': ['sized_internalformat'], 'RGB8UI': ['sized_internalformat'],
  'RGB8I': ['sized_internalformat'], 'RGB16UI': ['sized_internalformat'],
  'RGB16I': ['sized_internalformat'], 'RGB32UI': ['sized_internalformat'],
  'RGB32I': ['sized_internalformat'],
  'RGBA8': ['sized_internalformat'], 'SRGB8_ALPHA8': ['sized_internalformat'],
  'RGB5_A1': ['sized_internalformat'], 'RGBA4': ['sized_internalformat'],
  'RGB10_A2': ['sized_internalformat'], 'RGBA16F': ['sized_internalformat'],
  'RGBA32F': ['sized_internalformat'], 'RGBA8UI': ['sized_internalformat'],
  'RGBA8I': ['sized_internalformat'], 'RGB10_A2UI': ['sized_internalformat'],
  'RGBA16UI': ['sized_internalformat'], 'RGBA16I': ['sized_internalformat'],
  'RGBA32UI': ['sized_internalformat'], 'RGBA32I': ['sized_internalformat'],
  'R8_SNORM': ['sized_internalformat'], 'RG8_SNORM': ['sized_internalformat'],
  'RGB8_SNORM': ['sized_internalformat'], 'RGBA8_SNORM': ['sized_internalformat'],
  'DEPTH_COMPONENT16': ['sized_internalformat'], 'DEPTH_COMPONENT24': ['sized_internalformat'],
  'DEPTH_COMPONENT32F': ['sized_internalformat'], 'DEPTH24_STENCIL8': ['sized_internalformat'],
  'DEPTH32F_STENCIL8': ['sized_internalformat'], 'STENCIL_INDEX8': ['sized_internalformat'],
  'HALF_FLOAT': ['pixel_type', 'data_type'], 'INT': ['data_type'], 'UNSIGNED_INT': ['data_type'],
  'BYTE': ['data_type'], 'UNSIGNED_BYTE': ['data_type', 'pixel_type'],
  'SHORT': ['data_type'], 'UNSIGNED_SHORT': ['data_type'],
  'FLOAT': ['data_type', 'pixel_type'],
  'UNSIGNED_INT_2_10_10_10_REV': ['pixel_type'], 'UNSIGNED_INT_10F_11F_11F_REV': ['pixel_type'],
  'UNSIGNED_INT_5_9_9_9_REV': ['pixel_type'], 'UNSIGNED_INT_24_8': ['pixel_type'],
  'FLOAT_32_UNSIGNED_INT_24_8_REV': ['pixel_type'],
  'UNSIGNED_SHORT_4_4_4_4': ['pixel_type'], 'UNSIGNED_SHORT_5_5_5_1': ['pixel_type'],
  'UNSIGNED_SHORT_5_6_5': ['pixel_type'],
  'INT_2_10_10_10_REV': ['pixel_type'],
  'RED': ['format'], 'RG': ['format'], 'RED_INTEGER': ['format'],
  'RG_INTEGER': ['format'], 'RGB_INTEGER': ['format'], 'RGBA_INTEGER': ['format'],
  'RGB': ['format'], 'RGBA': ['format'], 'ALPHA': ['format'],
  'LUMINANCE': ['format'], 'LUMINANCE_ALPHA': ['format'],
  'DEPTH_COMPONENT': ['format'], 'DEPTH_STENCIL': ['format'],
  'TRANSFORM_FEEDBACK': ['transform_feedback'], 'TRANSFORM_FEEDBACK_BINDING': ['get_parameter'],
  'TRANSFORM_FEEDBACK_BUFFER_BINDING': ['get_parameter'],
  'TRANSFORM_FEEDBACK_BUFFER_SIZE': ['get_parameter'],
  'TRANSFORM_FEEDBACK_BUFFER_START': ['get_parameter'],
  'TRANSFORM_FEEDBACK_PAUSED': ['get_parameter'],
  'TRANSFORM_FEEDBACK_ACTIVE': ['get_parameter'],
  'TRANSFORM_FEEDBACK_BUFFER_MODE': ['get_parameter'],
  'TRANSFORM_FEEDBACK_VARYINGS': ['get_parameter'],
  'INTERLEAVED_ATTRIBS': ['transform_feedback_mode'],
  'SEPARATE_ATTRIBS': ['transform_feedback_mode'],
  'RASTERIZER_DISCARD': ['capability'],
  'UNIFORM_BUFFER_BINDING': ['get_parameter'],
  'UNIFORM_BUFFER_START': ['get_parameter'], 'UNIFORM_BUFFER_SIZE': ['get_parameter'],
  'UNIFORM_BUFFER_OFFSET_ALIGNMENT': ['get_parameter'],
  'ACTIVE_UNIFORM_BLOCKS': ['get_parameter'],
  'UNIFORM_BLOCK_BINDING': ['uniform_block'],
  'UNIFORM_BLOCK_DATA_SIZE': ['uniform_block'],
  'UNIFORM_BLOCK_ACTIVE_UNIFORMS': ['uniform_block'],
  'UNIFORM_BLOCK_ACTIVE_UNIFORM_INDICES': ['uniform_block'],
  'UNIFORM_BLOCK_REFERENCED_BY_VERTEX_SHADER': ['uniform_block'],
  'UNIFORM_BLOCK_REFERENCED_BY_FRAGMENT_SHADER': ['uniform_block'],
  'UNIFORM_BLOCK_INDEX': ['uniform_info'],
  'UNIFORM_TYPE': ['uniform_info'], 'UNIFORM_SIZE': ['uniform_info'],
  'UNIFORM_OFFSET': ['uniform_info'], 'UNIFORM_ARRAY_STRIDE': ['uniform_info'],
  'UNIFORM_MATRIX_STRIDE': ['uniform_info'], 'UNIFORM_IS_ROW_MAJOR': ['uniform_info'],
  'ANY_SAMPLES_PASSED': ['query_target'], 'ANY_SAMPLES_PASSED_CONSERVATIVE': ['query_target'],
  'TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN': ['query_target'],
  'CURRENT_QUERY': ['get_parameter'],
  'QUERY_RESULT': ['query_parameter'], 'QUERY_RESULT_AVAILABLE': ['query_parameter'],
  'SYNC_CONDITION': ['sync_parameter'], 'SYNC_STATUS': ['sync_parameter'],
  'SYNC_FLAGS': ['sync_parameter'], 'SYNC_FENCE': ['sync_type'],
  'SYNC_GPU_COMMANDS_COMPLETE': ['sync_condition'],
  'OBJECT_TYPE': ['sync_parameter'],
  'SIGNALED': ['sync_status'], 'UNSIGNALED': ['sync_status'],
  'ALREADY_SIGNALED': ['sync_wait_result'], 'TIMEOUT_EXPIRED': ['sync_wait_result'],
  'CONDITION_SATISFIED': ['sync_wait_result'], 'WAIT_FAILED': ['sync_wait_result'],
  'SYNC_FLUSH_COMMANDS_BIT': ['sync_flag'],
  'VERTEX_ATTRIB_ARRAY_DIVISOR': ['vertex_attrib'],
  'VERTEX_ATTRIB_ARRAY_INTEGER': ['vertex_attrib'],
  'VERTEX_ARRAY_BINDING': ['get_parameter'],
  'VERTEX_ATTRIB_ARRAY_ENABLED': ['vertex_attrib'],
  'VERTEX_ATTRIB_ARRAY_SIZE': ['vertex_attrib'],
  'VERTEX_ATTRIB_ARRAY_STRIDE': ['vertex_attrib'],
  'VERTEX_ATTRIB_ARRAY_TYPE': ['vertex_attrib'],
  'VERTEX_ATTRIB_ARRAY_NORMALIZED': ['vertex_attrib'],
  'VERTEX_ATTRIB_ARRAY_POINTER': ['vertex_attrib'],
  'VERTEX_ATTRIB_ARRAY_BUFFER_BINDING': ['vertex_attrib'],
  'CURRENT_VERTEX_ATTRIB': ['vertex_attrib'],
  'COLOR': ['buffer_type'], 'DEPTH': ['buffer_type'], 'STENCIL': ['buffer_type'],
  'READ_BUFFER': ['get_parameter'],
  'MAX_TEXTURE_LOD_BIAS': ['limit'],
  'FRAGMENT_SHADER_DERIVATIVE_HINT': ['hint_target'],
  'UNSIGNED_NORMALIZED': ['type_info'], 'SIGNED_NORMALIZED': ['type_info'],
  'INVALID_INDEX': ['special'],
  'TIMEOUT_IGNORED': ['special'],
  'FRAMEBUFFER_DEFAULT': ['framebuffer_parameter'],
  'FRAMEBUFFER_ATTACHMENT_COLOR_ENCODING': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_COMPONENT_TYPE': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_RED_SIZE': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_GREEN_SIZE': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_BLUE_SIZE': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_ALPHA_SIZE': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_DEPTH_SIZE': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_STENCIL_SIZE': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_TEXTURE_LAYER': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_OBJECT_TYPE': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_OBJECT_NAME': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_TEXTURE_LEVEL': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_ATTACHMENT_TEXTURE_CUBE_MAP_FACE': ['framebuffer_attachment_parameter'],
  'FRAMEBUFFER_INCOMPLETE_MULTISAMPLE': ['framebuffer_status'],
  'FRAMEBUFFER_COMPLETE': ['framebuffer_status'],
  'FRAMEBUFFER_INCOMPLETE_ATTACHMENT': ['framebuffer_status'],
  'FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT': ['framebuffer_status'],
  'FRAMEBUFFER_INCOMPLETE_DIMENSIONS': ['framebuffer_status'],
  'FRAMEBUFFER_UNSUPPORTED': ['framebuffer_status'],
  'INVALID_FRAMEBUFFER_OPERATION': ['error_code'],
  'COLOR_ATTACHMENT0': ['color_attachment'],
  'COLOR_ATTACHMENT1': ['color_attachment'], 'COLOR_ATTACHMENT2': ['color_attachment'],
  'COLOR_ATTACHMENT3': ['color_attachment'], 'COLOR_ATTACHMENT4': ['color_attachment'],
  'COLOR_ATTACHMENT5': ['color_attachment'], 'COLOR_ATTACHMENT6': ['color_attachment'],
  'COLOR_ATTACHMENT7': ['color_attachment'], 'COLOR_ATTACHMENT8': ['color_attachment'],
  'COLOR_ATTACHMENT9': ['color_attachment'], 'COLOR_ATTACHMENT10': ['color_attachment'],
  'COLOR_ATTACHMENT11': ['color_attachment'], 'COLOR_ATTACHMENT12': ['color_attachment'],
  'COLOR_ATTACHMENT13': ['color_attachment'], 'COLOR_ATTACHMENT14': ['color_attachment'],
  'COLOR_ATTACHMENT15': ['color_attachment'],
  'DEPTH_ATTACHMENT': ['framebuffer_attachment'],
  'STENCIL_ATTACHMENT': ['framebuffer_attachment'],
  'DEPTH_STENCIL_ATTACHMENT': ['framebuffer_attachment'],
  'RENDERBUFFER_WIDTH': ['renderbuffer_parameter'],
  'RENDERBUFFER_HEIGHT': ['renderbuffer_parameter'],
  'RENDERBUFFER_INTERNAL_FORMAT': ['renderbuffer_parameter'],
  'RENDERBUFFER_RED_SIZE': ['renderbuffer_parameter'],
  'RENDERBUFFER_GREEN_SIZE': ['renderbuffer_parameter'],
  'RENDERBUFFER_BLUE_SIZE': ['renderbuffer_parameter'],
  'RENDERBUFFER_ALPHA_SIZE': ['renderbuffer_parameter'],
  'RENDERBUFFER_DEPTH_SIZE': ['renderbuffer_parameter'],
  'RENDERBUFFER_STENCIL_SIZE': ['renderbuffer_parameter'],
  'POINTS': ['draw_mode'], 'LINES': ['draw_mode'], 'LINE_LOOP': ['draw_mode'],
  'LINE_STRIP': ['draw_mode'], 'TRIANGLES': ['draw_mode'],
  'TRIANGLE_STRIP': ['draw_mode'], 'TRIANGLE_FAN': ['draw_mode'],
  'ZERO': ['blend_factor'], 'ONE': ['blend_factor'],
  'SRC_COLOR': ['blend_factor'], 'ONE_MINUS_SRC_COLOR': ['blend_factor'],
  'SRC_ALPHA': ['blend_factor'], 'ONE_MINUS_SRC_ALPHA': ['blend_factor'],
  'DST_ALPHA': ['blend_factor'], 'ONE_MINUS_DST_ALPHA': ['blend_factor'],
  'DST_COLOR': ['blend_factor'], 'ONE_MINUS_DST_COLOR': ['blend_factor'],
  'SRC_ALPHA_SATURATE': ['blend_factor'],
  'CONSTANT_COLOR': ['blend_factor'], 'ONE_MINUS_CONSTANT_COLOR': ['blend_factor'],
  'CONSTANT_ALPHA': ['blend_factor'], 'ONE_MINUS_CONSTANT_ALPHA': ['blend_factor'],
  'FUNC_ADD': ['blend_equation'], 'FUNC_SUBTRACT': ['blend_equation'],
  'FUNC_REVERSE_SUBTRACT': ['blend_equation'],
  'MIN': ['blend_equation'], 'MAX': ['blend_equation'],
  'BLEND_EQUATION': ['get_parameter'], 'BLEND_EQUATION_RGB': ['get_parameter'],
  'BLEND_EQUATION_ALPHA': ['get_parameter'],
  'BLEND_DST_RGB': ['get_parameter'], 'BLEND_SRC_RGB': ['get_parameter'],
  'BLEND_DST_ALPHA': ['get_parameter'], 'BLEND_SRC_ALPHA': ['get_parameter'],
  'BLEND_COLOR': ['get_parameter'],
  'CULL_FACE': ['capability'], 'BLEND': ['capability'], 'DITHER': ['capability'],
  'STENCIL_TEST': ['capability'], 'DEPTH_TEST': ['capability'],
  'SCISSOR_TEST': ['capability'], 'POLYGON_OFFSET_FILL': ['capability'],
  'SAMPLE_ALPHA_TO_COVERAGE': ['capability'], 'SAMPLE_COVERAGE': ['capability'],
  'FRONT': ['cull_face'], 'BACK': ['cull_face'], 'FRONT_AND_BACK': ['cull_face'],
  'CW': ['front_face'], 'CCW': ['front_face'],
  'NO_ERROR': ['error_code'], 'INVALID_ENUM': ['error_code'],
  'INVALID_VALUE': ['error_code'], 'INVALID_OPERATION': ['error_code'],
  'OUT_OF_MEMORY': ['error_code'], 'CONTEXT_LOST_WEBGL': ['error_code'],
  'NEVER': ['comparison_func'], 'LESS': ['comparison_func'],
  'EQUAL': ['comparison_func'], 'LEQUAL': ['comparison_func'],
  'GREATER': ['comparison_func'], 'NOTEQUAL': ['comparison_func'],
  'GEQUAL': ['comparison_func'], 'ALWAYS': ['comparison_func'],
  'KEEP': ['stencil_op'], 'REPLACE': ['stencil_op'],
  'INCR': ['stencil_op'], 'DECR': ['stencil_op'],
  'INVERT': ['stencil_op'], 'INCR_WRAP': ['stencil_op'], 'DECR_WRAP': ['stencil_op'],
  'NEAREST': ['texture_filter'], 'LINEAR': ['texture_filter'],
  'NEAREST_MIPMAP_NEAREST': ['texture_filter'], 'LINEAR_MIPMAP_NEAREST': ['texture_filter'],
  'NEAREST_MIPMAP_LINEAR': ['texture_filter'], 'LINEAR_MIPMAP_LINEAR': ['texture_filter'],
  'REPEAT': ['texture_wrap'], 'CLAMP_TO_EDGE': ['texture_wrap'],
  'MIRRORED_REPEAT': ['texture_wrap'],
  'FRAGMENT_SHADER': ['shader_type'], 'VERTEX_SHADER': ['shader_type'],
  'COMPILE_STATUS': ['shader_parameter'], 'DELETE_STATUS': ['shader_parameter'],
  'LINK_STATUS': ['program_parameter'], 'VALIDATE_STATUS': ['program_parameter'],
  'ATTACHED_SHADERS': ['program_parameter'], 'ACTIVE_UNIFORMS': ['program_parameter'],
  'ACTIVE_ATTRIBUTES': ['program_parameter'],
  'SHADER_TYPE': ['shader_parameter'],
  'SHADING_LANGUAGE_VERSION': ['string_name'], 'CURRENT_PROGRAM': ['get_parameter'],
  'VENDOR': ['string_name'], 'RENDERER': ['string_name'], 'VERSION': ['string_name'],
  'NONE': ['special'],
  'DONT_CARE': ['hint_mode'], 'FASTEST': ['hint_mode'], 'NICEST': ['hint_mode'],
  'GENERATE_MIPMAP_HINT': ['hint_target'],
  'IMPLEMENTATION_COLOR_READ_TYPE': ['get_parameter'],
  'IMPLEMENTATION_COLOR_READ_FORMAT': ['get_parameter'],
  'LOW_FLOAT': ['shader_precision'], 'MEDIUM_FLOAT': ['shader_precision'],
  'HIGH_FLOAT': ['shader_precision'], 'LOW_INT': ['shader_precision'],
  'MEDIUM_INT': ['shader_precision'], 'HIGH_INT': ['shader_precision'],
  'COMPRESSED_TEXTURE_FORMATS': ['get_parameter'],
  'FLOAT_VEC2': ['uniform_type'], 'FLOAT_VEC3': ['uniform_type'], 'FLOAT_VEC4': ['uniform_type'],
  'INT_VEC2': ['uniform_type'], 'INT_VEC3': ['uniform_type'], 'INT_VEC4': ['uniform_type'],
  'BOOL': ['uniform_type'], 'BOOL_VEC2': ['uniform_type'],
  'BOOL_VEC3': ['uniform_type'], 'BOOL_VEC4': ['uniform_type'],
  'FLOAT_MAT2': ['uniform_type'], 'FLOAT_MAT3': ['uniform_type'], 'FLOAT_MAT4': ['uniform_type'],
  'FLOAT_MAT2x3': ['uniform_type'], 'FLOAT_MAT2x4': ['uniform_type'],
  'FLOAT_MAT3x2': ['uniform_type'], 'FLOAT_MAT3x4': ['uniform_type'],
  'FLOAT_MAT4x2': ['uniform_type'], 'FLOAT_MAT4x3': ['uniform_type'],
  'SAMPLER_2D': ['uniform_type'], 'SAMPLER_CUBE': ['uniform_type'],
  'SAMPLER_3D': ['uniform_type'], 'SAMPLER_2D_SHADOW': ['uniform_type'],
  'SAMPLER_2D_ARRAY': ['uniform_type'], 'SAMPLER_2D_ARRAY_SHADOW': ['uniform_type'],
  'SAMPLER_CUBE_SHADOW': ['uniform_type'],
  'INT_SAMPLER_2D': ['uniform_type'], 'INT_SAMPLER_3D': ['uniform_type'],
  'INT_SAMPLER_CUBE': ['uniform_type'], 'INT_SAMPLER_2D_ARRAY': ['uniform_type'],
  'UNSIGNED_INT_SAMPLER_2D': ['uniform_type'], 'UNSIGNED_INT_SAMPLER_3D': ['uniform_type'],
  'UNSIGNED_INT_SAMPLER_CUBE': ['uniform_type'], 'UNSIGNED_INT_SAMPLER_2D_ARRAY': ['uniform_type'],
  'UNSIGNED_INT_VEC2': ['uniform_type'], 'UNSIGNED_INT_VEC3': ['uniform_type'],
  'UNSIGNED_INT_VEC4': ['uniform_type'],
  'TEXTURE': ['texture_target'],
  'TEXTURE_CUBE_MAP_POSITIVE_X': ['texture_target'], 'TEXTURE_CUBE_MAP_NEGATIVE_X': ['texture_target'],
  'TEXTURE_CUBE_MAP_POSITIVE_Y': ['texture_target'], 'TEXTURE_CUBE_MAP_NEGATIVE_Y': ['texture_target'],
  'TEXTURE_CUBE_MAP_POSITIVE_Z': ['texture_target'], 'TEXTURE_CUBE_MAP_NEGATIVE_Z': ['texture_target'],
  'ACTIVE_TEXTURE': ['get_parameter'],
  'BROWSER_DEFAULT_WEBGL': ['webgl_specific'],
  'MAX_CLIENT_WAIT_TIMEOUT_WEBGL': ['limit'],
  'MAX_DRAW_BUFFERS': ['limit'], 'MAX_COLOR_ATTACHMENTS': ['limit'],
  'MAX_3D_TEXTURE_SIZE': ['limit'], 'MAX_ARRAY_TEXTURE_LAYERS': ['limit'],
  'MAX_TRANSFORM_FEEDBACK_SEPARATE_ATTRIBS': ['limit'],
  'MAX_TRANSFORM_FEEDBACK_INTERLEAVED_COMPONENTS': ['limit'],
  'MAX_TRANSFORM_FEEDBACK_SEPARATE_COMPONENTS': ['limit'],
  'MAX_UNIFORM_BUFFER_BINDINGS': ['limit'], 'MAX_UNIFORM_BLOCK_SIZE': ['limit'],
  'MAX_COMBINED_UNIFORM_BLOCKS': ['limit'],
  'MAX_VERTEX_UNIFORM_BLOCKS': ['limit'], 'MAX_FRAGMENT_UNIFORM_BLOCKS': ['limit'],
  'MAX_COMBINED_VERTEX_UNIFORM_COMPONENTS': ['limit'],
  'MAX_COMBINED_FRAGMENT_UNIFORM_COMPONENTS': ['limit'],
  'MAX_VERTEX_OUTPUT_COMPONENTS': ['limit'], 'MAX_FRAGMENT_INPUT_COMPONENTS': ['limit'],
  'MAX_SERVER_WAIT_TIMEOUT': ['limit'], 'MAX_ELEMENT_INDEX': ['limit'],
  'MAX_SAMPLES': ['limit'], 'MAX_ELEMENTS_VERTICES': ['limit'],
  'MAX_ELEMENTS_INDICES': ['limit'], 'MIN_PROGRAM_TEXEL_OFFSET': ['limit'],
  'MAX_PROGRAM_TEXEL_OFFSET': ['limit'], 'MAX_VARYING_COMPONENTS': ['limit'],
  'MAX_TEXTURE_SIZE': ['limit'], 'MAX_VIEWPORT_DIMS': ['limit'],
  'MAX_CUBE_MAP_TEXTURE_SIZE': ['limit'], 'MAX_RENDERBUFFER_SIZE': ['limit'],
  'MAX_VERTEX_ATTRIBS': ['limit'], 'MAX_VERTEX_UNIFORM_VECTORS': ['limit'],
  'MAX_VARYING_VECTORS': ['limit'], 'MAX_COMBINED_TEXTURE_IMAGE_UNITS': ['limit'],
  'MAX_VERTEX_TEXTURE_IMAGE_UNITS': ['limit'], 'MAX_TEXTURE_IMAGE_UNITS': ['limit'],
  'MAX_FRAGMENT_UNIFORM_VECTORS': ['limit'], 'MAX_VERTEX_UNIFORM_COMPONENTS': ['limit'],
  'MAX_FRAGMENT_UNIFORM_COMPONENTS': ['limit'], 'MAX_TEXTURE_LOD_BIAS': ['limit'],
  'LINE_WIDTH': ['get_parameter'], 'ALIASED_POINT_SIZE_RANGE': ['get_parameter'],
  'ALIASED_LINE_WIDTH_RANGE': ['get_parameter'], 'CULL_FACE_MODE': ['get_parameter'],
  'FRONT_FACE': ['get_parameter'], 'DEPTH_RANGE': ['get_parameter'],
  'DEPTH_WRITEMASK': ['get_parameter'], 'DEPTH_CLEAR_VALUE': ['get_parameter'],
  'DEPTH_FUNC': ['get_parameter'], 'STENCIL_CLEAR_VALUE': ['get_parameter'],
  'STENCIL_FUNC': ['get_parameter'], 'STENCIL_FAIL': ['get_parameter'],
  'STENCIL_PASS_DEPTH_FAIL': ['get_parameter'], 'STENCIL_PASS_DEPTH_PASS': ['get_parameter'],
  'STENCIL_REF': ['get_parameter'], 'STENCIL_VALUE_MASK': ['get_parameter'],
  'STENCIL_WRITEMASK': ['get_parameter'],
  'STENCIL_BACK_FUNC': ['get_parameter'], 'STENCIL_BACK_FAIL': ['get_parameter'],
  'STENCIL_BACK_PASS_DEPTH_FAIL': ['get_parameter'],
  'STENCIL_BACK_PASS_DEPTH_PASS': ['get_parameter'],
  'STENCIL_BACK_REF': ['get_parameter'], 'STENCIL_BACK_VALUE_MASK': ['get_parameter'],
  'STENCIL_BACK_WRITEMASK': ['get_parameter'],
  'VIEWPORT': ['get_parameter'], 'SCISSOR_BOX': ['get_parameter'],
  'COLOR_CLEAR_VALUE': ['get_parameter'], 'COLOR_WRITEMASK': ['get_parameter'],
  'SUBPIXEL_BITS': ['get_parameter'], 'RED_BITS': ['get_parameter'],
  'GREEN_BITS': ['get_parameter'], 'BLUE_BITS': ['get_parameter'],
  'ALPHA_BITS': ['get_parameter'], 'DEPTH_BITS': ['get_parameter'],
  'STENCIL_BITS': ['get_parameter'], 'POLYGON_OFFSET_UNITS': ['get_parameter'],
  'POLYGON_OFFSET_FACTOR': ['get_parameter'],
  'SAMPLE_BUFFERS': ['get_parameter'], 'SAMPLES': ['get_parameter'],
  'SAMPLE_COVERAGE_VALUE': ['get_parameter'], 'SAMPLE_COVERAGE_INVERT': ['get_parameter'],
};

// ============================================================
// Tier C: Heuristic role detection
// ============================================================

function isPowerOfTwo(n) {
  return n > 0 && (n & (n - 1)) === 0;
}

function tierC(name, value) {
  const roles = [];
  const numVal = parseInt(value);

  if (name.endsWith('_BIT') && isPowerOfTwo(numVal)) {
    roles.push('bitmask');
  }
  if (/^(R|RG|RGB|RGBA)\d/.test(name) || name.includes('SRGB')) {
    roles.push('sized_internalformat');
  }
  if (name.startsWith('INVALID_')) {
    roles.push('error_code');
  }
  if (name.startsWith('PACK_') || name.startsWith('UNPACK_')) {
    roles.push('pixel_store');
  }
  if (name.startsWith('MAX_') || name.startsWith('MIN_')) {
    roles.push('limit');
  }
  if (name.startsWith('DRAW_BUFFER') && /\d+$/.test(name)) {
    roles.push('draw_buffer');
  }
  if (name.startsWith('COLOR_ATTACHMENT') && /\d+$/.test(name)) {
    roles.push('color_attachment');
  }
  if (name.startsWith('TEXTURE') && /^\d+$/.test(name.replace('TEXTURE', ''))) {
    roles.push('texture_unit');
  }
  return roles;
}

// ============================================================
// Kind classification
// ============================================================

function classifyKind(name, value) {
  const numVal = parseInt(value);
  if (name.endsWith('_BIT') && isPowerOfTwo(numVal)) {
    return 'bitmask';
  }
  return 'enum';
}

// ============================================================
// Method extraction using webidl2
// ============================================================

const WEBGL1_INTERFACES = new Set([
  'WebGLRenderingContextBase',
  'WebGLRenderingContextOverloads'
]);

const WEBGL2_INTERFACES = new Set([
  'WebGL2RenderingContextBase',
  'WebGL2RenderingContextOverloads'
]);

function stripAnnotations(typeStr) {
  return typeStr
    .replace(/\[AllowShared\]\s*/g, '')
    .replace(/\[WebGLHandlesContextLoss\]\s*/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function extractIdlType(idlType) {
  if (!idlType) return 'void';
  if (typeof idlType === 'string') return idlType;
  if (idlType.idlType) {
    if (Array.isArray(idlType.idlType)) {
      return idlType.idlType.map(t => extractIdlType(t)).join(' or ');
    }
    if (typeof idlType.idlType === 'string') {
      let base = idlType.idlType;
      if (idlType.nullable) base += '?';
      return base;
    }
    return extractIdlType(idlType.idlType);
  }
  if (idlType.generic) {
    const inner = extractIdlType(idlType.idlType);
    return `${idlType.generic}<${inner}>`;
  }
  return 'any';
}

function extractMethods(parsedIdl, webglVersion) {
  const methods = {};

  for (const def of parsedIdl) {
    let interfaceName = null;

    if (def.type === 'interface mixin' || def.type === 'interface') {
      interfaceName = def.name;
    }

    if (!interfaceName) continue;

    let version;
    if (WEBGL1_INTERFACES.has(interfaceName)) {
      version = 1;
    } else if (WEBGL2_INTERFACES.has(interfaceName)) {
      version = 2;
    } else {
      continue;
    }

    if (webglVersion && version !== webglVersion) continue;

    if (!def.members) continue;

    for (const member of def.members) {
      if (member.type !== 'operation' || !member.name) continue;

      const methodName = member.name;
      const params = (member.arguments || []).map(arg => ({
        name: arg.name,
        type: stripAnnotations(extractIdlType(arg.idlType)),
        optional: arg.optional || false
      }));

      const requiredParams = params.filter(p => !p.optional);
      const arity = requiredParams.length;

      const overload = {
        arity: arity,
        params: params.map(p => {
          const entry = { name: p.name, type: p.type };
          if (p.optional) entry.optional = true;
          return entry;
        })
      };

      if (!methods[methodName]) {
        methods[methodName] = { webgl_version: version, overloads: [] };
      }

      const isDuplicate = methods[methodName].overloads.some(existing => {
        if (existing.params.length !== overload.params.length) return false;
        return existing.params.every((p, i) => p.type === overload.params[i].type);
      });

      if (!isDuplicate) {
        methods[methodName].overloads.push(overload);
      }

      if (version < methods[methodName].webgl_version) {
        methods[methodName].webgl_version = version;
      }
    }
  }

  return methods;
}

// ============================================================
// Extension definitions (hardcoded from MDN/Khronos)
// ============================================================

const EXTENSIONS = {
  'OES_vertex_array_object': {
    methods: {
      'createVertexArrayOES': { overloads: [{ arity: 0, params: [] }] },
      'deleteVertexArrayOES': { overloads: [{ arity: 1, params: [{ name: 'arrayObject', type: 'WebGLVertexArrayObjectOES?' }] }] },
      'isVertexArrayOES': { overloads: [{ arity: 1, params: [{ name: 'arrayObject', type: 'WebGLVertexArrayObjectOES?' }] }] },
      'bindVertexArrayOES': { overloads: [{ arity: 1, params: [{ name: 'arrayObject', type: 'WebGLVertexArrayObjectOES?' }] }] }
    },
    constants: {
      'VERTEX_ARRAY_BINDING_OES': { value: '0x85B5', kind: 'enum', roles: ['get_parameter'] }
    }
  },
  'OES_standard_derivatives': {
    methods: {},
    constants: {
      'FRAGMENT_SHADER_DERIVATIVE_HINT_OES': { value: '0x8B8B', kind: 'enum', roles: ['hint_target'] }
    }
  },
  'OES_element_index_uint': {
    methods: {},
    constants: {}
  },
  'OES_texture_float': {
    methods: {},
    constants: {}
  },
  'OES_texture_half_float': {
    methods: {},
    constants: {
      'HALF_FLOAT_OES': { value: '0x8D61', kind: 'enum', roles: ['pixel_type'] }
    }
  },
  'OES_texture_float_linear': {
    methods: {},
    constants: {}
  },
  'OES_texture_half_float_linear': {
    methods: {},
    constants: {}
  },
  'OES_fbo_render_mipmap': {
    methods: {},
    constants: {}
  },
  'EXT_color_buffer_float': {
    methods: {},
    constants: {}
  },
  'EXT_color_buffer_half_float': {
    methods: {},
    constants: {
      'RGBA16F_EXT': { value: '0x881A', kind: 'enum', roles: ['sized_internalformat'] },
      'RGB16F_EXT': { value: '0x881B', kind: 'enum', roles: ['sized_internalformat'] },
      'FRAMEBUFFER_ATTACHMENT_COMPONENT_TYPE_EXT': { value: '0x8211', kind: 'enum', roles: ['framebuffer_attachment_parameter'] },
      'UNSIGNED_NORMALIZED_EXT': { value: '0x8C17', kind: 'enum', roles: ['type_info'] }
    }
  },
  'EXT_disjoint_timer_query_webgl2': {
    methods: {
      'queryCounterEXT': { overloads: [{ arity: 2, params: [{ name: 'query', type: 'WebGLQuery' }, { name: 'target', type: 'GLenum' }] }] }
    },
    constants: {
      'QUERY_COUNTER_BITS_EXT': { value: '0x8864', kind: 'enum', roles: ['query_parameter'] },
      'TIME_ELAPSED_EXT': { value: '0x88BF', kind: 'enum', roles: ['query_target'] },
      'TIMESTAMP_EXT': { value: '0x8E28', kind: 'enum', roles: ['query_target'] },
      'GPU_DISJOINT_EXT': { value: '0x8FBB', kind: 'enum', roles: ['get_parameter'] }
    }
  },
  'EXT_texture_filter_anisotropic': {
    methods: {},
    constants: {
      'TEXTURE_MAX_ANISOTROPY_EXT': { value: '0x84FE', kind: 'enum', roles: ['texture_parameter'] },
      'MAX_TEXTURE_MAX_ANISOTROPY_EXT': { value: '0x84FF', kind: 'enum', roles: ['limit'] }
    }
  },
  'EXT_float_blend': {
    methods: {},
    constants: {}
  },
  'EXT_shader_texture_lod': {
    methods: {},
    constants: {}
  },
  'EXT_sRGB': {
    methods: {},
    constants: {
      'SRGB_EXT': { value: '0x8C40', kind: 'enum', roles: ['format'] },
      'SRGB_ALPHA_EXT': { value: '0x8C42', kind: 'enum', roles: ['format'] },
      'SRGB8_ALPHA8_EXT': { value: '0x8C43', kind: 'enum', roles: ['sized_internalformat'] },
      'FRAMEBUFFER_ATTACHMENT_COLOR_ENCODING_EXT': { value: '0x8210', kind: 'enum', roles: ['framebuffer_attachment_parameter'] }
    }
  },
  'WEBGL_color_buffer_float': {
    methods: {},
    constants: {
      'RGBA32F_EXT': { value: '0x8814', kind: 'enum', roles: ['sized_internalformat'] },
      'FRAMEBUFFER_ATTACHMENT_COMPONENT_TYPE_EXT': { value: '0x8211', kind: 'enum', roles: ['framebuffer_attachment_parameter'] },
      'UNSIGNED_NORMALIZED_EXT': { value: '0x8C17', kind: 'enum', roles: ['type_info'] }
    }
  },
  'WEBGL_debug_renderer_info': {
    methods: {},
    constants: {
      'UNMASKED_VENDOR_WEBGL': { value: '0x9245', kind: 'enum', roles: ['get_parameter'] },
      'UNMASKED_RENDERER_WEBGL': { value: '0x9246', kind: 'enum', roles: ['get_parameter'] }
    }
  },
  'WEBGL_compressed_texture_s3tc': {
    methods: {},
    constants: {
      'COMPRESSED_RGB_S3TC_DXT1_EXT': { value: '0x83F0', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_RGBA_S3TC_DXT1_EXT': { value: '0x83F1', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_RGBA_S3TC_DXT3_EXT': { value: '0x83F2', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_RGBA_S3TC_DXT5_EXT': { value: '0x83F3', kind: 'enum', roles: ['compressed_format'] }
    }
  },
  'WEBGL_compressed_texture_s3tc_srgb': {
    methods: {},
    constants: {
      'COMPRESSED_SRGB_S3TC_DXT1_EXT': { value: '0x8C4C', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT': { value: '0x8C4D', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT': { value: '0x8C4E', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT': { value: '0x8C4F', kind: 'enum', roles: ['compressed_format'] }
    }
  },
  'WEBGL_compressed_texture_etc': {
    methods: {},
    constants: {
      'COMPRESSED_R11_EAC': { value: '0x9270', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_SIGNED_R11_EAC': { value: '0x9271', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_RG11_EAC': { value: '0x9272', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_SIGNED_RG11_EAC': { value: '0x9273', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_RGB8_ETC2': { value: '0x9274', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_SRGB8_ETC2': { value: '0x9275', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_RGB8_PUNCHTHROUGH_ALPHA1_ETC2': { value: '0x9276', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_SRGB8_PUNCHTHROUGH_ALPHA1_ETC2': { value: '0x9277', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_RGBA8_ETC2_EAC': { value: '0x9278', kind: 'enum', roles: ['compressed_format'] },
      'COMPRESSED_SRGB8_ALPHA8_ETC2_EAC': { value: '0x9279', kind: 'enum', roles: ['compressed_format'] }
    }
  },
  'WEBGL_depth_texture': {
    methods: {},
    constants: {
      'UNSIGNED_INT_24_8_WEBGL': { value: '0x84FA', kind: 'enum', roles: ['pixel_type'] }
    }
  },
  'WEBGL_draw_buffers': {
    methods: {
      'drawBuffersWEBGL': { overloads: [{ arity: 1, params: [{ name: 'buffers', type: 'sequence<GLenum>' }] }] }
    },
    constants: {
      'COLOR_ATTACHMENT0_WEBGL': { value: '0x8CE0', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT1_WEBGL': { value: '0x8CE1', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT2_WEBGL': { value: '0x8CE2', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT3_WEBGL': { value: '0x8CE3', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT4_WEBGL': { value: '0x8CE4', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT5_WEBGL': { value: '0x8CE5', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT6_WEBGL': { value: '0x8CE6', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT7_WEBGL': { value: '0x8CE7', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT8_WEBGL': { value: '0x8CE8', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT9_WEBGL': { value: '0x8CE9', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT10_WEBGL': { value: '0x8CEA', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT11_WEBGL': { value: '0x8CEB', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT12_WEBGL': { value: '0x8CEC', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT13_WEBGL': { value: '0x8CED', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT14_WEBGL': { value: '0x8CEE', kind: 'enum', roles: ['color_attachment'] },
      'COLOR_ATTACHMENT15_WEBGL': { value: '0x8CEF', kind: 'enum', roles: ['color_attachment'] },
      'DRAW_BUFFER0_WEBGL': { value: '0x8825', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER1_WEBGL': { value: '0x8826', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER2_WEBGL': { value: '0x8827', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER3_WEBGL': { value: '0x8828', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER4_WEBGL': { value: '0x8829', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER5_WEBGL': { value: '0x882A', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER6_WEBGL': { value: '0x882B', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER7_WEBGL': { value: '0x882C', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER8_WEBGL': { value: '0x882D', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER9_WEBGL': { value: '0x882E', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER10_WEBGL': { value: '0x882F', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER11_WEBGL': { value: '0x8830', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER12_WEBGL': { value: '0x8831', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER13_WEBGL': { value: '0x8832', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER14_WEBGL': { value: '0x8833', kind: 'enum', roles: ['draw_buffer'] },
      'DRAW_BUFFER15_WEBGL': { value: '0x8834', kind: 'enum', roles: ['draw_buffer'] },
      'MAX_COLOR_ATTACHMENTS_WEBGL': { value: '0x8CDF', kind: 'enum', roles: ['limit'] },
      'MAX_DRAW_BUFFERS_WEBGL': { value: '0x8824', kind: 'enum', roles: ['limit'] }
    }
  },
  'WEBGL_lose_context': {
    methods: {
      'loseContext': { overloads: [{ arity: 0, params: [] }] },
      'restoreContext': { overloads: [{ arity: 0, params: [] }] }
    },
    constants: {}
  },
  'WEBGL_debug_shaders': {
    methods: {
      'getTranslatedShaderSource': { overloads: [{ arity: 1, params: [{ name: 'shader', type: 'WebGLShader' }] }] }
    },
    constants: {}
  },
  'WEBGL_multi_draw': {
    methods: {
      'multiDrawArraysWEBGL': { overloads: [{ arity: 5, params: [
        { name: 'mode', type: 'GLenum' },
        { name: 'firstsList', type: 'Int32Array or sequence<GLint>' },
        { name: 'firstsOffset', type: 'GLuint' },
        { name: 'countsList', type: 'Int32Array or sequence<GLsizei>' },
        { name: 'countsOffset', type: 'GLuint' },
        { name: 'drawcount', type: 'GLsizei' }
      ] }] },
      'multiDrawElementsWEBGL': { overloads: [{ arity: 6, params: [
        { name: 'mode', type: 'GLenum' },
        { name: 'countsList', type: 'Int32Array or sequence<GLsizei>' },
        { name: 'countsOffset', type: 'GLuint' },
        { name: 'type', type: 'GLenum' },
        { name: 'offsetsList', type: 'Int32Array or sequence<GLsizei>' },
        { name: 'offsetsOffset', type: 'GLuint' },
        { name: 'drawcount', type: 'GLsizei' }
      ] }] },
      'multiDrawArraysInstancedWEBGL': { overloads: [{ arity: 7, params: [
        { name: 'mode', type: 'GLenum' },
        { name: 'firstsList', type: 'Int32Array or sequence<GLint>' },
        { name: 'firstsOffset', type: 'GLuint' },
        { name: 'countsList', type: 'Int32Array or sequence<GLsizei>' },
        { name: 'countsOffset', type: 'GLuint' },
        { name: 'instanceCountsList', type: 'Int32Array or sequence<GLsizei>' },
        { name: 'instanceCountsOffset', type: 'GLuint' },
        { name: 'drawcount', type: 'GLsizei' }
      ] }] },
      'multiDrawElementsInstancedWEBGL': { overloads: [{ arity: 8, params: [
        { name: 'mode', type: 'GLenum' },
        { name: 'countsList', type: 'Int32Array or sequence<GLsizei>' },
        { name: 'countsOffset', type: 'GLuint' },
        { name: 'type', type: 'GLenum' },
        { name: 'offsetsList', type: 'Int32Array or sequence<GLsizei>' },
        { name: 'offsetsOffset', type: 'GLuint' },
        { name: 'instanceCountsList', type: 'Int32Array or sequence<GLsizei>' },
        { name: 'instanceCountsOffset', type: 'GLuint' },
        { name: 'drawcount', type: 'GLsizei' }
      ] }] }
    },
    constants: {}
  },
  'OES_draw_buffers_indexed': {
    methods: {
      'enableiOES': { overloads: [{ arity: 2, params: [{ name: 'target', type: 'GLenum' }, { name: 'index', type: 'GLuint' }] }] },
      'disableiOES': { overloads: [{ arity: 2, params: [{ name: 'target', type: 'GLenum' }, { name: 'index', type: 'GLuint' }] }] },
      'blendEquationiOES': { overloads: [{ arity: 2, params: [{ name: 'buf', type: 'GLuint' }, { name: 'mode', type: 'GLenum' }] }] },
      'blendEquationSeparateiOES': { overloads: [{ arity: 3, params: [{ name: 'buf', type: 'GLuint' }, { name: 'modeRGB', type: 'GLenum' }, { name: 'modeAlpha', type: 'GLenum' }] }] },
      'blendFunciOES': { overloads: [{ arity: 3, params: [{ name: 'buf', type: 'GLuint' }, { name: 'src', type: 'GLenum' }, { name: 'dst', type: 'GLenum' }] }] },
      'blendFuncSeparateiOES': { overloads: [{ arity: 5, params: [{ name: 'buf', type: 'GLuint' }, { name: 'srcRGB', type: 'GLenum' }, { name: 'dstRGB', type: 'GLenum' }, { name: 'srcAlpha', type: 'GLenum' }, { name: 'dstAlpha', type: 'GLenum' }] }] },
      'colorMaskiOES': { overloads: [{ arity: 5, params: [{ name: 'buf', type: 'GLuint' }, { name: 'r', type: 'GLboolean' }, { name: 'g', type: 'GLboolean' }, { name: 'b', type: 'GLboolean' }, { name: 'a', type: 'GLboolean' }] }] }
    },
    constants: {}
  },
  'EXT_texture_norm16': {
    methods: {},
    constants: {
      'R16_EXT': { value: '0x822A', kind: 'enum', roles: ['sized_internalformat'] },
      'RG16_EXT': { value: '0x822C', kind: 'enum', roles: ['sized_internalformat'] },
      'RGB16_EXT': { value: '0x8054', kind: 'enum', roles: ['sized_internalformat'] },
      'RGBA16_EXT': { value: '0x805B', kind: 'enum', roles: ['sized_internalformat'] },
      'R16_SNORM_EXT': { value: '0x8F98', kind: 'enum', roles: ['sized_internalformat'] },
      'RG16_SNORM_EXT': { value: '0x8F99', kind: 'enum', roles: ['sized_internalformat'] },
      'RGB16_SNORM_EXT': { value: '0x8F9A', kind: 'enum', roles: ['sized_internalformat'] },
      'RGBA16_SNORM_EXT': { value: '0x8F9B', kind: 'enum', roles: ['sized_internalformat'] }
    }
  },
  'KHR_parallel_shader_compile': {
    methods: {},
    constants: {
      'COMPLETION_STATUS_KHR': { value: '0x91B1', kind: 'enum', roles: ['shader_parameter'] }
    }
  }
};

// ============================================================
// GLSL builtins (ESSL 3.00)
// ============================================================

const GLSL_BUILTINS = {
  texture_sampling: [
    'texture', 'textureLod', 'textureGrad', 'textureProj',
    'textureProjLod', 'textureProjGrad', 'textureOffset',
    'texelFetch', 'texelFetchOffset', 'textureGradOffset',
    'textureProjOffset', 'textureProjGradOffset', 'textureProjLodOffset',
    'textureSize', 'textureLodOffset'
  ],
  pack_unpack: [
    'packSnorm2x16', 'unpackSnorm2x16',
    'packUnorm2x16', 'unpackUnorm2x16',
    'packHalf2x16', 'unpackHalf2x16'
  ],
  fragment_processing: ['dFdx', 'dFdy', 'fwidth'],
  integer_functions: [
    'floatBitsToInt', 'floatBitsToUint',
    'intBitsToFloat', 'uintBitsToFloat'
  ],
  matrix_functions: ['transpose', 'determinant', 'inverse', 'outerProduct'],
  common_math: [
    'round', 'roundEven', 'trunc', 'isnan', 'isinf',
    'modf', 'frexp', 'ldexp',
    'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh'
  ]
};

// ============================================================
// Main extraction
// ============================================================

function run() {
  const w1Path = path.join(CACHE_DIR, 'webgl1.idl');
  const w2Path = path.join(CACHE_DIR, 'webgl2.idl');

  const w1Text = fs.readFileSync(w1Path, 'utf8');
  const w2Text = fs.readFileSync(w2Path, 'utf8');

  const w1Hash = crypto.createHash('sha256').update(w1Text).digest('hex');
  const w2Hash = crypto.createHash('sha256').update(w2Text).digest('hex');

  // --- Constant extraction ---
  const constants1 = extractConstantsWithContext(w1Text, 1);
  const constants2 = extractConstantsWithContext(w2Text, 2);

  const allConstants = {};
  const warnings = [];

  for (const c of [...constants1, ...constants2]) {
    if (allConstants[c.name]) continue;

    const roles = new Set();

    // Tier A: block comment scraping
    if (c.blockRole && c.blockRole !== 'General') {
      const normalized = normalizeRole(c.blockRole);
      if (normalized) {
        roles.add(normalized);
      }
    }

    // Tier B: manual mapping
    if (TIER_B_ROLES[c.name]) {
      for (const r of TIER_B_ROLES[c.name]) {
        roles.add(r);
      }
    }

    // Tier C: heuristics
    const heurRoles = tierC(c.name, c.value);
    for (const r of heurRoles) {
      roles.add(r);
    }

    if (roles.size === 0) {
      warnings.push(`Unclassified constant: ${c.name} = ${c.value} (block: ${c.blockRole})`);
    }

    allConstants[c.name] = {
      value: c.value,
      kind: classifyKind(c.name, c.value),
      roles: [...roles].sort(),
      webgl_version: c.webgl_version
    };
  }

  // --- Method extraction ---
  // Parse IDL with webidl2 - strip comments first
  function stripComments(text) {
    return text
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/\/\/.*$/gm, '');
  }

  let parsed1, parsed2;
  try {
    parsed1 = webidl2.parse(stripComments(w1Text));
  } catch (e) {
    console.error('Failed to parse webgl1.idl:', e.message);
    process.exit(1);
  }
  try {
    parsed2 = webidl2.parse(stripComments(w2Text));
  } catch (e) {
    console.error('Failed to parse webgl2.idl:', e.message);
    process.exit(1);
  }

  const methods1 = extractMethods(parsed1, null);
  const methods2 = extractMethods(parsed2, null);

  const allMethods = {};

  for (const [name, data] of Object.entries(methods1)) {
    allMethods[name] = data;
  }

  for (const [name, data] of Object.entries(methods2)) {
    if (!allMethods[name]) {
      allMethods[name] = data;
    } else {
      for (const overload of data.overloads) {
        const isDuplicate = allMethods[name].overloads.some(existing => {
          if (existing.params.length !== overload.params.length) return false;
          return existing.params.every((p, i) => p.type === overload.params[i].type);
        });
        if (!isDuplicate) {
          allMethods[name].overloads.push(overload);
        }
      }
    }
  }

  // --- Build output ---
  const output = {
    meta: {
      sources: [
        { name: 'webgl1.idl', sha256: w1Hash },
        { name: 'webgl2.idl', sha256: w2Hash }
      ],
      schema_version: '3.0',
      extracted_at: new Date().toISOString()
    },
    constants: allConstants,
    methods: allMethods,
    extensions: EXTENSIONS,
    glsl_builtins: GLSL_BUILTINS
  };

  // --- Write output ---
  const outputDir = path.dirname(OUTPUT_PATH);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2) + '\n');

  // --- Summary stats ---
  const constantCount = Object.keys(allConstants).length;
  const methodCount = Object.keys(allMethods).length;
  const extensionCount = Object.keys(EXTENSIONS).length;
  const totalOverloads = Object.values(allMethods).reduce((sum, m) => sum + m.overloads.length, 0);

  console.log('=== WebGL API Surface Extraction ===');
  console.log(`Output: ${OUTPUT_PATH}`);
  console.log(`Schema version: 3.0`);
  console.log('');
  console.log(`Constants: ${constantCount}`);
  console.log(`Methods:   ${methodCount} (${totalOverloads} overloads)`);
  console.log(`Extensions: ${extensionCount}`);
  console.log(`GLSL builtin categories: ${Object.keys(GLSL_BUILTINS).length}`);
  console.log('');

  // Canary checks
  let canaryPass = true;

  if (methodCount < 150) {
    console.warn(`WARNING: Only ${methodCount} methods extracted (expected >= 150)`);
    canaryPass = false;
  } else {
    console.log(`PASS: ${methodCount} methods >= 150 threshold`);
  }

  if (constantCount < 300) {
    console.warn(`WARNING: Only ${constantCount} constants extracted (expected >= 300)`);
    canaryPass = false;
  } else {
    console.log(`PASS: ${constantCount} constants >= 300 threshold`);
  }

  if (extensionCount < 15) {
    console.warn(`WARNING: Only ${extensionCount} extensions defined (expected >= 15)`);
    canaryPass = false;
  } else {
    console.log(`PASS: ${extensionCount} extensions >= 15 threshold`);
  }

  if (warnings.length > 0) {
    console.log(`\nUnclassified constants: ${warnings.length}`);
    for (const w of warnings) {
      console.log(`  ${w}`);
    }
  }

  // Role distribution
  const roleCounts = {};
  for (const c of Object.values(allConstants)) {
    for (const r of c.roles) {
      roleCounts[r] = (roleCounts[r] || 0) + 1;
    }
  }
  const sortedRoles = Object.entries(roleCounts).sort((a, b) => b[1] - a[1]);
  console.log('\nRole distribution (top 20):');
  for (const [role, count] of sortedRoles.slice(0, 20)) {
    console.log(`  [${String(count).padStart(3)}] ${role}`);
  }

  console.log('\n' + (canaryPass ? 'All canary checks passed.' : 'Some canary checks failed (see warnings above).'));
}

run();

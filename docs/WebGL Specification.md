# WebGL Specification

## Table of Contents

*This specification covers WebGL 1.0 API interfaces and behavior*

## WebIDL Interfaces

```webidl
typedef unsigned long  GLenum;
typedef boolean        GLboolean;
typedef unsigned long  GLbitfield;
typedef byte           GLbyte;         /* 'byte' should be a signed 8 bit type. */
typedef short          GLshort;
typedef long           GLint;
typedef long           GLsizei;
typedef long long      GLintptr;
typedef long long      GLsizeiptr;
// Ideally the typedef below would use 'unsigned byte', but that doesn't currently exist in Web IDL.
typedef octet          GLubyte;        /* 'octet' should be an unsigned 8 bit type. */
typedef unsigned short GLushort;
typedef unsigned long  GLuint;
typedef unrestricted float GLfloat;
typedef unrestricted float GLclampf;

// The power preference settings are documented in the WebGLContextAttributes
// section of the specification.
enum WebGLPowerPreference { "default", "low-power", "high-performance" };
```

```webidl
dictionary WebGLContextAttributes {
    boolean alpha = true;
    boolean depth = true;
    boolean stencil = false;
    boolean antialias = true;
    boolean premultipliedAlpha = true;
    boolean preserveDrawingBuffer = false;
    WebGLPowerPreference powerPreference = "default";
    boolean failIfMajorPerformanceCaveat = false;
    boolean desynchronized = false;
};
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLObject {
    attribute USVString label;
};
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLBuffer : WebGLObject {
};
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLFramebuffer : WebGLObject {
};
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLProgram : WebGLObject {
};
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLRenderbuffer : WebGLObject {
};
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLShader : WebGLObject {
};
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLTexture : WebGLObject {
};
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLUniformLocation {
};
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLActiveInfo {
    readonly attribute GLint size;
    readonly attribute GLenum type;
    readonly attribute DOMString name;
};
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLShaderPrecisionFormat {
    readonly attribute GLint rangeMin;
    readonly attribute GLint rangeMax;
    readonly attribute GLint precision;
};
```

```webidl
typedef (ImageBitmap or
         ImageData or
         HTMLImageElement or
         HTMLCanvasElement or
         HTMLVideoElement or
         OffscreenCanvas or
         VideoFrame) TexImageSource;

typedef ([AllowShared] Float32Array or sequence<GLfloat>) Float32List;
typedef ([AllowShared] Int32Array or sequence<GLint>) Int32List;

interface mixin WebGLRenderingContextBase
{

    /* ClearBufferMask */
    const GLenum DEPTH_BUFFER_BIT               = 0x00000100;
    const GLenum STENCIL_BUFFER_BIT             = 0x00000400;
    const GLenum COLOR_BUFFER_BIT               = 0x00004000;

    /* BeginMode */
    const GLenum POINTS                         = 0x0000;
    const GLenum LINES                          = 0x0001;
    const GLenum LINE_LOOP                      = 0x0002;
    const GLenum LINE_STRIP                     = 0x0003;
    const GLenum TRIANGLES                      = 0x0004;
    const GLenum TRIANGLE_STRIP                 = 0x0005;
    const GLenum TRIANGLE_FAN                   = 0x0006;

    /* AlphaFunction (not supported in ES20) */
    /*      NEVER */
    /*      LESS */
    /*      EQUAL */
    /*      LEQUAL */
    /*      GREATER */
    /*      NOTEQUAL */
    /*      GEQUAL */
    /*      ALWAYS */

    /* BlendingFactorDest */
    const GLenum ZERO                           = 0;
    const GLenum ONE                            = 1;
    const GLenum SRC_COLOR                      = 0x0300;
    const GLenum ONE_MINUS_SRC_COLOR            = 0x0301;
    const GLenum SRC_ALPHA                      = 0x0302;
    const GLenum ONE_MINUS_SRC_ALPHA            = 0x0303;
    const GLenum DST_ALPHA                      = 0x0304;
    const GLenum ONE_MINUS_DST_ALPHA            = 0x0305;

    /* BlendingFactorSrc */
    /*      ZERO */
    /*      ONE */
    const GLenum DST_COLOR                      = 0x0306;
    const GLenum ONE_MINUS_DST_COLOR            = 0x0307;
    const GLenum SRC_ALPHA_SATURATE             = 0x0308;
    /*      SRC_ALPHA */
    /*      ONE_MINUS_SRC_ALPHA */
    /*      DST_ALPHA */
    /*      ONE_MINUS_DST_ALPHA */

    /* BlendEquationSeparate */
    const GLenum FUNC_ADD                       = 0x8006;
    const GLenum BLEND_EQUATION                 = 0x8009;
    const GLenum BLEND_EQUATION_RGB             = 0x8009;   /* same as BLEND_EQUATION */
    const GLenum BLEND_EQUATION_ALPHA           = 0x883D;

    /* BlendSubtract */
    const GLenum FUNC_SUBTRACT                  = 0x800A;
    const GLenum FUNC_REVERSE_SUBTRACT          = 0x800B;

    /* Separate Blend Functions */
    const GLenum BLEND_DST_RGB                  = 0x80C8;
    const GLenum BLEND_SRC_RGB                  = 0x80C9;
    const GLenum BLEND_DST_ALPHA                = 0x80CA;
    const GLenum BLEND_SRC_ALPHA                = 0x80CB;
    const GLenum CONSTANT_COLOR                 = 0x8001;
    const GLenum ONE_MINUS_CONSTANT_COLOR       = 0x8002;
    const GLenum CONSTANT_ALPHA                 = 0x8003;
    const GLenum ONE_MINUS_CONSTANT_ALPHA       = 0x8004;
    const GLenum BLEND_COLOR                    = 0x8005;

    /* Buffer Objects */
    const GLenum ARRAY_BUFFER                   = 0x8892;
    const GLenum ELEMENT_ARRAY_BUFFER           = 0x8893;
    const GLenum ARRAY_BUFFER_BINDING           = 0x8894;
    const GLenum ELEMENT_ARRAY_BUFFER_BINDING   = 0x8895;

    const GLenum STREAM_DRAW                    = 0x88E0;
    const GLenum STATIC_DRAW                    = 0x88E4;
    const GLenum DYNAMIC_DRAW                   = 0x88E8;

    const GLenum BUFFER_SIZE                    = 0x8764;
    const GLenum BUFFER_USAGE                   = 0x8765;

    const GLenum CURRENT_VERTEX_ATTRIB          = 0x8626;

    /* CullFaceMode */
    const GLenum FRONT                          = 0x0404;
    const GLenum BACK                           = 0x0405;
    const GLenum FRONT_AND_BACK                 = 0x0408;

    /* DepthFunction */
    /*      NEVER */
    /*      LESS */
    /*      EQUAL */
    /*      LEQUAL */
    /*      GREATER */
    /*      NOTEQUAL */
    /*      GEQUAL */
    /*      ALWAYS */

    /* EnableCap */
    /* TEXTURE_2D */
    const GLenum CULL_FACE                      = 0x0B44;
    const GLenum BLEND                          = 0x0BE2;
    const GLenum DITHER                         = 0x0BD0;
    const GLenum STENCIL_TEST                   = 0x0B90;
    const GLenum DEPTH_TEST                     = 0x0B71;
    const GLenum SCISSOR_TEST                   = 0x0C11;
    const GLenum POLYGON_OFFSET_FILL            = 0x8037;
    const GLenum SAMPLE_ALPHA_TO_COVERAGE       = 0x809E;
    const GLenum SAMPLE_COVERAGE                = 0x80A0;

    /* ErrorCode */
    const GLenum NO_ERROR                       = 0;
    const GLenum INVALID_ENUM                   = 0x0500;
    const GLenum INVALID_VALUE                  = 0x0501;
    const GLenum INVALID_OPERATION              = 0x0502;
    const GLenum OUT_OF_MEMORY                  = 0x0505;

    /* FrontFaceDirection */
    const GLenum CW                             = 0x0900;
    const GLenum CCW                            = 0x0901;

    /* GetPName */
    const GLenum LINE_WIDTH                     = 0x0B21;
    const GLenum ALIASED_POINT_SIZE_RANGE       = 0x846D;
    const GLenum ALIASED_LINE_WIDTH_RANGE       = 0x846E;
    const GLenum CULL_FACE_MODE                 = 0x0B45;
    const GLenum FRONT_FACE                     = 0x0B46;
    const GLenum DEPTH_RANGE                    = 0x0B70;
    const GLenum DEPTH_WRITEMASK                = 0x0B72;
    const GLenum DEPTH_CLEAR_VALUE              = 0x0B73;
    const GLenum DEPTH_FUNC                     = 0x0B74;
    const GLenum STENCIL_CLEAR_VALUE            = 0x0B91;
    const GLenum STENCIL_FUNC                   = 0x0B92;
    const GLenum STENCIL_FAIL                   = 0x0B94;
    const GLenum STENCIL_PASS_DEPTH_FAIL        = 0x0B95;
    const GLenum STENCIL_PASS_DEPTH_PASS        = 0x0B96;
    const GLenum STENCIL_REF                    = 0x0B97;
    const GLenum STENCIL_VALUE_MASK             = 0x0B93;
    const GLenum STENCIL_WRITEMASK              = 0x0B98;
    const GLenum STENCIL_BACK_FUNC              = 0x8800;
    const GLenum STENCIL_BACK_FAIL              = 0x8801;
    const GLenum STENCIL_BACK_PASS_DEPTH_FAIL   = 0x8802;
    const GLenum STENCIL_BACK_PASS_DEPTH_PASS   = 0x8803;
    const GLenum STENCIL_BACK_REF               = 0x8CA3;
    const GLenum STENCIL_BACK_VALUE_MASK        = 0x8CA4;
    const GLenum STENCIL_BACK_WRITEMASK         = 0x8CA5;
    const GLenum VIEWPORT                       = 0x0BA2;
    const GLenum SCISSOR_BOX                    = 0x0C10;
    /*      SCISSOR_TEST */
    const GLenum COLOR_CLEAR_VALUE              = 0x0C22;
    const GLenum COLOR_WRITEMASK                = 0x0C23;
    const GLenum UNPACK_ALIGNMENT               = 0x0CF5;
    const GLenum PACK_ALIGNMENT                 = 0x0D05;
    const GLenum MAX_TEXTURE_SIZE               = 0x0D33;
    const GLenum MAX_VIEWPORT_DIMS              = 0x0D3A;
    const GLenum SUBPIXEL_BITS                  = 0x0D50;
    const GLenum RED_BITS                       = 0x0D52;
    const GLenum GREEN_BITS                     = 0x0D53;
    const GLenum BLUE_BITS                      = 0x0D54;
    const GLenum ALPHA_BITS                     = 0x0D55;
    const GLenum DEPTH_BITS                     = 0x0D56;
    const GLenum STENCIL_BITS                   = 0x0D57;
    const GLenum POLYGON_OFFSET_UNITS           = 0x2A00;
    /*      POLYGON_OFFSET_FILL */
    const GLenum POLYGON_OFFSET_FACTOR          = 0x8038;
    const GLenum TEXTURE_BINDING_2D             = 0x8069;
    const GLenum SAMPLE_BUFFERS                 = 0x80A8;
    const GLenum SAMPLES                        = 0x80A9;
    const GLenum SAMPLE_COVERAGE_VALUE          = 0x80AA;
    const GLenum SAMPLE_COVERAGE_INVERT         = 0x80AB;

    /* GetTextureParameter */
    /*      TEXTURE_MAG_FILTER */
    /*      TEXTURE_MIN_FILTER */
    /*      TEXTURE_WRAP_S */
    /*      TEXTURE_WRAP_T */

    const GLenum COMPRESSED_TEXTURE_FORMATS     = 0x86A3;

    /* HintMode */
    const GLenum DONT_CARE                      = 0x1100;
    const GLenum FASTEST                        = 0x1101;
    const GLenum NICEST                         = 0x1102;

    /* HintTarget */
    const GLenum GENERATE_MIPMAP_HINT            = 0x8192;

    /* DataType */
    const GLenum BYTE                           = 0x1400;
    const GLenum UNSIGNED_BYTE                  = 0x1401;
    const GLenum SHORT                          = 0x1402;
    const GLenum UNSIGNED_SHORT                 = 0x1403;
    const GLenum INT                            = 0x1404;
    const GLenum UNSIGNED_INT                   = 0x1405;
    const GLenum FLOAT                          = 0x1406;

    /* PixelFormat */
    const GLenum DEPTH_COMPONENT                = 0x1902;
    const GLenum ALPHA                          = 0x1906;
    const GLenum RGB                            = 0x1907;
    const GLenum RGBA                           = 0x1908;
    const GLenum LUMINANCE                      = 0x1909;
    const GLenum LUMINANCE_ALPHA                = 0x190A;

    /* PixelType */
    /*      UNSIGNED_BYTE */
    const GLenum UNSIGNED_SHORT_4_4_4_4         = 0x8033;
    const GLenum UNSIGNED_SHORT_5_5_5_1         = 0x8034;
    const GLenum UNSIGNED_SHORT_5_6_5           = 0x8363;

    /* Shaders */
    const GLenum FRAGMENT_SHADER                  = 0x8B30;
    const GLenum VERTEX_SHADER                    = 0x8B31;
    const GLenum MAX_VERTEX_ATTRIBS               = 0x8869;
    const GLenum MAX_VERTEX_UNIFORM_VECTORS       = 0x8DFB;
    const GLenum MAX_VARYING_VECTORS              = 0x8DFC;
    const GLenum MAX_COMBINED_TEXTURE_IMAGE_UNITS = 0x8B4D;
    const GLenum MAX_VERTEX_TEXTURE_IMAGE_UNITS   = 0x8B4C;
    const GLenum MAX_TEXTURE_IMAGE_UNITS          = 0x8872;
    const GLenum MAX_FRAGMENT_UNIFORM_VECTORS     = 0x8DFD;
    const GLenum SHADER_TYPE                      = 0x8B4F;
    const GLenum DELETE_STATUS                    = 0x8B80;
    const GLenum LINK_STATUS                      = 0x8B82;
    const GLenum VALIDATE_STATUS                  = 0x8B83;
    const GLenum ATTACHED_SHADERS                 = 0x8B85;
    const GLenum ACTIVE_UNIFORMS                  = 0x8B86;
    const GLenum ACTIVE_ATTRIBUTES                = 0x8B89;
    const GLenum SHADING_LANGUAGE_VERSION         = 0x8B8C;
    const GLenum CURRENT_PROGRAM                  = 0x8B8D;

    /* StencilFunction */
    const GLenum NEVER                          = 0x0200;
    const GLenum LESS                           = 0x0201;
    const GLenum EQUAL                          = 0x0202;
    const GLenum LEQUAL                         = 0x0203;
    const GLenum GREATER                        = 0x0204;
    const GLenum NOTEQUAL                       = 0x0205;
    const GLenum GEQUAL                         = 0x0206;
    const GLenum ALWAYS                         = 0x0207;

    /* StencilOp */
    /*      ZERO */
    const GLenum KEEP                           = 0x1E00;
    const GLenum REPLACE                        = 0x1E01;
    const GLenum INCR                           = 0x1E02;
    const GLenum DECR                           = 0x1E03;
    const GLenum INVERT                         = 0x150A;
    const GLenum INCR_WRAP                      = 0x8507;
    const GLenum DECR_WRAP                      = 0x8508;

    /* StringName */
    const GLenum VENDOR                         = 0x1F00;
    const GLenum RENDERER                       = 0x1F01;
    const GLenum VERSION                        = 0x1F02;

    /* TextureMagFilter */
    const GLenum NEAREST                        = 0x2600;
    const GLenum LINEAR                         = 0x2601;

    /* TextureMinFilter */
    /*      NEAREST */
    /*      LINEAR */
    const GLenum NEAREST_MIPMAP_NEAREST         = 0x2700;
    const GLenum LINEAR_MIPMAP_NEAREST          = 0x2701;
    const GLenum NEAREST_MIPMAP_LINEAR          = 0x2702;
    const GLenum LINEAR_MIPMAP_LINEAR           = 0x2703;

    /* TextureParameterName */
    const GLenum TEXTURE_MAG_FILTER             = 0x2800;
    const GLenum TEXTURE_MIN_FILTER             = 0x2801;
    const GLenum TEXTURE_WRAP_S                 = 0x2802;
    const GLenum TEXTURE_WRAP_T                 = 0x2803;

    /* TextureTarget */
    const GLenum TEXTURE_2D                     = 0x0DE1;
    const GLenum TEXTURE                        = 0x1702;

    const GLenum TEXTURE_CUBE_MAP               = 0x8513;
    const GLenum TEXTURE_BINDING_CUBE_MAP       = 0x8514;
    const GLenum TEXTURE_CUBE_MAP_POSITIVE_X    = 0x8515;
    const GLenum TEXTURE_CUBE_MAP_NEGATIVE_X    = 0x8516;
    const GLenum TEXTURE_CUBE_MAP_POSITIVE_Y    = 0x8517;
    const GLenum TEXTURE_CUBE_MAP_NEGATIVE_Y    = 0x8518;
    const GLenum TEXTURE_CUBE_MAP_POSITIVE_Z    = 0x8519;
    const GLenum TEXTURE_CUBE_MAP_NEGATIVE_Z    = 0x851A;
    const GLenum MAX_CUBE_MAP_TEXTURE_SIZE      = 0x851C;

    /* TextureUnit */
    const GLenum TEXTURE0                       = 0x84C0;
    const GLenum TEXTURE1                       = 0x84C1;
    const GLenum TEXTURE2                       = 0x84C2;
    const GLenum TEXTURE3                       = 0x84C3;
    const GLenum TEXTURE4                       = 0x84C4;
    const GLenum TEXTURE5                       = 0x84C5;
    const GLenum TEXTURE6                       = 0x84C6;
    const GLenum TEXTURE7                       = 0x84C7;
    const GLenum TEXTURE8                       = 0x84C8;
    const GLenum TEXTURE9                       = 0x84C9;
    const GLenum TEXTURE10                      = 0x84CA;
    const GLenum TEXTURE11                      = 0x84CB;
    const GLenum TEXTURE12                      = 0x84CC;
    const GLenum TEXTURE13                      = 0x84CD;
    const GLenum TEXTURE14                      = 0x84CE;
    const GLenum TEXTURE15                      = 0x84CF;
    const GLenum TEXTURE16                      = 0x84D0;
    const GLenum TEXTURE17                      = 0x84D1;
    const GLenum TEXTURE18                      = 0x84D2;
    const GLenum TEXTURE19                      = 0x84D3;
    const GLenum TEXTURE20                      = 0x84D4;
    const GLenum TEXTURE21                      = 0x84D5;
    const GLenum TEXTURE22                      = 0x84D6;
    const GLenum TEXTURE23                      = 0x84D7;
    const GLenum TEXTURE24                      = 0x84D8;
    const GLenum TEXTURE25                      = 0x84D9;
    const GLenum TEXTURE26                      = 0x84DA;
    const GLenum TEXTURE27                      = 0x84DB;
    const GLenum TEXTURE28                      = 0x84DC;
    const GLenum TEXTURE29                      = 0x84DD;
    const GLenum TEXTURE30                      = 0x84DE;
    const GLenum TEXTURE31                      = 0x84DF;
    const GLenum ACTIVE_TEXTURE                 = 0x84E0;

    /* TextureWrapMode */
    const GLenum REPEAT                         = 0x2901;
    const GLenum CLAMP_TO_EDGE                  = 0x812F;
    const GLenum MIRRORED_REPEAT                = 0x8370;

    /* Uniform Types */
    const GLenum FLOAT_VEC2                     = 0x8B50;
    const GLenum FLOAT_VEC3                     = 0x8B51;
    const GLenum FLOAT_VEC4                     = 0x8B52;
    const GLenum INT_VEC2                       = 0x8B53;
    const GLenum INT_VEC3                       = 0x8B54;
    const GLenum INT_VEC4                       = 0x8B55;
    const GLenum BOOL                           = 0x8B56;
    const GLenum BOOL_VEC2                      = 0x8B57;
    const GLenum BOOL_VEC3                      = 0x8B58;
    const GLenum BOOL_VEC4                      = 0x8B59;
    const GLenum FLOAT_MAT2                     = 0x8B5A;
    const GLenum FLOAT_MAT3                     = 0x8B5B;
    const GLenum FLOAT_MAT4                     = 0x8B5C;
    const GLenum SAMPLER_2D                     = 0x8B5E;
    const GLenum SAMPLER_CUBE                   = 0x8B60;

    /* Vertex Arrays */
    const GLenum VERTEX_ATTRIB_ARRAY_ENABLED        = 0x8622;
    const GLenum VERTEX_ATTRIB_ARRAY_SIZE           = 0x8623;
    const GLenum VERTEX_ATTRIB_ARRAY_STRIDE         = 0x8624;
    const GLenum VERTEX_ATTRIB_ARRAY_TYPE           = 0x8625;
    const GLenum VERTEX_ATTRIB_ARRAY_NORMALIZED     = 0x886A;
    const GLenum VERTEX_ATTRIB_ARRAY_POINTER        = 0x8645;
    const GLenum VERTEX_ATTRIB_ARRAY_BUFFER_BINDING = 0x889F;

    /* Read Format */
    const GLenum IMPLEMENTATION_COLOR_READ_TYPE   = 0x8B9A;
    const GLenum IMPLEMENTATION_COLOR_READ_FORMAT = 0x8B9B;

    /* Shader Source */
    const GLenum COMPILE_STATUS                 = 0x8B81;

    /* Shader Precision-Specified Types */
    const GLenum LOW_FLOAT                      = 0x8DF0;
    const GLenum MEDIUM_FLOAT                   = 0x8DF1;
    const GLenum HIGH_FLOAT                     = 0x8DF2;
    const GLenum LOW_INT                        = 0x8DF3;
    const GLenum MEDIUM_INT                     = 0x8DF4;
    const GLenum HIGH_INT                       = 0x8DF5;

    /* Framebuffer Object. */
    const GLenum FRAMEBUFFER                    = 0x8D40;
    const GLenum RENDERBUFFER                   = 0x8D41;

    const GLenum RGBA4                          = 0x8056;
    const GLenum RGB5_A1                        = 0x8057;
    const GLenum RGBA8                          = 0x8058;
    const GLenum RGB565                         = 0x8D62;
    const GLenum DEPTH_COMPONENT16              = 0x81A5;
    const GLenum STENCIL_INDEX8                 = 0x8D48;
    const GLenum DEPTH_STENCIL                  = 0x84F9;

    const GLenum RENDERBUFFER_WIDTH             = 0x8D42;
    const GLenum RENDERBUFFER_HEIGHT            = 0x8D43;
    const GLenum RENDERBUFFER_INTERNAL_FORMAT   = 0x8D44;
    const GLenum RENDERBUFFER_RED_SIZE          = 0x8D50;
    const GLenum RENDERBUFFER_GREEN_SIZE        = 0x8D51;
    const GLenum RENDERBUFFER_BLUE_SIZE         = 0x8D52;
    const GLenum RENDERBUFFER_ALPHA_SIZE        = 0x8D53;
    const GLenum RENDERBUFFER_DEPTH_SIZE        = 0x8D54;
    const GLenum RENDERBUFFER_STENCIL_SIZE      = 0x8D55;

    const GLenum FRAMEBUFFER_ATTACHMENT_OBJECT_TYPE           = 0x8CD0;
    const GLenum FRAMEBUFFER_ATTACHMENT_OBJECT_NAME           = 0x8CD1;
    const GLenum FRAMEBUFFER_ATTACHMENT_TEXTURE_LEVEL         = 0x8CD2;
    const GLenum FRAMEBUFFER_ATTACHMENT_TEXTURE_CUBE_MAP_FACE = 0x8CD3;

    const GLenum COLOR_ATTACHMENT0              = 0x8CE0;
    const GLenum DEPTH_ATTACHMENT               = 0x8D00;
    const GLenum STENCIL_ATTACHMENT             = 0x8D20;
    const GLenum DEPTH_STENCIL_ATTACHMENT       = 0x821A;

    const GLenum NONE                           = 0;

    const GLenum FRAMEBUFFER_COMPLETE                      = 0x8CD5;
    const GLenum FRAMEBUFFER_INCOMPLETE_ATTACHMENT         = 0x8CD6;
    const GLenum FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT = 0x8CD7;
    const GLenum FRAMEBUFFER_INCOMPLETE_DIMENSIONS         = 0x8CD9;
    const GLenum FRAMEBUFFER_UNSUPPORTED                   = 0x8CDD;

    const GLenum FRAMEBUFFER_BINDING            = 0x8CA6;
    const GLenum RENDERBUFFER_BINDING           = 0x8CA7;
    const GLenum MAX_RENDERBUFFER_SIZE          = 0x84E8;

    const GLenum INVALID_FRAMEBUFFER_OPERATION  = 0x0506;

    /* WebGL-specific enums */
    const GLenum UNPACK_FLIP_Y_WEBGL            = 0x9240;
    const GLenum UNPACK_PREMULTIPLY_ALPHA_WEBGL = 0x9241;
    const GLenum CONTEXT_LOST_WEBGL             = 0x9242;
    const GLenum UNPACK_COLORSPACE_CONVERSION_WEBGL = 0x9243;
    const GLenum BROWSER_DEFAULT_WEBGL          = 0x9244;

    readonly attribute (HTMLCanvasElement or OffscreenCanvas) canvas;
    readonly attribute GLsizei drawingBufferWidth;
    readonly attribute GLsizei drawingBufferHeight;
    readonly attribute GLenum drawingBufferFormat;

    /* Upon context creation, drawingBufferColorSpace and unpackColorSpace both
       default to the value "srgb". */
    attribute PredefinedColorSpace drawingBufferColorSpace;
    attribute PredefinedColorSpace unpackColorSpace;

    [WebGLHandlesContextLoss] WebGLContextAttributes? getContextAttributes();
    [WebGLHandlesContextLoss] boolean isContextLost();

    sequence<DOMString>? getSupportedExtensions();
    object? getExtension(DOMString name);

    undefined drawingBufferStorage(GLenum sizedFormat, unsigned long width, unsigned long height);

    undefined activeTexture(GLenum texture);
    undefined attachShader(WebGLProgram program, WebGLShader shader);
    undefined bindAttribLocation(WebGLProgram program, GLuint index, DOMString name);
    undefined bindBuffer(GLenum target, WebGLBuffer? buffer);
    undefined bindFramebuffer(GLenum target, WebGLFramebuffer? framebuffer);
    undefined bindRenderbuffer(GLenum target, WebGLRenderbuffer? renderbuffer);
    undefined bindTexture(GLenum target, WebGLTexture? texture);
    undefined blendColor(GLclampf red, GLclampf green, GLclampf blue, GLclampf alpha);
    undefined blendEquation(GLenum mode);
    undefined blendEquationSeparate(GLenum modeRGB, GLenum modeAlpha);
    undefined blendFunc(GLenum sfactor, GLenum dfactor);
    undefined blendFuncSeparate(GLenum srcRGB, GLenum dstRGB,
                                GLenum srcAlpha, GLenum dstAlpha);

    [WebGLHandlesContextLoss] GLenum checkFramebufferStatus(GLenum target);
    undefined clear(GLbitfield mask);
    undefined clearColor(GLclampf red, GLclampf green, GLclampf blue, GLclampf alpha);
    undefined clearDepth(GLclampf depth);
    undefined clearStencil(GLint s);
    undefined colorMask(GLboolean red, GLboolean green, GLboolean blue, GLboolean alpha);
    undefined compileShader(WebGLShader shader);

    undefined copyTexImage2D(GLenum target, GLint level, GLenum internalformat,
                             GLint x, GLint y, GLsizei width, GLsizei height,
                             GLint border);
    undefined copyTexSubImage2D(GLenum target, GLint level, GLint xoffset, GLint yoffset,
                                GLint x, GLint y, GLsizei width, GLsizei height);

    WebGLBuffer createBuffer();
    WebGLFramebuffer createFramebuffer();
    WebGLProgram createProgram();
    WebGLRenderbuffer createRenderbuffer();
    WebGLShader? createShader(GLenum type);
    WebGLTexture createTexture();

    undefined cullFace(GLenum mode);

    undefined deleteBuffer(WebGLBuffer? buffer);
    undefined deleteFramebuffer(WebGLFramebuffer? framebuffer);
    undefined deleteProgram(WebGLProgram? program);
    undefined deleteRenderbuffer(WebGLRenderbuffer? renderbuffer);
    undefined deleteShader(WebGLShader? shader);
    undefined deleteTexture(WebGLTexture? texture);

    undefined depthFunc(GLenum func);
    undefined depthMask(GLboolean flag);
    undefined depthRange(GLclampf zNear, GLclampf zFar);
    undefined detachShader(WebGLProgram program, WebGLShader shader);
    undefined disable(GLenum cap);
    undefined disableVertexAttribArray(GLuint index);
    undefined drawArrays(GLenum mode, GLint first, GLsizei count);
    undefined drawElements(GLenum mode, GLsizei count, GLenum type, GLintptr offset);

    undefined enable(GLenum cap);
    undefined enableVertexAttribArray(GLuint index);
    undefined finish();
    undefined flush();
    undefined framebufferRenderbuffer(GLenum target, GLenum attachment,
                                      GLenum renderbuffertarget,
                                      WebGLRenderbuffer? renderbuffer);
    undefined framebufferTexture2D(GLenum target, GLenum attachment, GLenum textarget,
                                   WebGLTexture? texture, GLint level);
    undefined frontFace(GLenum mode);

    undefined generateMipmap(GLenum target);

    WebGLActiveInfo? getActiveAttrib(WebGLProgram program, GLuint index);
    WebGLActiveInfo? getActiveUniform(WebGLProgram program, GLuint index);
    sequence<WebGLShader>? getAttachedShaders(WebGLProgram program);

    [WebGLHandlesContextLoss] GLint getAttribLocation(WebGLProgram program, DOMString name);

    any getBufferParameter(GLenum target, GLenum pname);
    any getParameter(GLenum pname);

    [WebGLHandlesContextLoss] GLenum getError();

    any getFramebufferAttachmentParameter(GLenum target, GLenum attachment,
                                          GLenum pname);
    any getProgramParameter(WebGLProgram program, GLenum pname);
    DOMString? getProgramInfoLog(WebGLProgram program);
    any getRenderbufferParameter(GLenum target, GLenum pname);
    any getShaderParameter(WebGLShader shader, GLenum pname);
    WebGLShaderPrecisionFormat? getShaderPrecisionFormat(GLenum shadertype, GLenum precisiontype);
    DOMString? getShaderInfoLog(WebGLShader shader);

    DOMString? getShaderSource(WebGLShader shader);

    any getTexParameter(GLenum target, GLenum pname);

    any getUniform(WebGLProgram program, WebGLUniformLocation location);

    WebGLUniformLocation? getUniformLocation(WebGLProgram program, DOMString name);

    any getVertexAttrib(GLuint index, GLenum pname);

    [WebGLHandlesContextLoss] GLintptr getVertexAttribOffset(GLuint index, GLenum pname);

    undefined hint(GLenum target, GLenum mode);
    [WebGLHandlesContextLoss] GLboolean isBuffer(WebGLBuffer? buffer);
    [WebGLHandlesContextLoss] GLboolean isEnabled(GLenum cap);
    [WebGLHandlesContextLoss] GLboolean isFramebuffer(WebGLFramebuffer? framebuffer);
    [WebGLHandlesContextLoss] GLboolean isProgram(WebGLProgram? program);
    [WebGLHandlesContextLoss] GLboolean isRenderbuffer(WebGLRenderbuffer? renderbuffer);
    [WebGLHandlesContextLoss] GLboolean isShader(WebGLShader? shader);
    [WebGLHandlesContextLoss] GLboolean isTexture(WebGLTexture? texture);
    undefined lineWidth(GLfloat width);
    undefined linkProgram(WebGLProgram program);
    undefined pixelStorei(GLenum pname, GLint param);
    undefined polygonOffset(GLfloat factor, GLfloat units);

    undefined renderbufferStorage(GLenum target, GLenum internalformat,
                                  GLsizei width, GLsizei height);
    undefined sampleCoverage(GLclampf value, GLboolean invert);
    undefined scissor(GLint x, GLint y, GLsizei width, GLsizei height);

    undefined shaderSource(WebGLShader shader, DOMString source);

    undefined stencilFunc(GLenum func, GLint ref, GLuint mask);
    undefined stencilFuncSeparate(GLenum face, GLenum func, GLint ref, GLuint mask);
    undefined stencilMask(GLuint mask);
    undefined stencilMaskSeparate(GLenum face, GLuint mask);
    undefined stencilOp(GLenum fail, GLenum zfail, GLenum zpass);
    undefined stencilOpSeparate(GLenum face, GLenum fail, GLenum zfail, GLenum zpass);

    undefined texParameterf(GLenum target, GLenum pname, GLfloat param);
    undefined texParameteri(GLenum target, GLenum pname, GLint param);

    undefined uniform1f(WebGLUniformLocation? location, GLfloat x);
    undefined uniform2f(WebGLUniformLocation? location, GLfloat x, GLfloat y);
    undefined uniform3f(WebGLUniformLocation? location, GLfloat x, GLfloat y, GLfloat z);
    undefined uniform4f(WebGLUniformLocation? location, GLfloat x, GLfloat y, GLfloat z, GLfloat w);

    undefined uniform1i(WebGLUniformLocation? location, GLint x);
    undefined uniform2i(WebGLUniformLocation? location, GLint x, GLint y);
    undefined uniform3i(WebGLUniformLocation? location, GLint x, GLint y, GLint z);
    undefined uniform4i(WebGLUniformLocation? location, GLint x, GLint y, GLint z, GLint w);

    undefined useProgram(WebGLProgram? program);
    undefined validateProgram(WebGLProgram program);

    undefined vertexAttrib1f(GLuint index, GLfloat x);
    undefined vertexAttrib2f(GLuint index, GLfloat x, GLfloat y);
    undefined vertexAttrib3f(GLuint index, GLfloat x, GLfloat y, GLfloat z);
    undefined vertexAttrib4f(GLuint index, GLfloat x, GLfloat y, GLfloat z, GLfloat w);

    undefined vertexAttrib1fv(GLuint index, Float32List values);
    undefined vertexAttrib2fv(GLuint index, Float32List values);
    undefined vertexAttrib3fv(GLuint index, Float32List values);
    undefined vertexAttrib4fv(GLuint index, Float32List values);

    undefined vertexAttribPointer(GLuint index, GLint size, GLenum type,
                                  GLboolean normalized, GLsizei stride, GLintptr offset);

    undefined viewport(GLint x, GLint y, GLsizei width, GLsizei height);
};

interface mixin WebGLRenderingContextOverloads
{
    undefined bufferData(GLenum target, GLsizeiptr size, GLenum usage);
    undefined bufferData(GLenum target, AllowSharedBufferSource? data, GLenum usage);
    undefined bufferSubData(GLenum target, GLintptr offset, AllowSharedBufferSource data);

    undefined compressedTexImage2D(GLenum target, GLint level, GLenum internalformat,
                                   GLsizei width, GLsizei height, GLint border,
                                   [AllowShared] ArrayBufferView data);
    undefined compressedTexSubImage2D(GLenum target, GLint level,
                                      GLint xoffset, GLint yoffset,
                                      GLsizei width, GLsizei height, GLenum format,
                                      [AllowShared] ArrayBufferView data);

    undefined readPixels(GLint x, GLint y, GLsizei width, GLsizei height,
                         GLenum format, GLenum type, [AllowShared] ArrayBufferView? pixels);

    undefined texImage2D(GLenum target, GLint level, GLint internalformat,
                         GLsizei width, GLsizei height, GLint border, GLenum format,
                         GLenum type, [AllowShared] ArrayBufferView? pixels);
    undefined texImage2D(GLenum target, GLint level, GLint internalformat,
                         GLenum format, GLenum type, TexImageSource source); // May throw DOMException

    undefined texSubImage2D(GLenum target, GLint level, GLint xoffset, GLint yoffset,
                            GLsizei width, GLsizei height,
                            GLenum format, GLenum type, [AllowShared] ArrayBufferView? pixels);
    undefined texSubImage2D(GLenum target, GLint level, GLint xoffset, GLint yoffset,
                            GLenum format, GLenum type, TexImageSource source); // May throw DOMException

    undefined uniform1fv(WebGLUniformLocation? location, Float32List v);
    undefined uniform2fv(WebGLUniformLocation? location, Float32List v);
    undefined uniform3fv(WebGLUniformLocation? location, Float32List v);
    undefined uniform4fv(WebGLUniformLocation? location, Float32List v);

    undefined uniform1iv(WebGLUniformLocation? location, Int32List v);
    undefined uniform2iv(WebGLUniformLocation? location, Int32List v);
    undefined uniform3iv(WebGLUniformLocation? location, Int32List v);
    undefined uniform4iv(WebGLUniformLocation? location, Int32List v);

    undefined uniformMatrix2fv(WebGLUniformLocation? location, GLboolean transpose, Float32List value);
    undefined uniformMatrix3fv(WebGLUniformLocation? location, GLboolean transpose, Float32List value);
    undefined uniformMatrix4fv(WebGLUniformLocation? location, GLboolean transpose, Float32List value);
};

[Exposed=(Window,Worker)]
interface WebGLRenderingContext
{
};
WebGLRenderingContext includes WebGLRenderingContextBase;
WebGLRenderingContext includes WebGLRenderingContextOverloads;
```

```webidl
[Exposed=(Window,Worker)]
interface WebGLContextEvent : Event {
    constructor(DOMString type, optional WebGLContextEventInit eventInit = {});
    readonly attribute DOMString statusMessage;
};

// EventInit is defined in the DOM4 specification.
dictionary WebGLContextEventInit : EventInit {
    DOMString statusMessage = "";
};
```

## Abstract

This specification describes an additional rendering context and support
        objects for the
        
            HTML 5 canvas element [CANVAS].
        
        This context allows rendering using an API that conforms closely to the OpenGL ES 2.0 API.

## Status

This document is an editor's draft. Do not cite this document as other than work in
        progress.

## Feedback

Public discussion of this specification is welcome on
        the public_webgl@khronos.org mailing list
        (instructions, archives).

Please file bugs against the specification or its conformance tests in
        the issue tracker. Pull requests
        are welcome against the Github
        repository.

## Introduction

> **Note:** WebGL™ is an immediate mode 3D rendering API designed for the
      web.  It is derived from OpenGL® ES 2.0, and provides similar
      rendering functionality, but in an HTML context.  WebGL is
      designed as a rendering context for the HTML Canvas element.
      The HTML Canvas provides a destination for programmatic
      rendering in web pages, and allows for performing that rendering
      using different rendering APIs.  The only such interface
      described as part of the Canvas specification is the 2D canvas
      rendering context, CanvasRenderingContext2D. This document
      describes another such interface, WebGLRenderingContext, which
      presents the WebGL API.
    

      The immediate mode nature of the API is a divergence from most
      web APIs.  Given the many use cases of 3D graphics, WebGL
      chooses the approach of providing flexible primitives that can
      be applied to any use case.  Libraries can provide an API on top
      of WebGL that is more tailored to specific areas, thus adding a
      convenience layer to WebGL that can accelerate and simplify development.
      However, because of its OpenGL ES 2.0 heritage, it should be
      straightforward for developers familiar with modern desktop
      OpenGL or OpenGL ES 2.0 development to transition to WebGL
      development.

WebGL™ is an immediate mode 3D rendering API designed for the
      web.  It is derived from OpenGL® ES 2.0, and provides similar
      rendering functionality, but in an HTML context.  WebGL is
      designed as a rendering context for the HTML Canvas element.
      The HTML Canvas provides a destination for programmatic
      rendering in web pages, and allows for performing that rendering
      using different rendering APIs.  The only such interface
      described as part of the Canvas specification is the 2D canvas
      rendering context, CanvasRenderingContext2D. This document
      describes another such interface, WebGLRenderingContext, which
      presents the WebGL API.

The immediate mode nature of the API is a divergence from most
      web APIs.  Given the many use cases of 3D graphics, WebGL
      chooses the approach of providing flexible primitives that can
      be applied to any use case.  Libraries can provide an API on top
      of WebGL that is more tailored to specific areas, thus adding a
      convenience layer to WebGL that can accelerate and simplify development.
      However, because of its OpenGL ES 2.0 heritage, it should be
      straightforward for developers familiar with modern desktop
      OpenGL or OpenGL ES 2.0 development to transition to WebGL
      development.

Many functions described in this document contain links to OpenGL ES
     man pages. While every effort is made to make these pages match the
     OpenGL ES 2.0 specification [GLES20],
     they may contain errors. In the case of a contradiction, the OpenGL
     ES 2.0 specification is the final authority.

The remaining sections of this document are intended to be read in conjunction
      with the OpenGL ES 2.0 specification (2.0.25 at the time of this writing, available
      from the Khronos OpenGL ES API Registry).
      Unless otherwise specified, the behavior of each method is defined by the
      OpenGL ES 2.0 specification.  This specification may diverge from OpenGL ES 2.0
      in order to ensure interoperability or security, often defining areas that
      OpenGL ES 2.0 leaves implementation-defined.  These differences are summarized in the
      Differences Between WebGL and OpenGL ES 2.0 section.

## Context Creation and Drawing Buffer

Before using the WebGL API, the author must obtain a WebGLRenderingContext
        object for a given HTMLCanvasElement [CANVAS] or
        OffscreenCanvas [OFFSCREENCANVAS] as described
        below. This object is used to manage OpenGL state and render to the drawing buffer, which
        must be created at the time of context creation.

Each WebGLRenderingContext has an
        associated canvas, set upon creation, which is
        a canvas [CANVAS] or offscreen
        canvas [OFFSCREENCANVAS].

Each WebGLRenderingContext has context
        creation parameters, set upon creation, in
        a WebGLContextAttributes object.

Each WebGLRenderingContext has actual
        context parameters, set each time the drawing buffer is created, in
        a WebGLContextAttributes object.

Each WebGLRenderingContext has a webgl
        context lost flag, which is initially unset.

When the getContext() method of a canvas element
        or offscreen canvas object is to return a new object for
        the contextId webgl [CANVASCONTEXTS],
        the user agent must perform the following steps:

        
 Create a new WebGLRenderingContext object, context.

         Let context's canvas be the canvas or offscreen
             canvas the getContext() method is associated with.

         Create a new WebGLContextAttributes object, contextAttributes.

         If getContext() was invoked with a second argument, options, set
             the attributes of contextAttributes from those specified in options.

         Create a drawing buffer using the settings
             specified in contextAttributes, and associate the drawing buffer
             with context.

         If drawing buffer creation failed, perform the following steps:

          
 Fire a WebGL context creation
          error at canvas.

           Return null and terminate these steps.

          
 Create a new WebGLContextAttributes object, actualAttributes.

         Set the attributes of actualAttributes based on the properties of the newly
             created drawing buffer.

         Set context's context creation
        parameters to contextAttributes.

         Set context's actual context
        parameters to actualAttributes.

         Return context.

- Create a new WebGLRenderingContext object, context.

         Let context's canvas be the canvas or offscreen
             canvas the getContext() method is associated with.

         Create a new WebGLContextAttributes object, contextAttributes.

         If getContext() was invoked with a second argument, options, set
             the attributes of contextAttributes from those specified in options.

         Create a drawing buffer using the settings
             specified in contextAttributes, and associate the drawing buffer
             with context.

         If drawing buffer creation failed, perform the following steps:

          
 Fire a WebGL context creation
          error at canvas.

           Return null and terminate these steps.

          
 Create a new WebGLContextAttributes object, actualAttributes.

         Set the attributes of actualAttributes based on the properties of the newly
             created drawing buffer.

         Set context's context creation
        parameters to contextAttributes.

         Set context's actual context
        parameters to actualAttributes.

         Return context.
- Let context's canvas be the canvas or offscreen
             canvas the getContext() method is associated with.

         Create a new WebGLContextAttributes object, contextAttributes.

         If getContext() was invoked with a second argument, options, set
             the attributes of contextAttributes from those specified in options.

         Create a drawing buffer using the settings
             specified in contextAttributes, and associate the drawing buffer
             with context.

         If drawing buffer creation failed, perform the following steps:

          
 Fire a WebGL context creation
          error at canvas.

           Return null and terminate these steps.

          
 Create a new WebGLContextAttributes object, actualAttributes.

         Set the attributes of actualAttributes based on the properties of the newly
             created drawing buffer.

         Set context's context creation
        parameters to contextAttributes.

         Set context's actual context
        parameters to actualAttributes.

         Return context.
- Create a new WebGLContextAttributes object, contextAttributes.

         If getContext() was invoked with a second argument, options, set
             the attributes of contextAttributes from those specified in options.

         Create a drawing buffer using the settings
             specified in contextAttributes, and associate the drawing buffer
             with context.

         If drawing buffer creation failed, perform the following steps:

          
 Fire a WebGL context creation
          error at canvas.

           Return null and terminate these steps.

          
 Create a new WebGLContextAttributes object, actualAttributes.

         Set the attributes of actualAttributes based on the properties of the newly
             created drawing buffer.

         Set context's context creation
        parameters to contextAttributes.

         Set context's actual context
        parameters to actualAttributes.

         Return context.
- If getContext() was invoked with a second argument, options, set
             the attributes of contextAttributes from those specified in options.

         Create a drawing buffer using the settings
             specified in contextAttributes, and associate the drawing buffer
             with context.

         If drawing buffer creation failed, perform the following steps:

          
 Fire a WebGL context creation
          error at canvas.

           Return null and terminate these steps.

          
 Create a new WebGLContextAttributes object, actualAttributes.

         Set the attributes of actualAttributes based on the properties of the newly
             created drawing buffer.

         Set context's context creation
        parameters to contextAttributes.

         Set context's actual context
        parameters to actualAttributes.

         Return context.
- Create a drawing buffer using the settings
             specified in contextAttributes, and associate the drawing buffer
             with context.

         If drawing buffer creation failed, perform the following steps:

          
 Fire a WebGL context creation
          error at canvas.

           Return null and terminate these steps.

          
 Create a new WebGLContextAttributes object, actualAttributes.

         Set the attributes of actualAttributes based on the properties of the newly
             created drawing buffer.

         Set context's context creation
        parameters to contextAttributes.

         Set context's actual context
        parameters to actualAttributes.

         Return context.
- If drawing buffer creation failed, perform the following steps:

          
 Fire a WebGL context creation
          error at canvas.

           Return null and terminate these steps.

          
 Create a new WebGLContextAttributes object, actualAttributes.

         Set the attributes of actualAttributes based on the properties of the newly
             created drawing buffer.

         Set context's context creation
        parameters to contextAttributes.

         Set context's actual context
        parameters to actualAttributes.

         Return context.
- Fire a WebGL context creation
          error at canvas.

           Return null and terminate these steps.
- Return null and terminate these steps.
- Create a new WebGLContextAttributes object, actualAttributes.

         Set the attributes of actualAttributes based on the properties of the newly
             created drawing buffer.

         Set context's context creation
        parameters to contextAttributes.

         Set context's actual context
        parameters to actualAttributes.

         Return context.
- Set the attributes of actualAttributes based on the properties of the newly
             created drawing buffer.

         Set context's context creation
        parameters to contextAttributes.

         Set context's actual context
        parameters to actualAttributes.

         Return context.
- Set context's context creation
        parameters to contextAttributes.

         Set context's actual context
        parameters to actualAttributes.

         Return context.
- Set context's actual context
        parameters to actualAttributes.

         Return context.
- Return context.

- Fire a WebGL context creation
          error at canvas.

           Return null and terminate these steps.
- Return null and terminate these steps.

> **Note:** The canvas context type 'experimental-webgl' has historically been used to provide access to
      WebGL implementations which are not yet complete or conformant.

The canvas context type 'experimental-webgl' has historically been used to provide access to
      WebGL implementations which are not yet complete or conformant.

If the user agent supports both the webgl and experimental-webgl
      canvas context types, they shall be treated as aliases. For example, if a call
      to getContext('webgl') successfully creates a WebGLRenderingContext, a subsequent
      call to getContext('experimental-webgl') shall return the same context object.

The drawing buffer into which the API calls are rendered shall be defined upon creation of
        the WebGLRenderingContext object. The following description defines how
        to create a drawing buffer.

The table below shows all the buffers which make up the drawing buffer, along with their
        minimum sizes and whether they are defined or not by default. The size of this drawing
        buffer shall be determined by the width and height attributes of
        the HTMLCanvasElement or OffscreenCanvas. The table below also shows the value to which
        these buffers shall be cleared when first created, when the size is changed, or after
        presentation when the preserveDrawingBuffer context creation attribute
        is false.

HTMLCanvasElement.width and .height values less than 1 are treated as 1.
        A 0x0 canvas will yield a 1x1 drawingBufferWidth/Height.

If the requested width or height cannot be satisfied, either when the drawing buffer is first
        created or when the width and height attributes of the
        HTMLCanvasElement or OffscreenCanvas are changed, a drawing buffer
        with smaller dimensions shall be created. The dimensions actually used are implementation
        dependent and there is no guarantee that a buffer with the same aspect ratio will be
        created. The actual drawing buffer size can be obtained from
        the drawingBufferWidth and drawingBufferHeight attributes.

A WebGL implementation must not perform any automatic scaling of the size of the drawing
        buffer on high-definition displays. The context's drawingBufferWidth
        and drawingBufferHeight must match the canvas's width
        and height attributes as closely as possible, modulo implementation-dependent
        constraints.

> **Note:** The constraint above does not change the amount of space the canvas element consumes on
            the web page, even on a high-definition display. The
            canvas's intrinsic
            dimensions [CANVAS] equal the size of its coordinate
            space, with the numbers interpreted in CSS pixels, and CSS pixels
            are resolution-independent [CSS].
        

            A WebGL application can achieve a 1:1 ratio between drawing buffer pixels and on-screen
            pixels on high-definition displays by examining properties
            like window.devicePixelRatio, scaling the canvas's width
            and height by that factor, and setting its CSS width and height to the
            original width and height. An application can simulate the effect of running on a
            higher-resolution display simply by scaling up the canvas's width
            and height properties.

The constraint above does not change the amount of space the canvas element consumes on
            the web page, even on a high-definition display. The
            canvas's intrinsic
            dimensions [CANVAS] equal the size of its coordinate
            space, with the numbers interpreted in CSS pixels, and CSS pixels
            are resolution-independent [CSS].

A WebGL application can achieve a 1:1 ratio between drawing buffer pixels and on-screen
            pixels on high-definition displays by examining properties
            like window.devicePixelRatio, scaling the canvas's width
            and height by that factor, and setting its CSS width and height to the
            original width and height. An application can simulate the effect of running on a
            higher-resolution display simply by scaling up the canvas's width
            and height properties.

The optional WebGLContextAttributes object may be used
        to change whether or not the buffers are defined. It can also be used to define whether the
        color buffer will include an alpha channel. If defined, the alpha channel is used by the
        HTML compositor to combine the color buffer with the rest of the page. The
        WebGLContextAttributes object is only used on the first call to
        getContext. No facility is provided to change the attributes of the drawing
        buffer after its creation.

The depth, stencil and antialias attributes, when set
        to true, are requests, not requirements. The WebGL implementation should make a best effort
        to honor them. When any of these attributes is set to false, however, the WebGL
        implementation must not provide the associated functionality. Combinations of attributes not
        supported by the WebGL implementation or graphics hardware shall not cause a failure to
        create a WebGLRenderingContext. The actual context
        parameters are set to the attributes of the created drawing buffer. The
        alpha, premultipliedAlpha and preserveDrawingBuffer
        attributes must be obeyed by the WebGL implementation.

WebGL presents its drawing buffer to the HTML page compositor immediately before a
        compositing operation, but only if at least one of the following have been called since the
        previous compositing operation:
        
Context creation
Canvas resize

                Any of the
                [Draw Operations],
                called while the drawing buffer is the currently bound (draw) framebuffer.

- Context creation
- Canvas resize
- Any of the
                [Draw Operations],
                called while the drawing buffer is the currently bound (draw) framebuffer.

Before the drawing buffer is presented for compositing the implementation shall ensure that
        all rendering operations have been flushed to the drawing buffer. By default, after
        compositing the contents of the drawing buffer shall be cleared to their default values, as
        shown in the table above.

This default behavior can be changed by setting the preserveDrawingBuffer
        attribute of the WebGLContextAttributes object. If
        this flag is true, the contents of the drawing buffer shall be preserved until the author
        either clears or overwrites them. If this flag is false, attempting to perform operations
        using this context as a source image after the rendering function has returned can lead to
        undefined behavior. This includes readPixels or toDataURL calls,
        using this context as the source image of another context's texImage2D or
        drawImage call, or creating
        an ImageBitmap [HTML]
        from this context's canvas.

> **Note:** While it is sometimes desirable to preserve the drawing buffer, it can cause significant
            performance loss on some platforms. Whenever possible this flag should remain false
            and other techniques used. Techniques like synchronous drawing buffer access (e.g.,
            calling readPixels or toDataURL in the same function that
            renders to the drawing buffer) can be used to get the contents of the drawing buffer.
            If the author needs to render to the same drawing buffer over a series of calls, a
            Framebuffer Object can be used.
        

            Implementations may optimize away the required implicit clear operation of the Drawing
            Buffer as long as a guarantee can be made that the author cannot gain access to buffer
            contents from another process. For instance, if the author performs an explicit
            clear then the implicit clear is not needed.

While it is sometimes desirable to preserve the drawing buffer, it can cause significant
            performance loss on some platforms. Whenever possible this flag should remain false
            and other techniques used. Techniques like synchronous drawing buffer access (e.g.,
            calling readPixels or toDataURL in the same function that
            renders to the drawing buffer) can be used to get the contents of the drawing buffer.
            If the author needs to render to the same drawing buffer over a series of calls, a
            Framebuffer Object can be used.

Implementations may optimize away the required implicit clear operation of the Drawing
            Buffer as long as a guarantee can be made that the author cannot gain access to buffer
            contents from another process. For instance, if the author performs an explicit
            clear then the implicit clear is not needed.

> **Note:** drawingBufferStorage allows for efficiently respecifying width and height together simultaneously.
                With HTMLCanvasElement.width and HTMLCanvasElement.height,
                setting one and then the other can incur intermediate reallocations, though User Agents do try to optimize these out.

- RGBA8
SRGB8_ALPHA8 (0x8C43) (E.g. from EXT_sRGB)
                RGBA16F (0x881A) (E.g. from EXT_color_buffer_half_float)
- SRGB8_ALPHA8 (0x8C43) (E.g. from EXT_sRGB)
                RGBA16F (0x881A) (E.g. from EXT_color_buffer_half_float)
- RGBA16F (0x881A) (E.g. from EXT_color_buffer_half_float)

> **Note:** In WebGL 1.0, SRGB8_ALPHA8 requires the extension EXT_sRGB.
                    In WebGL 2.0, SRGB8_ALPHA8 does not require an extension.
                

                    In WebGL 1.0, RGBA16F requires the extension EXT_color_buffer_half_float.
                    In WebGL 2.0, RGBA16F requires the extension EXT_color_buffer_float.

In WebGL 1.0, SRGB8_ALPHA8 requires the extension EXT_sRGB.
                    In WebGL 2.0, SRGB8_ALPHA8 does not require an extension.

In WebGL 1.0, RGBA16F requires the extension EXT_color_buffer_half_float.
                    In WebGL 2.0, RGBA16F requires the extension EXT_color_buffer_float.

OpenGL manages a rectangular viewport as part of its state which defines the placement of
        the rendering results in the drawing buffer. Upon creation of WebGL
        context context, the viewport is initialized to a rectangle with origin at (0, 0)
        and width and height equal to (context.drawingBufferWidth, context.drawingBufferHeight).

A WebGL implementation shall not affect the state of the OpenGL viewport in response to
        resizing of the canvas element.

Rationale: automatically setting the viewport will interfere with applications that set
        it manually. Applications are expected to use onresize handlers to respond to
        changes in size of the canvas and set the OpenGL viewport in turn.

The OpenGL API allows the application to modify the blending modes used during rendering,
        and for this reason allows control over how alpha values in the drawing buffer are
        interpreted; see the premultipliedAlpha parameter in
        the WebGLContextAttributes section.

The HTML Canvas APIs toDataURL and drawImage must respect
        the premultipliedAlpha context creation parameter. When toDataURL
        is called against a Canvas into which WebGL content is being rendered, then if the requested
        image format does not specify premultiplied alpha and the WebGL context has
        the premultipliedAlpha parameter set to true, then the pixel values must be
        de-multiplied; i.e., the color channels are divided by the alpha channel. Note that
        this operation is lossy.

Passing a WebGL-rendered Canvas to the drawImage method
        of CanvasRenderingContext2D may or may not need to modify the the rendered
        WebGL content during the drawing operation, depending on the premultiplication needs of the
        CanvasRenderingContext2D implementation.

When passing a WebGL-rendered Canvas to the texImage2D API, then depending on
        the setting of the premultipliedAlpha context creation parameter of the passed
        canvas and the UNPACK_PREMULTIPLY_ALPHA_WEBGL pixel store parameter of the
        destination WebGL context, the pixel data may need to be changed to or from premultiplied
        form.

## DOM Interfaces

This section describes the interfaces and functionality added to the
        DOM to support runtime access to the functionality described above.

The following types are used in all interfaces in the following section.

The WebGLContextAttributes dictionary contains drawing surface attributes and
        is passed as the second parameter to getContext.

The following list describes each attribute in the WebGLContextAttributes object and its
        use. The default value for each attribute is shown above. The default value is used either
        if no second parameter is passed to getContext, or if a user object is passed
        which has no attribute of the given name.

If the value is true the page compositor will assume the drawing buffer contains
                colors with premultiplied alpha. If the value is false the page compositor will
                assume that colors in the drawing buffer are not premultiplied. This flag is ignored
                if the alpha flag is false.

With premultipliedAlpha:true, any pixels sent to the page
                compositor shall have color values less-than-or-equal-to their alpha value,
                otherwise the colors resulting from compositing such out-of-range pixel values
                are undefined.
                
                    For example, with premultipliedAlpha:true
vec4(1.0, 0.0, 0.0, 0.5) might display as green
                    instead of red, possibly due to optimized packed compositing math overflows.
                    This is left undefined due to the intractible performance impact of requiring
                    consistent behavior.

> **Note:** For example, with premultipliedAlpha:true
vec4(1.0, 0.0, 0.0, 0.5) might display as green
                    instead of red, possibly due to optimized packed compositing math overflows.
                    This is left undefined due to the intractible performance impact of requiring
                    consistent behavior.

See Premultiplied Alpha for more
                information on the effects of the premultipliedAlpha flag.

Provides a hint to the user agent indicating what configuration of GPU is suitable
                for this WebGL context. This may influence which GPU is used in a system with
                multiple GPUs. For example, a dual-GPU system might have one GPU that consumes
                less power at the expense of rendering performance. Note that this property is
                only a hint and a WebGL implementation may choose to ignore it.

WebGL implementations use context lost and restored events to regulate power and
                memory consumption, regardless of the value of this attribute.

The allowed values are:

default

Let the user agent decide which GPU configuration is most suitable. This is the
                    default value.

high-performance

Indicates a request for a GPU configuration that prioritizes rendering
                    performance over power consumption.
                    Developers are encouraged to only specify this value if they believe it
                    is absolutely necessary, since it may significantly decrease battery life on
                    mobile devices.
                    Implementations may decide to initially respect this request and,
                    after some time, lose the context and restore a new context ignoring the
                    request.

> **Note:** Applications that request high-performance should test and
                      maintain robust context loss handling, as User Agents are very likely to decide
                      to lose background high-performance contexts.

Applications that request high-performance should test and
                      maintain robust context loss handling, as User Agents are very likely to decide
                      to lose background high-performance contexts.

low-power

Indicates a request for a GPU configuration that prioritizes power saving over
                    rendering performance. Generally, content should use this if it is unlikely to
                    be constrained by drawing performance; for example, if it renders only one frame
                    per second, draws only relatively simple geometry with simple shaders, or uses a
                    small HTML canvas element. Developers are encouraged to use this value if their
                    content allows, since it may significantly improve battery life on mobile
                    devices.

- An implementation might switch to a software rasterizer if the user's GPU
                    driver is known to be unstable.
                An implementation might require reading back the framebuffer from GPU memory
                    to system memory before compositing it with the rest of the page,
                    significantly reducing performance.
- An implementation might require reading back the framebuffer from GPU memory
                    to system memory before compositing it with the rest of the page,
                    significantly reducing performance.

If the value is true, then the user agent may optimize the rendering of the canvas
                to reduce the latency, as measured from input events to rasterization, by
                desynchronizing the canvas paint cycle from the event loop, bypassing the ordinary
                user agent rendering algorithm, or both. Insofar as this mode involves bypassing the
                usual paint mechanisms, rasterization, or both, it might introduce visible tearing
                artifacts.

> **Note:** The user agent usually renders on a buffer which is not being displayed, quickly
                  swapping it and the one being scanned out for presentation; the former buffer is
                  called back buffer and the latter front buffer. A popular technique for
                  reducing latency is called front buffer rendering, also known as single
                  buffer rendering, where rendering happens inparallel and racily with the
                  scanning out process. This technique reduces the latency at the price of
                  potentially introducing tearing artifacts and can be used to implement in total or
                  part of the desynchronized
                  boolean. [MULTIPLEBUFFERING]

                  The desynchronized boolean can be useful when implementing certain
                  kinds of applications, such as drawing applications, where the latency between
                  input and rasterization is critical.

The user agent usually renders on a buffer which is not being displayed, quickly
                  swapping it and the one being scanned out for presentation; the former buffer is
                  called back buffer and the latter front buffer. A popular technique for
                  reducing latency is called front buffer rendering, also known as single
                  buffer rendering, where rendering happens inparallel and racily with the
                  scanning out process. This technique reduces the latency at the price of
                  potentially introducing tearing artifacts and can be used to implement in total or
                  part of the desynchronized
                  boolean. [MULTIPLEBUFFERING]

The desynchronized boolean can be useful when implementing certain
                  kinds of applications, such as drawing applications, where the latency between
                  input and rasterization is critical.

The WebGLObject interface is the parent interface for all GL objects.

Each WebGLObject has
        an internal invalidated flag, which is initially unset.

Each WebGLObject has a .label attribute, which defaults to "".
        Implementations should use this application-provided label string to improve debugging,
        e.g. in error messages,
        and/or providing the label to any underlying driver where possible to assist in native-level debugging tools.
        Implementations must not change behavior due to a label.

The WebGLBuffer interface represents an OpenGL Buffer Object. The
        underlying object is created as if by calling glGenBuffers
        (OpenGL ES 2.0 §2.9, man page)
        , bound as if by calling glBindBuffer
        (OpenGL ES 2.0 §2.9, man page)
        and marked for deletion as if by calling glDeleteBuffers
        (OpenGL ES 2.0 §2.9, man page)
        .

The WebGLFramebuffer interface represents an OpenGL Framebuffer Object. The
        underlying object is created as if by calling glGenFramebuffers
        (OpenGL ES 2.0 §4.4.1, man page)
        , bound as if by calling glBindFramebuffer
        (OpenGL ES 2.0 §4.4.1, man page)
        and marked for deletion as if by calling glDeleteFramebuffers
        (OpenGL ES 2.0 §4.4.1, man page)
        .

The WebGLProgram interface represents an OpenGL Program Object. The
        underlying object is created as if by calling glCreateProgram
        (OpenGL ES 2.0 §2.10.3, man page)
        , used as if by calling glUseProgram
        (OpenGL ES 2.0 §2.10.3, man page)
        and marked for deletion as if by calling glDeleteProgram
        (OpenGL ES 2.0 §2.10.3, man page)
        .

The WebGLRenderbuffer interface represents an OpenGL Renderbuffer Object. The
        underlying object is created as if by calling glGenRenderbuffers
        (OpenGL ES 2.0 §4.4.3, man page)
        , bound as if by calling glBindRenderbuffer
        (OpenGL ES 2.0 §4.4.3, man page)
        and marked for deletion as if by calling glDeleteRenderbuffers
        (OpenGL ES 2.0 §4.4.3, man page)
        .

The WebGLShader interface represents an OpenGL Shader Object. The
        underlying object is created as if by calling glCreateShader
        (OpenGL ES 2.0 §2.10.1, man page)
        , attached to a Program as if by calling glAttachShader
        (OpenGL ES 2.0 §2.10.3, man page)
        and marked for deletion as if by calling glDeleteShader
        (OpenGL ES 2.0 §2.10.1, man page)
        .

The WebGLTexture interface represents an OpenGL Texture Object. The
        underlying object is created as if by calling glGenTextures
        (OpenGL ES 2.0 §3.7.13, man page)
        , bound as if by calling glBindTexture
        (OpenGL ES 2.0 §3.7.13, man page)
        and marked for deletion as if by calling glDeleteTextures
        (OpenGL ES 2.0 §3.7.13, man page)
        .

The WebGLUniformLocation interface represents the location of a uniform variable
        in a shader program.

The WebGLActiveInfo interface represents the information returned
        from the getActiveAttrib and getActiveUniform calls.

The following attributes are available:

The WebGLShaderPrecisionFormat interface represents the information returned
        from the getShaderPrecisionFormat call.

The following attributes are available:

Vertex, index, texture, and other data is transferred to the WebGL implementation using
        ArrayBuffers,
        Typed Arrays and
        DataViews
        as defined in the ECMAScript specification
[ECMASCRIPT].

Typed Arrays support the creation of interleaved, heterogeneous vertex data; uploading of
        distinct blocks of data into a large vertex buffer object; and most other use cases required
        by OpenGL programs.

The WebGLRenderingContext represents the API allowing
        OpenGL ES 2.0 style rendering into the canvas element.

Before performing the implementation of any method of the WebGLRenderingContext
        interface or any method of an interface returned by the getExtension method,
        the following steps must be performed:

        
 If the [WebGLHandlesContextLoss] extended attribute appears on the called
        method, perform the implementation of the called method, return its result and terminate
        these steps. 
 Let use default return value be false. 
 If the webgl context lost flag is set,
        let use default return value be true.

            
 Otherwise, if any argument to the method is a WebGLObject with
            its invalidated flag set, generate
            an INVALID_OPERATION error and let use default return value be
            true. 

 If use default return value is true, perform the following steps:

            
 If the return type of the called method is any or any nullable type,
            return null. 
 Terminate this algorithm without calling the method implementation. 

 Otherwise, perform the implementation of the called method and return its result.

- If the [WebGLHandlesContextLoss] extended attribute appears on the called
        method, perform the implementation of the called method, return its result and terminate
        these steps.
- Let use default return value be false.
- If the webgl context lost flag is set,
        let use default return value be true.

            
 Otherwise, if any argument to the method is a WebGLObject with
            its invalidated flag set, generate
            an INVALID_OPERATION error and let use default return value be
            true.
- Otherwise, if any argument to the method is a WebGLObject with
            its invalidated flag set, generate
            an INVALID_OPERATION error and let use default return value be
            true.
- If use default return value is true, perform the following steps:

            
 If the return type of the called method is any or any nullable type,
            return null. 
 Terminate this algorithm without calling the method implementation.
- If the return type of the called method is any or any nullable type,
            return null.
- Terminate this algorithm without calling the method implementation.
- Otherwise, perform the implementation of the called method and return its result.

- Otherwise, if any argument to the method is a WebGLObject with
            its invalidated flag set, generate
            an INVALID_OPERATION error and let use default return value be
            true.

- If the return type of the called method is any or any nullable type,
            return null.
- Terminate this algorithm without calling the method implementation.

See the context lost event for further details.

The following attributes are available:

OpenGL ES 2.0 maintains state values for use in rendering. All the calls in this
        group behave identically to their OpenGL counterparts unless otherwise noted.

All queries returning sequences or typed arrays return a new object each time.

If pname is not in the table above, generates an INVALID_ENUM error and returns null.

If pname is IMPLEMENTATION_COLOR_READ_FORMAT
            or IMPLEMENTATION_COLOR_READ_TYPE, and the currently bound framebuffer is
            not framebuffer complete, generates an INVALID_OPERATION error and
            returns null.
            The following pname arguments return a string describing some aspect of the current WebGL implementation:

VERSION
Returns a version or release number of the form WebGL<space>1.0<optional><space><vendor-specific information></optional>.
SHADING_LANGUAGE_VERSION
Returns a version or release number of the form WebGL<space>GLSL<space>ES<space>1.0<optional><space><vendor-specific information></optional>.
VENDOR
Returns the company responsible for this WebGL implementation. This name does not change from release to release.
RENDERER
Returns the name of the renderer. This name is typically specific to a particular configuration of a hardware platform. It does not change from release to release.

See Extension Queries for information on querying the
            available extensions in the current WebGL implementation.
[WebGLHandlesContextLoss] GLenum getError()
            (OpenGL ES 2.0 §2.5, man page)

                If the context's webgl context lost flag is set,
                returns CONTEXT_LOST_WEBGL the first time this method is
                called. Afterward, returns NO_ERROR until the context has
                been restored.
        void hint(GLenum target, GLenum mode)
            (OpenGL ES 2.0 §5.2, man page)
[WebGLHandlesContextLoss] GLboolean isEnabled(GLenum cap)
            (OpenGL ES 2.0 §6.1.1, man page)

            For any isEnabled query, the same boolean value can be obtained via
            getParameter.
            
            Returns false if the context's webgl context lost
            flag is set.
        void lineWidth(GLfloat width)
            (OpenGL ES 2.0 §3.4, man page)

            See NaN Line Width for restrictions specified for WebGL.
        
void pixelStorei(GLenum pname, GLint param)
            (OpenGL ES 2.0 §3.6.1, man page)

                In addition to the parameters in the OpenGL ES 2.0 specification, the WebGL
                specification accepts the parameters UNPACK_FLIP_Y_WEBGL,
                UNPACK_PREMULTIPLY_ALPHA_WEBGL
                and UNPACK_COLORSPACE_CONVERSION_WEBGL. See Pixel
                Storage Parameters for documentation of these parameters.
        void polygonOffset(GLfloat factor, GLfloat units)
            (OpenGL ES 2.0 §3.5.2, man page)
void sampleCoverage(GLclampf value, GLboolean invert)
            (OpenGL ES 2.0 §4.1.3, man page)
void stencilFunc(GLenum func, GLint ref, GLuint mask)
            (OpenGL ES 2.0 §4.1.4, man page)
void stencilFuncSeparate(GLenum face, GLenum func, GLint ref, GLuint mask)
            (OpenGL ES 2.0 §4.1.4, man page)

                See Stencil Separate Mask and Reference Value for information
                on WebGL specific limitations to the allowable argument values.
        void stencilMask(GLuint mask)
            (OpenGL ES 2.0 §4.2.2, man page)

                See Stencil Separate Mask and Reference Value for information
                on WebGL specific limitations to the allowable mask values.
        void stencilMaskSeparate(GLenum face, GLuint mask)
            (OpenGL ES 2.0 §4.2.2, man page)
void stencilOp(GLenum fail, GLenum zfail, GLenum zpass)
            (OpenGL ES 2.0 §4.1.4, man page)
void stencilOpSeparate(GLenum face, GLenum fail, GLenum zfail, GLenum zpass)
            (OpenGL ES 2.0 §4.1.4, man page)

The following pname arguments return a string describing some aspect of the current WebGL implementation:

See Extension Queries for information on querying the
            available extensions in the current WebGL implementation.

Drawing commands can only modify pixels inside the currently bound framebuffer. In
        addition, the viewport and the scissor box affect drawing.

The viewport specifies the affine transformation of x and y from normalized device
        coordinates to window coordinates. The size of the viewport is initially determined
        as specified in section The WebGL Viewport.
        The scissor box defines a rectangle which constrains drawing. When the scissor test is
        enabled only pixels that lie within the scissor box can be modified by drawing commands
        including clear, and primitives can only be drawn inside the intersection
        of the viewport, the currently bound framebuffer, and the scissor box. When the scissor
        test is not enabled primitives can only be drawn inside the intersection of the viewport
        and the currently bound framebuffer.

Buffer objects (sometimes referred to as VBOs) hold vertex attribute data for the GLSL
        shaders.

void bufferSubData(GLenum target, GLintptr offset, AllowSharedBufferSource data)
            (OpenGL ES 2.0 §2.9, man page)

If pname is not in the table above, generates an INVALID_ENUM error.

If an OpenGL error is generated, returns null.

Framebuffer objects provide an alternative rendering target to the drawing buffer. They
        are a collection of color, alpha, depth and stencil buffers and are often used to
        render an image that will later be used as a texture.

If pname is not in the table above, generates an INVALID_ENUM error.

If an OpenGL error is generated, returns null.

Renderbuffer objects are used to provide storage for the individual buffers used in a
        framebuffer object.

If pname is not in the table above, generates an INVALID_ENUM error.

If an OpenGL error is generated, returns null.

Texture objects provide storage and state for texturing operations. If no WebGLTexture is bound
        (e.g., passing null or 0 to bindTexture) then attempts to modify or query the texture object shall
        generate an INVALID_OPERATION error. This is indicated in the functions below.

void compressedTexImage2D(GLenum target, GLint level, GLenum internalformat,
                    GLsizei width, GLsizei height, GLint border, [AllowShared] ArrayBufferView pixels)
                (OpenGL ES 2.0 §3.7.3, man page)

void compressedTexSubImage2D(GLenum target, GLint level,
                    GLint xoffset, GLint yoffset, GLsizei width, GLsizei height, GLenum format, [AllowShared] ArrayBufferView pixels)
                (OpenGL ES 2.0 §3.7.3, man page)

If pname is not in the table above, generates an INVALID_ENUM error.

If an attempt is made to call this function with no WebGLTexture bound (see above), generates an
            INVALID_OPERATION error.

If an OpenGL error is generated, returns null.

void texImage2D(GLenum target, GLint level, GLint internalformat,
                    GLenum format, GLenum type, TexImageSource source) /* May throw DOMException */
            (OpenGL ES 2.0 §3.7.1, man page)

> **Note:** This color space conversion applies to ImageBitmap objects as well, though
            other texture unpack parameters do not apply to ImageBitmaps because they
            are expected to be specified during ImageBitmap construction.
            Implementation experience revealed that it was beneficial to
            perform ImageBitmaps' color space conversion as late as possible when
            uploading to WebGL textures.

> **Note:** Some implementations of HTMLCanvasElement's or OffscreenCanvas's
            CanvasRenderingContext2D store color values internally in premultiplied form. If such a
            canvas is uploaded to a WebGL texture with the
            UNPACK_PREMULTIPLY_ALPHA_WEBGL pixel storage parameter set to false, the
            color channels will have to be un-multiplied by the alpha channel, which is a lossy
            operation. The WebGL implementation therefore can not guarantee that colors with alpha
            < 1.0 will be preserved losslessly when first drawn to a canvas via
            CanvasRenderingContext2D and then uploaded to a WebGL texture when
            the UNPACK_PREMULTIPLY_ALPHA_WEBGL pixel storage parameter is set to false.

void texSubImage2D(GLenum target, GLint level, GLint xoffset, GLint yoffset,
                       GLenum format, GLenum type, TexImageSource source) /* May throw DOMException */
            (OpenGL ES 2.0 §3.7.2, man page)

Rendering with OpenGL ES 2.0 requires the use of shaders, written in OpenGL ES's shading language, GLSL ES.
        Shaders must be loaded with a source string (shaderSource), compiled
        (compileShader) and attached to a program (attachShader) which must be linked
        (linkProgram) and then used (useProgram).

Returns a new object representing the list of shaders attached to the passed program.

Returns null if any OpenGL errors are generated during the execution of this
            function.

If pname is not in the table above, generates an INVALID_ENUM error and returns null.

Returns null if any OpenGL errors are generated during the execution of this
            function.

Returns null if any OpenGL errors are generated during the execution of this
            function.

If pname is not in the table above, generates an INVALID_ENUM error and returns null.

Returns null if any OpenGL errors are generated during the execution of this
            function.

Return a new WebGLShaderPrecisionFormat describing the range and precision
            for the specified shader numeric format. The shadertype value can be FRAGMENT_SHADER or
            VERTEX_SHADER. The precisiontype value can be LOW_FLOAT, MEDIUM_FLOAT, HIGH_FLOAT,
            LOW_INT, MEDIUM_INT or HIGH_INT.

Returns null if any OpenGL errors are generated during the execution of this
            function.

Returns null if any OpenGL errors are generated during the execution of this
            function.

Returns null if any OpenGL errors are generated during the execution of this
            function.

- If the program is linked successfully, the generated executable code is immediately
            installed as part of the current rendering state.
- If the program is not linked successfully, the executable code referenced by the
            current rendering state is immediately invalidated. Further draw calls that utilize the
            current program generate an INVALID_OPERATION error.
            See Current program invalidated upon unsuccessful
            link.

Values used by the shaders are passed in as uniforms or vertex attributes.

Returns null if any OpenGL errors are generated during the execution of this
            function.

Returns null if any OpenGL errors are generated during the execution of this
            function.

All queries returning sequences or typed arrays return a new object each time.

Returns null if any OpenGL errors are generated during the execution of this
            function.

All queries returning sequences or typed arrays return a new object each time.

If pname is not in the table above, generates an INVALID_ENUM error.

If an OpenGL error is generated, returns null.

void uniform[1234][fi](WebGLUniformLocation? location, ...)

void uniform[1234][fi]v(WebGLUniformLocation? location, ...)
            void uniformMatrix[234]fv(WebGLUniformLocation? location, GLboolean transpose, ...)
            (OpenGL ES 2.0 §2.10.4, man page)

            Each of the uniform* functions above sets the specified uniform or uniforms to the
            values provided. If the passed location is not null and was not obtained
            from the currently used program via an earlier call to getUniformLocation,
            an INVALID_OPERATION error will be generated. If the passed
            location is null, the data passed in will be silently ignored and
            no uniform variables will be changed.
            
            If the array passed to any of the vector forms (those ending in v) has an
            invalid length, an INVALID_VALUE error will be generated. The length is
            invalid if it is too short for or is not an integer multiple of the assigned type.

            Performance problems have been observed on some implementations when
            using uniform1i to update sampler uniforms. To change the texture
            referenced by a sampler uniform, binding a new texture to the texture unit referenced
            by the uniform should be preferred over using uniform1i to update the
            uniform itself.
void vertexAttrib[1234]f(GLuint index, ...)
void vertexAttrib[1234]fv(GLuint index, ...)
            (OpenGL ES 2.0 §2.7, man page)

           Sets the vertex attribute at the passed index to the given constant value. Values set via the
           vertexAttrib are guaranteed to be returned from the getVertexAttrib function
           with the CURRENT_VERTEX_ATTRIB param, even if there have been intervening calls to
           drawArrays or drawElements.
           
           If the array passed to any of the vector forms (those ending in v) is too
           short, an INVALID_VALUE error will be generated.

       void vertexAttribPointer(GLuint index, GLint size, GLenum type,
                            GLboolean normalized, GLsizei stride, GLintptr offset)
            (OpenGL ES 2.0 §2.8, man page)

            Assign the WebGLBuffer object currently bound to the ARRAY_BUFFER target to the vertex
            attribute at the passed index. Size is number of components per attribute. Stride and
            offset are in units of bytes. Passed stride and offset must be appropriate for the
            passed type and size or an INVALID_OPERATION error will be generated;
            see Buffer Offset and Stride Requirements. If
            offset is negative, an INVALID_VALUE error will be generated. If no
            WebGLBuffer is bound to the ARRAY_BUFFER target and offset is non-zero,
            an INVALID_OPERATION error will be generated. In WebGL, the maximum
            supported stride is 255; see  Vertex Attribute Data Stride.

void uniformMatrix[234]fv(WebGLUniformLocation? location, GLboolean transpose, ...)
            (OpenGL ES 2.0 §2.10.4, man page)

> **Note:** Performance problems have been observed on some implementations when
            using uniform1i to update sampler uniforms. To change the texture
            referenced by a sampler uniform, binding a new texture to the texture unit referenced
            by the uniform should be preferred over using uniform1i to update the
            uniform itself.

void vertexAttrib[1234]f(GLuint index, ...)

void vertexAttrib[1234]fv(GLuint index, ...)
            (OpenGL ES 2.0 §2.7, man page)

OpenGL ES 2.0 has several calls which are allowed to
        write to the currently bound (draw) framebuffer.
        WebGL categorizes all such calls as [Draw Operations].

Furthermore, rendering can
        be directed to the drawing buffer or to a Framebuffer object. When rendering is
        directed to the drawing buffer, making any of the rendering calls shall
        cause the drawing buffer to be presented to the HTML page compositor at the start
        of the next compositing operation.

These include, but (due to additions in extensions or in WebGL 2.0) are not limited to:
        
clear
drawArrays
drawElements

        For instance,
        ANGLE_instanced_arrays
        adds drawArraysInstancedANGLE, and
        WebGL 2.0
        adds drawArraysInstanced.

- clear
- drawArrays
- drawElements

If any one of these calls attempts to draw to a missing attachment of a complete framebuffer,
        nothing is drawn to that attachment and no error is generated
        per Drawing to a Missing Attachment.

OpenGL ES 2.0 has several calls which are allowed to
        read from the currently bound (read) framebuffer.
        WebGL categorizes all such calls as [Read Operations].

These include, but (due to additions in extensions or in WebGL 2.0) are not limited to:
        
copyTexImage2D
copyTexSubImage2D
readPixels

- copyTexImage2D
- copyTexSubImage2D
- readPixels

Occurrences such as power events on mobile devices may cause the WebGL rendering context to
        be lost at any time and require the application to rebuild it;
        see WebGLContextEvent for more details. The
        following method assists in detecting context lost events.

An implementation of WebGL must not support any additional parameters, constants or functions
        without first enabling that functionality through the extension mechanism. The
        getSupportedExtensions function returns an array of the extension strings
        supported by this implementation. An extension is enabled by passing one of those strings to
        the getExtension function. This call returns an object which contains any
        constants or functions defined by that extension. The definition of that object is specific
        to the extension and must be defined by the extension specification.

Once an extension is enabled, it is only disabled if the WebGL rendering context is lost (see
        below), with the exception of the "WEBGL_lose_context" extension which remains active through
        any loss of context. Any objects referenced by a disabled extension, such as the object returned
        by getExtension, are no longer associated with the WebGL rendering context. Any
        extension objects that derive from WebGLObject have their
        invalidated flag set to true. Behavior of
        extensions' methods after context loss is defined by the steps in the
        section "The WebGL context".
    
        There are no other mechanisms to disable an extension.
    

        Multiple calls to getExtension with the same extension string, taking into account
        case-insensitive comparison, must return the same object as long as the extension is enabled. An
        attempt to use any features of an extension without first calling getExtension to enable it must
        generate an appropriate GL error and must not make use of the feature.
    

        This specification does not define any extensions. A separate WebGL
        extension registry defines extensions that may be supported by a particular WebGL
        implementation.
    

sequence<DOMString>? getSupportedExtensions()
        
            Returns a list of all the supported extension strings.

        object? getExtension(DOMString name)
        
            Returns an object if, and only if, name is
            an ASCII
            case-insensitive match [HTML] for one of the names returned
            from getSupportedExtensions; otherwise, returns null. The
            object returned from getExtension contains any constants or functions
            provided by the extension. A returned object may have no constants or functions if the
            extension does not define any, but a unique object must still be returned. That object
            is used to indicate that the extension has been enabled.
    

WebGLContextEvent

        WebGL generates a WebGLContextEvent event in response to important changes in status of a
        WebGL rendering context. Events are sent using the DOM Event System [DOM3EVENTS],
        and are dispatched to the HTMLCanvasElement or OffscreenCanvas associated with the WebGL rendering context.
        The types of status changes that can trigger a WebGLContextEvent event are 
        the loss of the context, the restoration of the context, and
         the inability to create a context.
    

        To fire a WebGL context event named e means
        that an event using
        the WebGLContextEvent interface, with
        its type
        attribute [DOM4] initialized to e, its
        cancelable attribute initialized to true, and
        its isTrusted
        attribute [DOM4] initialized to true, is to
        be dispatched at the
        given object.
    

[Exposed=(Window,Worker)]
interface WebGLContextEvent : Event {
    constructor(DOMString type, optional WebGLContextEventInit eventInit = {});
    readonly attribute DOMString statusMessage;
};

// EventInit is defined in the DOM4 specification.
dictionary WebGLContextEventInit : EventInit {
    DOMString statusMessage = "";
};

    The task
    source for
    all tasks queued [HTML]
    in this section is the WebGL task source.
    
Attributes

        The following attributes are available:
    

statusMessage of type DOMString

            A string containing additional information, or the empty string if no additional information
            is available.
    
The Context Lost Event

        When the user agent detects that the drawing buffer associated with
        a WebGLRenderingContext context has been lost, it must run the
        following steps:

        
 Let canvas be the context's
canvas. 
 If context's webgl context lost flag
        is set, abort these steps. 
 Set context's webgl context lost
        flag. 
 Set the invalidated flag of
        each WebGLObject instance created by this context. 
 Disable all extensions except "WEBGL_lose_context". 
 Queue a task to
        perform the following steps:

            
 Fire a WebGL context event named
            "webglcontextlost" at canvas, with its statusMessage attribute set
            to "". 
 If the
            event's canceled
            flag is not set, abort these steps. 
 Perform the following steps asynchronously. 
 Await a restorable drawing buffer. 
 Queue a task to restore the drawing
            buffer for context. 

        A WebGLObject created while the context is lost
        (e.g. a WebGLBuffer via createBuffer())
        begins life with its invalidated flag set.
    

        The following code prevents the default behavior of the webglcontextlost
        event and enables the webglcontextrestored event to be delivered:
    canvas.addEventListener("webglcontextlost", function(e) { e.preventDefault(); }, false); 

The Context Restored Event

        When the user agent is to restore the drawing
        buffer for a WebGLRenderingContext context, it must run the
        following steps:

        
 Let canvas be the canvas object associated with context.

         If context's webgl context lost flag is
        not set, abort these steps.

         Create a drawing buffer using the
        settings specified in context's context
        creation parameters, and associate the drawing buffer with context,
        discarding any previous drawing buffer.

         Clear context's webgl context lost
        flag.

         Reset context's OpenGL error state.

         Fire a WebGL context event named
        "webglcontextrestored" at canvas, with its statusMessage attribute set
        to "".

        

        Once the context is restored, WebGL resources such as textures and buffers that were created
        before the context was restored are no longer valid.
        Previously enabled extensions are not restored.
        The application will want to restore all modified state and destroyed extensions and resources.
    

        The following code illustrates how an application can handle context loss and restoration:
function initializeGame() {
  initializeWorld();
  initializeResources();
}

function initializeResources() {
  initializeShaders();
  initializeBuffers();
  initializeTextures();

  // ready to draw, start the main loop
  renderFrame();
}

function renderFrame() {
  updateWorld();
  drawSkyBox();
  drawWalls();
  drawMonsters();

  requestId = window.requestAnimationFrame(
      renderFrame, canvas);
}

canvas.addEventListener(
    "webglcontextlost", function (event) {

  // inform WebGL that we handle context restoration
  event.preventDefault();

  // Stop rendering
  window.cancelAnimationFrame(requestId);
}, false);

canvas.addEventListener(
    "webglcontextrestored", function (event) {

  initializeResources();
}, false);

initializeGame();

The Context Creation Error Event

        When the user agent is to fire a WebGL
        context creation error at a canvas, it must perform the following steps:

        
 Fire a WebGL context event named
        "webglcontextcreationerror" at canvas, optionally with its statusMessage
        attribute set to a platform dependent string about the nature of the failure. 

        The following code illustrates how an application can retrieve information about context creation failure:

var errorInfo = "";
function onContextCreationError(event) {

  canvas.removeEventListener(
     "webglcontextcreationerror",
     onContextCreationError, false);

  errorInfo = e.statusMessage || "Unknown";
}

canvas.addEventListener(
    "webglcontextcreationerror",
    onContextCreationError, false);

var gl = canvas.getContext("webgl");
if(!gl) {
  alert("A WebGL context could not be created.\nReason: " +
        errorInfo);
}

Differences Between WebGL and OpenGL ES 2.0

This section describes changes made to the WebGL API relative to the OpenGL ES 2.0 API to improve
portability across various operating systems and devices.

Buffer Object Binding

In the WebGL API, a given buffer object may only be bound to one of the ARRAY_BUFFER or
ELEMENT_ARRAY_BUFFER binding points in its lifetime. This restriction implies that a
given buffer object may contain either vertices or indices, but not both.

The type of a WebGLBuffer is initialized the first time it is passed as an argument
to bindBuffer. A subsequent call to bindBuffer which attempts to bind the
same WebGLBuffer to the other binding point will generate an INVALID_OPERATION error, and
the state of the binding point will remain untouched.

No Client Side Arrays

The WebGL API does not support client-side arrays.

If a vertex attribute is enabled as an array via enableVertexAttribArray but no buffer
is bound to that attribute (generally via bindBuffer and
vertexAttribPointer), then draw commands (drawArrays or
drawElements) will generate an INVALID_OPERATION error.

If an indexed draw command (drawElements) is called and no WebGLBuffer is
bound to the ELEMENT_ARRAY_BUFFER binding point, an INVALID_OPERATION
error is generated.

If vertexAttribPointer is called without a WebGLBuffer bound to the
ARRAY_BUFFER binding point, and offset is non-zero, an
INVALID_OPERATION error is generated.

    Allowing setting VERTEX_ATTRIB_ARRAY_BUFFER_BINDING to null even though client-side arrays
    are never supported allows for clearing the binding to its original state, which isn't
    strictly possible otherwise.
    
    This also matches the behavior in OpenGL ES 3.0.5 [GLES30] p25 for
    non-default VAO objects.

No Default Textures

The WebGL API does not support default textures. A non-null WebGLTexture object must be
bound in order for texture-related operations and queries to succeed.

No Shader Binaries

Accessing binary representations of compiled shaders is not supported in the WebGL API. This
includes the OpenGL ES 2.0 ShaderBinary entry point. In addition, querying shader
binary formats and the availability of a shader compiler via getParameter is not
supported in the WebGL API.

All WebGL implementations must implicitly support an on-line shader compiler.

Buffer Offset and Stride Requirements

The offset arguments to drawElements and vertexAttribPointer,
and the stride argument to vertexAttribPointer, must be a multiple of the
size of the data type passed to the call, or an INVALID_OPERATION error is generated.

        This enforces the following requirement from OpenGL ES 2.0.25
        [GLES20] p24:
    

        "Clients must align data elements consistent with the requirements of the client
        platform, with an additional base-level requirement that an offset within a buffer
        to a datum comprising N basic machine units be a multiple of
        N."
    

In addition the offset argument to drawElements must be non-negative or
an INVALID_VALUE error is generated.

Enabled Vertex Attributes and Range Checking

It is possible for draw commands to request data outside the bounds of a WebGLBuffer by calling a
drawing command that requires fetching data for an active vertex attribute, when it is enabled as an
array, either directly (drawArrays), or indirectly from an indexed draw
(drawElements).
If this occurs, then one of the following behaviors will result:

 The WebGL implementation may generate an INVALID_OPERATION error and draw no geometry. 
 Out-of-range vertex fetches may return any of the following values:

  
 Values from anywhere within the buffer object. 
 Zero values, or (0,0,0,x) vectors for vector reads where x is a
       valid value represented in the type of the vector components and may
       be any of:

       
0, 1, or the maximum representable positive integer value, for
         signed or unsigned integer components
0.0 or 1.0, for floating-point components

This behavior replicates that defined in [KHRROBUSTACCESS].

If a vertex attribute is enabled as an array, a buffer is bound to that attribute, but the attribute
is not consumed by the current program, then regardless of the size of the bound buffer, it will not
cause any error to be generated during a call to drawArrays
or drawElements.

    Out-of-bounds fetches from the index buffer

Calling an indexed drawing command (drawElements) that fetches index elements outside
the bounds of ELEMENT_ARRAY_BUFFER will result in an INVALID_OPERATION error.

    Framebuffer Object Attachments

WebGL adds the DEPTH_STENCIL_ATTACHMENT framebuffer object attachment point and
the DEPTH_STENCIL renderbuffer internal format. To attach both depth and stencil
buffers to a framebuffer object, call renderbufferStorage with
the DEPTH_STENCIL internal format, and then call framebufferRenderbuffer
with the DEPTH_STENCIL_ATTACHMENT attachment point.

A renderbuffer attached to the DEPTH_ATTACHMENT attachment point must be allocated with
the DEPTH_COMPONENT16 internal format. A renderbuffer attached to
the STENCIL_ATTACHMENT attachment point must be allocated with
the STENCIL_INDEX8 internal format. A renderbuffer attached to
the DEPTH_STENCIL_ATTACHMENT attachment point must be allocated with
the DEPTH_STENCIL internal format.

In the WebGL API, it is an error to concurrently attach renderbuffers to the following combinations
of attachment points:

 DEPTH_ATTACHMENT + DEPTH_STENCIL_ATTACHMENT
 STENCIL_ATTACHMENT + DEPTH_STENCIL_ATTACHMENT
 DEPTH_ATTACHMENT + STENCIL_ATTACHMENT

If any of the constraints above are violated, then:

 checkFramebufferStatus must return FRAMEBUFFER_UNSUPPORTED.
 [Draw Operations] and [Read Operations],
     which either draw to or read from the framebuffer, must generate
     an INVALID_FRAMEBUFFER_OPERATION error and return early, leaving the contents of
     the framebuffer, destination texture or destination memory untouched.

The following combinations of framebuffer object attachments, when all of the attachments are
framebuffer attachment complete, non-zero, and have the same width and height, must result in the
framebuffer being framebuffer complete:

 COLOR_ATTACHMENT0 = RGBA/UNSIGNED_BYTE texture
 COLOR_ATTACHMENT0 = RGBA/UNSIGNED_BYTE texture + DEPTH_ATTACHMENT = DEPTH_COMPONENT16 renderbuffer
 COLOR_ATTACHMENT0 = RGBA/UNSIGNED_BYTE texture + DEPTH_STENCIL_ATTACHMENT = DEPTH_STENCIL renderbuffer

Texture Upload Width and Height

Unless width and height parameters are explicitly specified, the width
and height of the texture set by texImage2D and the width and height of the
sub-rectangle updated by texSubImage2D are determined based on the uploaded
TexImageSource source object:

source of type ImageData

            The width and height of the texture are set to the current values of the width and
            height properties of the ImageData object, representing the actual pixel width and height
            of the ImageData object.
        source of type HTMLImageElement

            If a bitmap is uploaded, the width and height of the texture are set to the width and
            height of the uploaded bitmap in pixels. If an SVG image is uploaded, the width and
            height of the texture are set to the current values of the width and height properties
            of the HTMLImageElement object.
        source of type HTMLCanvasElement or
          OffscreenCanvas

            The width and height of the texture are set to the current values of the width and
            height properties of the HTMLCanvasElement or OffscreenCanvas
            object.
        source of type HTMLVideoElement or VideoFrame[WEBCODECS]

            The width and height of the texture are set to the width and height of the uploaded
            frame of the video in pixels.
    
Pixel Storage Parameters

The WebGL API supports the following additional parameters to pixelStorei.

UNPACK_FLIP_Y_WEBGL of type boolean
If set, then during any subsequent calls to texImage2D or
texSubImage2D, the source data is flipped along the vertical axis, so that conceptually
the last row is the first one transferred. The initial value is false. Any non-zero
value is interpreted as true.

UNPACK_PREMULTIPLY_ALPHA_WEBGL of type boolean
If set, then during any subsequent calls to texImage2D
or texSubImage2D, the alpha channel of the source data, if present, is multiplied into
the color channels during the data transfer. The initial value is false. Any non-zero
value is interpreted as true.

UNPACK_COLORSPACE_CONVERSION_WEBGL of type unsigned long
If set to BROWSER_DEFAULT_WEBGL, then the browser's default colorspace conversion
(e.g. converting a display-p3 image to srgb)
is applied during subsequent texture data upload calls
(e.g. texImage2D and texSubImage2D) that take an argument of TexImageSource.

The precise conversions may be specific to both the browser and file type.
If set to NONE, no colorspace conversion is applied, other than conversion to RGBA.
(For example, a rec709 YUV video is still converted to rec709 RGB data, but not then converted to e.g. srgb RGB data)
The initial value is BROWSER_DEFAULT_WEBGL.

If the TexImageSource is an ImageBitmap, then these three parameters will
be ignored. Instead the equivalent
ImageBitmapOptions should be used to
create an ImageBitmap with the desired format.

Reading Pixels Outside the Framebuffer

For [Read Operations],
reads from out-of-bounds pixels sub-areas do not touch their corresponding destination sub-areas.

WebGL (behaves as if it) pre-initializes resources to zeros.
Therefore for example copyTexImage2D will have zeros in sub-areas that correspond to
out-of-bounds framebuffer reads.

Stencil Separate Mask and Reference Value

In the WebGL API, if stencil testing is enabled and the currently bound framebuffer has a stencil buffer,
then it is illegal to draw while any of the following cases are true.
Doing so will generate an INVALID_OPERATION error.

(STENCIL_WRITEMASK & maxStencilValue) != (STENCIL_BACK_WRITEMASK & maxStencilValue)

(as specified by stencilMaskSeparate for the mask parameter associated with the FRONT and BACK values of face, respectively)

(STENCIL_VALUE_MASK & maxStencilValue) != (STENCIL_BACK_VALUE_MASK & maxStencilValue)

(as specified by stencilFuncSeparate for the mask parameter associated with the FRONT and BACK values of face, respectively)

clamp(STENCIL_REF, 0, maxStencilValue) != clamp(STENCIL_BACK_REF, 0, maxStencilValue)

(as specified by stencilFuncSeparate for the ref parameter associated with the FRONT and BACK values of face, respectively)

where maxStencilValue is ((1 << s) - 1),
where s is the number of stencil bits in the draw framebuffer.
(When no stencil bits are present, these checks always pass.)

Vertex Attribute Data Stride

The WebGL API supports vertex attribute data strides up to 255 bytes. A call to
vertexAttribPointer will generate an INVALID_VALUE error if the value for
the stride parameter exceeds 255.

Viewport Depth Range

The WebGL API does not support depth ranges with where the near plane is mapped to a value greater
than that of the far plane. A call to depthRange will generate an
INVALID_OPERATION error if zNear is greater than zFar.

Blending With Constant Color

In the WebGL API, constant color and constant alpha cannot be used together as source and
destination factors in the blend function. A call to blendFunc will generate an
INVALID_OPERATION error if one of the two factors is set to CONSTANT_COLOR
or ONE_MINUS_CONSTANT_COLOR and the other to CONSTANT_ALPHA or
ONE_MINUS_CONSTANT_ALPHA. A call to blendFuncSeparate will generate an
INVALID_OPERATION error if srcRGB is set to CONSTANT_COLOR
or ONE_MINUS_CONSTANT_COLOR and dstRGB is set to CONSTANT_ALPHA or
ONE_MINUS_CONSTANT_ALPHA or vice versa.

Fixed point support

The WebGL API does not support the GL_FIXED data type.

    GLSL Constructs

Per Supported GLSL Constructs, identifiers starting with
"webgl_" and "_webgl_" are reserved for use by WebGL.

Extension Queries

In the OpenGL ES 2.0 API, the available extensions are determined by calling
glGetString(GL_EXTENSIONS), which returns a space-separated list of extension strings.
In the WebGL API, the EXTENSIONS enumerant has been removed.
Instead, getSupportedExtensions must be called to determine the set of available
extensions.

Compressed Texture Support

    The core WebGL specification does not define any supported compressed texture formats.
    Therefore, in the absence of any other extensions being enabled:

    
 The compressedTexImage2D
           and compressedTexSubImage2D methods
           generate an INVALID_ENUM error. 
 Calling getParameter with the
           argument COMPRESSED_TEXTURE_FORMATS returns a zero-length array (of
           type Uint32Array). 

    WebGL implementations should only expose compressed texture formats that are more efficient than the uncompressed form.

Maximum GLSL Token Size

    The GLSL ES spec [GLES20GLSL] does not define a limit to the
    length of tokens. WebGL requires support of tokens up to 256 characters in length. Shaders
    containing tokens longer than 256 characters must fail to compile.

Characters Outside the GLSL Source Character Set

    WebGL supports passing any HTML DOMString [DOMSTRING] to shaderSource without error.
    However during shader compilation, after GLSL preprocessing and comment stripping, all remaining characters MUST be within the character set of [GLES20GLSL].
    Otherwise, the shader MUST fail to compile.

    In particular, this allows for:
    
Non-ASCII unicode in comments
            // 你好
Invalid characters in preprocessor-eliminated blocks
#ifdef __cplusplus
#line 42 "foo.glsl"
#endif
            (The double-quote character is outside the GLSL character set, but since it is removed by preprocessing, this is allowed in shader sources)
    

        The GLSL ES spec [GLES20GLSL] defines the source character set for the OpenGL ES shading language as a subset of ISO/IEC 646:1991, commonly called ASCII [ASCII].
        Some GLSL implementations disallow any characters outside the ASCII range, even in comments.
        While browsers MUST correctly handle preprocessing the full DOMString character set, WebGL implementations generally must ensure that the shader source sent to a GLSL driver only contains ASCII for safety.
        Implementations SHOULD preserve line numbers for debugging purposes, potentially by inserting blank lines as needed.
    

    If a string containing a character not in this set is passed to any of the other shader-related entry points
    bindAttribLocation,
    getAttribLocation,
    or getUniformLocation,
    an INVALID_VALUE error will be generated.

Maximum Nesting of Structures in GLSL Shaders

    WebGL imposes a limit on the nesting of structures in GLSL shaders. Nesting occurs when a field
    in a struct refers to another struct type; the GLSL ES
    spec [GLES20GLSL] forbids embedded structure definitions. The
    fields in a top-level struct definition have a nesting level of 1.

    WebGL requires support of a structure nesting level of 4. Shaders containing structures nested
    more than 4 levels deep must fail to compile.

Maximum Uniform and Attribute Location Lengths

    WebGL imposes a limit of 256 characters on the lengths of uniform and attribute locations.

String Length Queries

    In the WebGL API, the enumerants INFO_LOG_LENGTH, SHADER_SOURCE_LENGTH,
    ACTIVE_UNIFORM_MAX_LENGTH, and ACTIVE_ATTRIBUTE_MAX_LENGTH have been removed. In
    the OpenGL ES 2.0 API, these enumerants are needed to determine the size of buffers passed to calls
    like glGetActiveAttrib. In the WebGL API, the analogous calls (getActiveAttrib,
    getActiveUniform, getProgramInfoLog, getShaderInfoLog, and
    getShaderSource) all return DOMString.

Texture Type in TexSubImage2D Calls

    In the WebGL API, the type argument passed to texSubImage2D must match the
    type used to originally define the texture object (i.e., using texImage2D).

Packing Restrictions for Uniforms and Varyings

    The OpenGL ES Shading Language, Version 1.00 [GLES20GLSL],
    Appendix A, Section 7 "Counting of Varyings and Uniforms" defines a conservative algorithm for
    computing the storage required for all of the uniform and varying variables in a shader. The
    GLSL ES specification requires that if the packing algorithm defined in Appendix A succeeds,
    then the shader must succeed compilation on the target platform. The WebGL API further requires
    that if the packing algorithm fails either for the uniform variables of a shader or for the
    varying variables of a program, compilation or linking must fail.

    Instead of using a fixed size grid of registers, the number of rows in the target architecture
    is determined in the following ways:

    
 when counting uniform variables in a vertex shader: getParameter(MAX_VERTEX_UNIFORM_VECTORS)
 when counting uniform variables in a fragment shader: getParameter(MAX_FRAGMENT_UNIFORM_VECTORS)
 when counting varying variables: getParameter(MAX_VARYING_VECTORS)

        The text above defines the circumstances under which compilation or linking of a shader or
        program must fail due to the constraints enforced by the packing algorithm. It is not
        guaranteed that a shader which uses more variables than the minimum required amount whose
        variables pack successfully according to this algorithm will compile successfully.
        Inefficiencies have been observed in implementations, including expansion of scalar arrays
        to consume multiple columns. Developers should avoid relying heavily upon automatic packing
        of multiple variables into columns. Instead, define larger variables (like vec4) and
        explicitly pack values into the rightmost columns.
    

Feedback Loops Between Textures and the Framebuffer

    In the OpenGL ES 2.0 API, it's possible to make calls that both write to and read from
    the same texture, creating a feedback loop.
    It specifies that where these feedback loops exist, undefined behavior results.

    In the WebGL API, such operations that would cause such feedback loops (by the definitions
    in the OpenGL ES 2.0 spec) will instead generate an INVALID_OPERATION error.

Reading From a Missing Attachment

    In the OpenGL ES 2.0 API, it is not specified what happens when a command tries to source
    data from a missing attachment, such as ReadPixels of color data from a complete framebuffer
    that does not have a color attachment.

    In the WebGL API, any [Read Operations] that require data from an attachment that is missing will
    generate an INVALID_OPERATION error.

Drawing To a Missing Attachment

    In the OpenGL ES 2.0 API, it is not specified what happens when a command tries to draw
    to a missing attachment, such as clearing a draw buffer from a complete framebuffer
    that does not have a color attachment.

    In the WebGL API, any [Draw Operations]
    that draw to an attachment that is missing will draw
    nothing to that attachment. No error is generated.

NaN Line Width

    In the WebGL API, if the width parameter passed to lineWidth is set
    to NaN, an INVALID_VALUE error is generated and the line width is not changed.

Attribute Aliasing

    It is possible for an application to bind more than one attribute name to the
    same location. This is referred to as aliasing. When more than one attributes that
    are aliased to the same location are active in the executable program,
    linkProgram should fail.

Initial value for gl_Position

    The GLSL ES [GLES20GLSL] spec leaves the value of
    gl_Position as undefined unless it is written to in a vertex shader. WebGL guarantees
    that gl_Position's initial value is (0,0,0,0).

GLSL ES Global Variable Initialization

    The GLSL ES 1.00 [GLES20GLSL] spec restricts global variable
    initializers to be constant expressions. In the WebGL API, it is allowed to use other global
    variables not qualified with the const qualifier and uniform values in global
    variable initializers in GLSL ES 1.00 shaders. Global variable initializers must be global
    initializer expressions, which are defined as one of:

a constant expression
a user-defined global variable
a uniform

    an expression formed by an operator on operands that are global initializer expressions,
    including getting an element of a global initializer vector or global initializer matrix,
    or a field of a global initializer structure

a constructor whose arguments are all global initializer expressions

    a built-in function call whose arguments are all global initializer expressions, with the
    exception of the texture lookup functions

    The following may not be used in global initializer expressions:

User-defined functions
Attributes and varyings
Built-in variables with the exception of constant expressions
Global variables as l-values in an assignment or other operation

    Compilers should generate a warning when a global variable initializer is in violation of the
    unmodified GLSL ES spec i.e. when a global variable initializer is not a constant expression.

    This behavior has existed in WebGL implementations for several years. Fixing this behavior to be
    consistent with the GLSL ES specification would have a large compatibility impact with existing
    content.

GLSL ES Preprocessor "defined" Operator

    The C++ standard, which the GLSL ES preprocessor specification refers to, has undefined behavior
    when the defined operator is generated by macro replacement when parsing the
    controlling expression of an #if or #elif directive. When shader code
    processed by the WebGL API generates the token defined during macro replacement
    inside a preprocessor expression, that must result in a compiler error.

    This has no effect on macro expansion outside preprocessor directives that handle the
    defined operator.

    Using defined as a macro name also has undefined behavior in the C++ standard. In
    the WebGL API, using defined as a macro name must result in a compiler error.

    Behavior of the WebGL API should be consistent in cases where the native API spec allows undefined
    behavior.

GLSL ES #extension directive location

    The GLSL ES 1.00 [GLES20GLSL] specification mandates that
    #extension directives must occur before any non-preprocessor tokens unless the
    extension specification says otherwise. In the WebGL API, #extension directives
    may always occur after non-preprocessor tokens in GLSL ES 1.00 shaders. The scope of
    #extension directives in GLSL ES 1.00 shaders is always the whole shader, and
    #extension directives that occur later override those seen earlier for the whole
    shader.

    Letting extensions determine where the #extension directives should be placed has
    resulted in a lot of room for interpretation in the spec. In practice GLES implementations have
    not enforced the rule that's written in the GLSL ES spec, and neither have WebGL
    implementations, so relaxing the rule is the only way to make the spec well-defined while being
    compatible with existing content.

Completeness of Cube Map Framebuffer Attachments

    In the WebGL API, a face of a cube map that is not cube complete is not framebuffer attachment
    complete. Querying framebuffer status when a face of an incomplete cube map is attached must
    return FRAMEBUFFER_INCOMPLETE_ATTACHMENT.

    APIs that WebGL is implemented on, including recent OpenGL core
    versions and OpenGL ES 3.0 and newer, have a requirement that cube
    map faces used as a framebuffer attachment must be part of a cube
    complete cube map. See for
    example OpenGL
    ES 3.0.4 §4.4.4 "Framebuffer Completeness", subsection
    "Framebuffer Attachment Completeness".

Transferring vertices when current program is null

    Any command that transfers vertices to the GL generates INVALID_OPERATION if the
    CURRENT_PROGRAM is null. This includes drawElements and
    drawArrays.

Fragment shader output

    If a fragment shader writes to neither gl_FragColor nor gl_FragData,
    the values of the fragment colors following shader execution are untouched.

Initial values for GLSL local and global variables

    The GLSL ES [GLES20GLSL] spec leaves the value of
    local and global variables as undefined unless they are initialized by the
    shader. WebGL guarantees that such variables are initialized to zero:
    0.0, vec4(0.0), 0, false, etc.

Vertex attribute conversions from normalized signed integers to floating point

    The OpenGL ES 2.0 spec [GLES20] section 2.1.2 "Data Conversions",
    subsection "Conversion from Integer to Floating-Point" defines conversion from a normalized
    signed integer c, where the bit width of the type is b, to floating-point
    value f as:

    
f = (2*c + 1) / (2^b - 1)

    During conversions of signed normalized vertex attributes to floating point, WebGL 1.0
    implementations may optionally use this conversion rule, which preserves zeros:

    
f = max(c / (2^(b - 1) - 1), -1.0)
    

    Some APIs on which WebGL 1.0 is built on use the second rule, and since this conversion is done
    in fixed-function hardware, it is not possible to emulate one behavior or the other. This
    difference in behavior does not affect most applications, so a query to determine which behavior
    is being used has not been added to the WebGL rendering context.
    

Uniform and attribute name collisions

    If any of the shaders attached to a WebGL program declare a uniform that has the same name as a
    statically used vertex attribute, program linking should fail.

    This behavior differs from one specified in GLSL ES 3.00.6 section 12.47.

    WebGL implementations have enforced this behavior for several years now, due to that some OpenGL
    drivers don't accept uniforms and vertex attributes with the same name.

Wide point primitive clipping

POINTS primitives may or may not be discarded if the vertex lies outside the clip
    volume, but within the near and far clip planes.

        Clipping of wide points works differently in GLES and GL, and this difference in behavior is
        prohibitive to work around in implementations.
    

OpenGL ES 2.0.25 p46:
        
            If the primitive under consideration is a point, then clipping discards it if it lies
            outside the near or far clip plane; otherwise it is passed unchanged.
        

OpenGL 3.2 Core p97:
        
            If the primitive under consideration is a point, then clipping passes it unchanged if it
            lies within the clip volume; otherwise, it is discarded.
        

Current program invalidated upon unsuccessful link

    In the WebGL API, if the program passed to linkProgram is also the current program
    object in use as defined by useProgram, and the link is unsuccessful, then the
    executable code referenced by the current rendering state is immediately invalidated. Further
    draw calls that utilize the current program generate an INVALID_OPERATION error.

        Rejecting draw calls eagerly against programs whose relink has failed makes WebGL
        implementations more robust. The OpenGL ES API's behavior is that the current executable is
        preserved until the current program is changed. Correctly implementing this behavior in all
        scenarios is challenging, and has led to security bugs.
    

References

[CANVAS]

            HTML5: The Canvas Element,
            World Wide Web Consortium (W3C).
        
[OFFSCREENCANVAS]

            HTML Living Standard - The OffscreenCanvas interface,
            WHATWG.
        
[CANVASCONTEXTS]

            Canvas Context Registry,
            WHATWG.
        
[ECMASCRIPT]

            ECMAScript® 2015 Language Specification,
            Ecma International, 2015.
        
[GL32CORE]

            The OpenGL® Graphics System: A Specification (Version 3.2 (Core Profile) - December 7, 2009),
            M. Segal, K. Akeley, December 2009.
        
[GLES20]

            OpenGL® ES Common Profile Specification Version 2.0.25,
            A. Munshi, J. Leech, November 2010.
        
[GLES20GLSL]

            The OpenGL® ES Shading Language Version 1.00,
            R. Simpson, May 2009.
        
[REGISTRY]

            WebGL Extension Registry

[RFC2119]

            Key words for use in RFCs to Indicate Requirement Levels,
            S. Bradner. IETF, March 1997.
        
[CSS]

            Cascading Style Sheets Level 2 Revision 1 (CSS 2.1) Specification,
            B. Bos, T. Celik, I. Hickson, H. W. Lie, June 2011.
        
[CORS]

            Cross-Origin Resource Sharing,
            A. van Kesteren, July 2010.
        
[DOM4]

            DOM4,
            A. van Kesteren, A. Gregor, Ms2ger.
        
[DOM3EVENTS]

            Document Object Model (DOM) Level 3 Events Specification,
            Doug Schepers and Jacob Rossi. W3C.
        
[HTML]

            HTML,
            I. Hickson, June 2011.
        
[WEBIDL]

            Web IDL - Living Standard,
            E. Chen, T. Gu, B. Zbarsky, C. McCormack, T. Langel.
        
[ASCII]
International Standard ISO/IEC 646:1991. Information technology -
            ISO 7-bit coded character set for information interchange

[DOMSTRING]

            Document Object Model Core: The DOMString type,
            World Wide Web Consortium (W3C).
        
[KHRROBUSTACCESS]

            KHR_robust_buffer_access_behavior OpenGL ES extension,
            Leech, J. and Daniell, P., August, 2014.
        
[MULTIPLEBUFFERING]
(Non-normative) 
            Multiple buffering. Wikipedia.
        
[WEBCODECS]
(Non-normative) WebCodecs API,
            C. Cunningham, P. Adenot, B. Aboba. W3C.
        
[PREDEFINEDCOLORSPACE]

            HTML Living Standard - The PredefinedColorSpace enum,
            WHATWG.
        
[WEBGPU]

            WebGPU Editor's Draft,
            WebGPU Community Group.
        

Acknowledgments
This specification is produced by the Khronos WebGL Working Group.

        Special thanks to: Arun Ranganathan (Mozilla), Chris Marrin (Apple), Jon Leech, Kenneth
        Russell (Google), Kenneth Waters (Google), Mark Callow (HI), Mark Steele (Mozilla), Oliver
        Hunt (Apple), Tim Johansson (Opera), Vangelis Kokkevis (Google), Vladimir Vukicevic
        (Mozilla), Gregg Tavares (Google)
    

        Additional thanks to: Alan Hudson (Yumetech), Benoit Jacob (Mozilla), Bill Licea Kane (AMD),
        Boris Zbarsky (Mozilla), Cameron McCormack (Mozilla), Cedric Vivier (Zegami), Dan Gessel
        (Apple), David Ligon (Qualcomm), David Sheets (Ashima Arts), Glenn Maynard, Greg Roth
        (Nvidia), Jacob Strom  (Ericsson), Jeff Gilbert (Mozilla), Kari Pulli (Nokia), Teddie Stenvi
        (ST-Ericsson), Neil Trevett (Nvidia), Per Wennersten (Ericsson), Per-Erik Brodin (Ericsson),
        Shiki Okasaka (Google), Tom Olson (ARM), Zhengrong Yao (Ericsson), and the members of the
        Khronos WebGL Working Group.

There are no other mechanisms to disable an extension.

Multiple calls to getExtension with the same extension string, taking into account
        case-insensitive comparison, must return the same object as long as the extension is enabled. An
        attempt to use any features of an extension without first calling getExtension to enable it must
        generate an appropriate GL error and must not make use of the feature.

This specification does not define any extensions. A separate WebGL
        extension registry defines extensions that may be supported by a particular WebGL
        implementation.

WebGL generates a WebGLContextEvent event in response to important changes in status of a
        WebGL rendering context. Events are sent using the DOM Event System [DOM3EVENTS],
        and are dispatched to the HTMLCanvasElement or OffscreenCanvas associated with the WebGL rendering context.
        The types of status changes that can trigger a WebGLContextEvent event are 
        the loss of the context, the restoration of the context, and
         the inability to create a context.

To fire a WebGL context event named e means
        that an event using
        the WebGLContextEvent interface, with
        its type
        attribute [DOM4] initialized to e, its
        cancelable attribute initialized to true, and
        its isTrusted
        attribute [DOM4] initialized to true, is to
        be dispatched at the
        given object.

The task
    source for
    all tasks queued [HTML]
    in this section is the WebGL task source.

The following attributes are available:

When the user agent detects that the drawing buffer associated with
        a WebGLRenderingContext context has been lost, it must run the
        following steps:

        
 Let canvas be the context's
canvas. 
 If context's webgl context lost flag
        is set, abort these steps. 
 Set context's webgl context lost
        flag. 
 Set the invalidated flag of
        each WebGLObject instance created by this context. 
 Disable all extensions except "WEBGL_lose_context". 
 Queue a task to
        perform the following steps:

            
 Fire a WebGL context event named
            "webglcontextlost" at canvas, with its statusMessage attribute set
            to "". 
 If the
            event's canceled
            flag is not set, abort these steps. 
 Perform the following steps asynchronously. 
 Await a restorable drawing buffer. 
 Queue a task to restore the drawing
            buffer for context.

- Let canvas be the context's
canvas.
- If context's webgl context lost flag
        is set, abort these steps.
- Set context's webgl context lost
        flag.
- Set the invalidated flag of
        each WebGLObject instance created by this context.
- Disable all extensions except "WEBGL_lose_context".
- Queue a task to
        perform the following steps:

            
 Fire a WebGL context event named
            "webglcontextlost" at canvas, with its statusMessage attribute set
            to "". 
 If the
            event's canceled
            flag is not set, abort these steps. 
 Perform the following steps asynchronously. 
 Await a restorable drawing buffer. 
 Queue a task to restore the drawing
            buffer for context.
- Fire a WebGL context event named
            "webglcontextlost" at canvas, with its statusMessage attribute set
            to "".
- If the
            event's canceled
            flag is not set, abort these steps.
- Perform the following steps asynchronously.
- Await a restorable drawing buffer.
- Queue a task to restore the drawing
            buffer for context.

- Fire a WebGL context event named
            "webglcontextlost" at canvas, with its statusMessage attribute set
            to "".
- If the
            event's canceled
            flag is not set, abort these steps.
- Perform the following steps asynchronously.
- Await a restorable drawing buffer.
- Queue a task to restore the drawing
            buffer for context.

A WebGLObject created while the context is lost
        (e.g. a WebGLBuffer via createBuffer())
        begins life with its invalidated flag set.

When the user agent is to restore the drawing
        buffer for a WebGLRenderingContext context, it must run the
        following steps:

        
 Let canvas be the canvas object associated with context.

         If context's webgl context lost flag is
        not set, abort these steps.

         Create a drawing buffer using the
        settings specified in context's context
        creation parameters, and associate the drawing buffer with context,
        discarding any previous drawing buffer.

         Clear context's webgl context lost
        flag.

         Reset context's OpenGL error state.

         Fire a WebGL context event named
        "webglcontextrestored" at canvas, with its statusMessage attribute set
        to "".

- Let canvas be the canvas object associated with context.

         If context's webgl context lost flag is
        not set, abort these steps.

         Create a drawing buffer using the
        settings specified in context's context
        creation parameters, and associate the drawing buffer with context,
        discarding any previous drawing buffer.

         Clear context's webgl context lost
        flag.

         Reset context's OpenGL error state.

         Fire a WebGL context event named
        "webglcontextrestored" at canvas, with its statusMessage attribute set
        to "".
- If context's webgl context lost flag is
        not set, abort these steps.

         Create a drawing buffer using the
        settings specified in context's context
        creation parameters, and associate the drawing buffer with context,
        discarding any previous drawing buffer.

         Clear context's webgl context lost
        flag.

         Reset context's OpenGL error state.

         Fire a WebGL context event named
        "webglcontextrestored" at canvas, with its statusMessage attribute set
        to "".
- Create a drawing buffer using the
        settings specified in context's context
        creation parameters, and associate the drawing buffer with context,
        discarding any previous drawing buffer.

         Clear context's webgl context lost
        flag.

         Reset context's OpenGL error state.

         Fire a WebGL context event named
        "webglcontextrestored" at canvas, with its statusMessage attribute set
        to "".
- Clear context's webgl context lost
        flag.

         Reset context's OpenGL error state.

         Fire a WebGL context event named
        "webglcontextrestored" at canvas, with its statusMessage attribute set
        to "".
- Reset context's OpenGL error state.

         Fire a WebGL context event named
        "webglcontextrestored" at canvas, with its statusMessage attribute set
        to "".
- Fire a WebGL context event named
        "webglcontextrestored" at canvas, with its statusMessage attribute set
        to "".

> **Note:** Once the context is restored, WebGL resources such as textures and buffers that were created
        before the context was restored are no longer valid.
        Previously enabled extensions are not restored.
        The application will want to restore all modified state and destroyed extensions and resources.

When the user agent is to fire a WebGL
        context creation error at a canvas, it must perform the following steps:

        
 Fire a WebGL context event named
        "webglcontextcreationerror" at canvas, optionally with its statusMessage
        attribute set to a platform dependent string about the nature of the failure.

- Fire a WebGL context event named
        "webglcontextcreationerror" at canvas, optionally with its statusMessage
        attribute set to a platform dependent string about the nature of the failure.


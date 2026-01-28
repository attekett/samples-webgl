#!/usr/bin/env python3
"""
Feature Combination Matrix Analysis Tool

Analyzes feature combination coverage in WebGL corpus to identify
missing combinations and generate actionable recommendations.
"""

import os
import re
import sys
import glob
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple
from itertools import combinations


# Feature detection patterns (reused from detailed_coverage_analysis.py)
FEATURE_PATTERNS = {
    '3D Textures': [
        r'TEXTURE_3D', r'texImage3D', r'texStorage3D',
        r'texSubImage3D', r'copyTexSubImage3D', r'compressedTexImage3D'
    ],
    'Blending': [
        r'BLEND\b', r'blendFunc', r'blendEquation',
        r'blendFuncSeparate', r'blendEquationSeparate', r'blendColor'
    ],
    'Buffer Operations': [
        r'createBuffer', r'deleteBuffer', r'bindBuffer',
        r'bufferData', r'bufferSubData', r'copyBufferSubData',
        r'getBufferParameter', r'getBufferSubData'
    ],
    'Depth/Stencil Ops': [
        r'DEPTH_TEST', r'STENCIL_TEST', r'depthFunc', r'depthMask',
        r'stencilFunc', r'stencilOp', r'stencilMask', r'stencilFuncSeparate'
    ],
    'Framebuffer Objects': [
        r'createFramebuffer', r'deleteFramebuffer', r'bindFramebuffer',
        r'framebufferTexture2D', r'framebufferTextureLayer',
        r'framebufferRenderbuffer', r'checkFramebufferStatus',
        r'blitFramebuffer', r'invalidateFramebuffer', r'invalidateSubFramebuffer'
    ],
    'Instanced Rendering': [
        r'drawArraysInstanced', r'drawElementsInstanced', r'vertexAttribDivisor'
    ],
    'Integer Textures': [
        r'R32I', r'RGBA32I', r'R32UI', r'RGBA32UI',
        r'R16I', r'RGBA16I', r'R16UI', r'RGBA16UI',
        r'R8I', r'RGBA8I', r'R8UI', r'RGBA8UI'
    ],
    'Multiple Render Targets': [
        r'drawBuffers', r'COLOR_ATTACHMENT[1-9]',
        r'readBuffer', r'clearBufferfv', r'clearBufferiv', r'clearBufferuiv'
    ],
    'Pixel Operations': [
        r'readPixels', r'copyTexImage2D', r'copyTexSubImage2D',
        r'copyTexSubImage3D', r'PACK_', r'UNPACK_'
    ],
    'Query Objects': [
        r'createQuery', r'deleteQuery', r'beginQuery', r'endQuery',
        r'getQueryParameter', r'getQuery', r'ANY_SAMPLES_PASSED',
        r'TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN'
    ],
    'Renderbuffers': [
        r'createRenderbuffer', r'deleteRenderbuffer', r'bindRenderbuffer',
        r'renderbufferStorage', r'renderbufferStorageMultisample',
        r'getRenderbufferParameter'
    ],
    'Sampler Objects': [
        r'createSampler', r'deleteSampler', r'bindSampler',
        r'samplerParameteri', r'samplerParameterf', r'getSamplerParameter'
    ],
    'Sync Objects': [
        r'fenceSync', r'clientWaitSync', r'waitSync',
        r'deleteSync', r'getSyncParameter', r'SYNC_'
    ],
    'Texture Arrays': [
        r'TEXTURE_2D_ARRAY', r'texStorage3D.*TEXTURE_2D_ARRAY',
        r'framebufferTextureLayer', r'TEXTURE_CUBE_MAP_ARRAY'
    ],
    'Texture Operations': [
        r'createTexture', r'deleteTexture', r'bindTexture',
        r'texImage2D', r'texImage3D', r'texSubImage2D', r'texSubImage3D',
        r'texStorage2D', r'texStorage3D', r'texParameteri',
        r'texParameterf', r'generateMipmap'
    ],
    'Transform Feedback': [
        r'TRANSFORM_FEEDBACK\b', r'transformFeedbackVaryings',
        r'beginTransformFeedback', r'endTransformFeedback',
        r'pauseTransformFeedback', r'resumeTransformFeedback',
        r'bindTransformFeedback', r'createTransformFeedback'
    ],
    'Uniform Buffer Objects': [
        r'UNIFORM_BUFFER', r'uniformBlockBinding', r'bindBufferBase',
        r'bindBufferRange', r'getUniformBlockIndex',
        r'getActiveUniformBlockParameter'
    ],
    'Vertex Array Objects': [
        r'createVertexArray', r'deleteVertexArray', r'bindVertexArray'
    ]
}


def extract_features(html_content: str) -> Set[str]:
    """
    Extract feature presence from HTML seed file.

    Args:
        html_content: Full HTML file content

    Returns:
        Set of feature names detected in the seed
    """
    features = set()

    for feature_name, patterns in FEATURE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, html_content):
                features.add(feature_name)
                break  # Found this feature, move to next

    return features


def main():
    parser = argparse.ArgumentParser(
        description='Analyze feature combination coverage in WebGL corpus'
    )
    parser.add_argument('--corpus-dir', default='agent_outputs',
                       help='Corpus directory (default: agent_outputs)')
    parser.add_argument('--depth', type=int, default=2, choices=[2, 3, 4],
                       help='Combination depth (default: 2)')
    parser.add_argument('--min-threshold', type=int, default=5,
                       help='Minimum seeds for covered status (default: 5)')
    parser.add_argument('--output-matrix', required=True,
                       help='CSV matrix output path')
    parser.add_argument('--output-gaps', required=True,
                       help='Markdown gap report output path')
    parser.add_argument('--output-plan',
                       help='Auto-generated enhancement plan path (optional)')
    parser.add_argument('--heatmap',
                       help='PNG heatmap output path (optional)')

    args = parser.parse_args()

    print(f"Analyzing corpus: {args.corpus_dir}")

    # Test on one seed file
    test_files = list(Path(args.corpus_dir).glob("mutation_b*.html"))
    if test_files:
        with open(test_files[0], 'r') as f:
            content = f.read()
            features = extract_features(content)
            print(f"Test file: {test_files[0].name}")
            print(f"Features found: {features}")

    print(f"This is a placeholder - full implementation coming")


if __name__ == '__main__':
    main()

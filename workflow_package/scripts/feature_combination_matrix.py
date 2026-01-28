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
        r'\bTEXTURE_3D\b', r'\btexImage3D\b', r'\btexStorage3D\b',
        r'\btexSubImage3D\b', r'\bcopyTexSubImage3D\b', r'\bcompressedTexImage3D\b'
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
        r'\bR32I\b', r'\bRGBA32I\b', r'\bR32UI\b', r'\bRGBA32UI\b',
        r'\bR16I\b', r'\bRGBA16I\b', r'\bR16UI\b', r'\bRGBA16UI\b',
        r'\bR8I\b', r'\bRGBA8I\b', r'\bR8UI\b', r'\bRGBA8UI\b'
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


def parse_corpus(corpus_dir: str) -> Tuple[Dict[str, Set[str]], Dict[str, float]]:
    """
    Parse entire corpus and extract feature vectors.

    Args:
        corpus_dir: Path to corpus directory

    Returns:
        Tuple of (seed_features, feature_coverage)
        - seed_features: Dict mapping filename to set of features
        - feature_coverage: Dict mapping feature to coverage percentage
    """
    corpus_path = Path(corpus_dir)
    seed_files = list(corpus_path.glob("mutation_b*.html"))

    if not seed_files:
        print(f"ERROR: No mutation_b*.html files found in {corpus_dir}")
        sys.exit(1)

    print(f"Found {len(seed_files)} seed files")

    seed_features = {}
    all_features = set()

    for seed_file in seed_files:
        with open(seed_file, 'r') as f:
            content = f.read()
            features = extract_features(content)
            seed_features[seed_file.name] = features
            all_features.update(features)

    # Calculate single-feature coverage percentages
    total_seeds = len(seed_files)
    feature_coverage = {}

    for feature in sorted(all_features):
        count = sum(1 for features in seed_features.values() if feature in features)
        coverage_pct = (count / total_seeds) * 100
        feature_coverage[feature] = coverage_pct

    print(f"Detected {len(all_features)} feature categories")

    return seed_features, feature_coverage


def build_combination_matrix(
    seed_features: Dict[str, Set[str]],
    depth: int = 2
) -> Dict[Tuple[str, ...], int]:
    """
    Build N-way combination matrix from seed feature vectors.

    Args:
        seed_features: Dict mapping seed name to set of features
        depth: Combination depth (2, 3, or 4)

    Returns:
        Dict mapping feature tuple to seed count
    """
    combo_matrix = {}

    for seed_name, features in seed_features.items():
        # Generate all N-way combinations from this seed's features
        for combo in combinations(sorted(features), depth):
            combo_matrix[combo] = combo_matrix.get(combo, 0) + 1

    return combo_matrix


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

    seed_features, feature_coverage = parse_corpus(args.corpus_dir)

    print("\nFeature Coverage Summary:")
    for feature in sorted(feature_coverage.keys()):
        count = sum(1 for f in seed_features.values() if feature in f)
        print(f"  {feature}: {feature_coverage[feature]:.1f}% ({count} seeds)")

    print(f"\nBuilding {args.depth}-way combination matrix...")
    combination_matrix = build_combination_matrix(seed_features, args.depth)

    print(f"Total combinations found: {len(combination_matrix)}")
    print(f"Combinations with 0 seeds: {sum(1 for c in combination_matrix.values() if c == 0)}")
    print(f"Combinations with <{args.min_threshold} seeds: {sum(1 for c in combination_matrix.values() if c < args.min_threshold)}")


if __name__ == '__main__':
    main()

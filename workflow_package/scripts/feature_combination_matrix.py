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


def calculate_priority(
    combo: Tuple[str, ...],
    feature_coverage: Dict[str, float],
    seed_count: int,
    threshold: float = 20.0
) -> float:
    """
    Calculate priority score for a combination gap.

    Formula: priority = sum(feature_gaps) * rarity_multiplier

    Args:
        combo: Tuple of feature names
        feature_coverage: Dict mapping feature to coverage percentage
        seed_count: Number of seeds with this combination
        threshold: Coverage threshold percentage (default 20%)

    Returns:
        Priority score (0-200+)
    """
    # Calculate total gap across all features in combination
    total_gap = 0.0
    for feature in combo:
        coverage = feature_coverage.get(feature, 0.0)
        if coverage < threshold:
            total_gap += (threshold - coverage)

    # Rarity multiplier based on seed count
    if seed_count == 0:
        rarity = 100
    elif seed_count == 1:
        rarity = 50
    elif seed_count == 2:
        rarity = 25
    elif seed_count <= 4:
        rarity = 15
    else:
        rarity = 10

    return total_gap * rarity


def identify_gaps(
    combination_matrix: Dict[Tuple[str, ...], int],
    feature_coverage: Dict[str, float],
    min_threshold: int
) -> List[Dict]:
    """
    Identify and prioritize combination gaps.

    Args:
        combination_matrix: Dict mapping combo to seed count
        feature_coverage: Dict mapping feature to coverage %
        min_threshold: Minimum seeds for "covered" status

    Returns:
        List of gap dicts sorted by priority (descending)
    """
    gaps = []

    for combo, count in combination_matrix.items():
        if count < min_threshold:
            priority = calculate_priority(combo, feature_coverage, count)

            gaps.append({
                'combo': combo,
                'count': count,
                'priority': priority,
                'features': [
                    {
                        'name': f,
                        'coverage': feature_coverage.get(f, 0.0),
                        'gap': max(0, 20.0 - feature_coverage.get(f, 0.0))
                    }
                    for f in combo
                ]
            })

    # Sort by priority descending
    gaps.sort(key=lambda x: x['priority'], reverse=True)

    return gaps


def write_matrix_csv(
    combination_matrix: Dict[Tuple[str, ...], int],
    features: List[str],
    output_path: str
):
    """
    Write combination matrix to CSV file.

    Args:
        combination_matrix: Dict mapping combo to seed count
        features: List of all features (sorted)
        output_path: CSV file path
    """
    import csv

    # For 2-way only (higher dimensions not suitable for matrix format)
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header row
        writer.writerow(['Feature'] + features)

        # Data rows
        for f1 in features:
            row = [f1]
            for f2 in features:
                if f1 == f2:
                    # Diagonal: single feature coverage (not a combination)
                    row.append('-')
                else:
                    # Look up combination count (order-independent)
                    combo = tuple(sorted([f1, f2]))
                    count = combination_matrix.get(combo, 0)
                    row.append(str(count))
            writer.writerow(row)

    print(f"Matrix written to: {output_path}")


def find_reference_seeds(
    combo: Tuple[str, ...],
    seed_features: Dict[str, Set[str]]
) -> List[Tuple[str, int, Set[str]]]:
    """
    Find seeds containing any feature in the combo (potential templates).

    Args:
        combo: Tuple of feature names to search for
        seed_features: Dict mapping seed name to set of features

    Returns:
        List of (seed_name, match_count, features) tuples, sorted by match_count
    """
    reference_seeds = []

    for seed_name, features in seed_features.items():
        # Check if seed has any feature from the combo
        match_count = sum(1 for f in combo if f in features)

        if match_count > 0:
            reference_seeds.append((seed_name, match_count, features))

    # Sort by match count (seeds with more matching features first)
    reference_seeds.sort(key=lambda x: x[1], reverse=True)

    return reference_seeds


def write_gaps_markdown(
    gaps: List[Dict],
    feature_coverage: Dict[str, float],
    seed_features: Dict[str, Set[str]],
    total_seeds: int,
    output_path: str
):
    """
    Write detailed gap report to Markdown file.

    Args:
        gaps: List of gap dicts (priority sorted)
        feature_coverage: Dict mapping feature to coverage %
        seed_features: Dict mapping seed to features
        total_seeds: Total number of seeds in corpus
        output_path: Markdown file path
    """
    from datetime import datetime

    with open(output_path, 'w') as f:
        # Header
        f.write("# Feature Combination Gap Analysis\n\n")
        f.write(f"**Corpus**: {total_seeds} seeds\n")
        f.write(f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("---\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")

        critical_gaps = [g for g in gaps if g['priority'] > 80]
        high_gaps = [g for g in gaps if 40 < g['priority'] <= 80]
        medium_gaps = [g for g in gaps if 20 < g['priority'] <= 40]

        f.write(f"- **Critical gaps (priority >80)**: {len(critical_gaps)} combinations\n")
        f.write(f"- **High gaps (priority 40-80)**: {len(high_gaps)} combinations\n")
        f.write(f"- **Medium gaps (priority 20-40)**: {len(medium_gaps)} combinations\n")
        f.write(f"- **Total gaps analyzed**: {len(gaps)} combinations\n\n")

        f.write("---\n\n")

        # Critical Gaps section
        f.write("## Critical Gaps (Priority Score >80)\n\n")

        if not critical_gaps:
            f.write("✅ No critical gaps found! All important combinations are covered.\n\n")
        else:
            for i, gap in enumerate(critical_gaps, 1):
                f.write(f"### {i}. {' + '.join(gap['combo'])} (Priority: {gap['priority']:.1f}) ⚠️\n\n")
                f.write(f"**Current Status:**\n")
                f.write(f"- Seeds with combination: {gap['count']}\n")

                for feat_info in gap['features']:
                    f.write(f"- {feat_info['name']} coverage: {feat_info['coverage']:.1f}%")
                    if feat_info['gap'] > 0:
                        f.write(f" (gap: {feat_info['gap']:.1f}%)")
                    f.write("\n")

                f.write("\n")

                # Find reference seeds
                references = find_reference_seeds(gap['combo'], seed_features)

                f.write("**Seed Specification:**\n")
                f.write(f"- **Target**: Create 3-5 seeds\n")
                f.write(f"- **Core pattern**: Combine {' + '.join(gap['combo'])}\n")
                f.write(f"- **Complexity targets**: 12-17 try-catch blocks per seed\n")
                f.write(f"- **Estimated lines**: 180-250 per seed\n\n")

                f.write("**Reference Seeds (Templates):**\n")
                for seed_name, match_count, _ in references[:3]:
                    f.write(f"- `{seed_name}` - Has {match_count}/{len(gap['combo'])} features\n")
                f.write("\n")

                f.write("---\n\n")

    print(f"Gap report written to: {output_path}")


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

    print("\nIdentifying gaps...")
    gaps = identify_gaps(combination_matrix, feature_coverage, args.min_threshold)

    print(f"\nTop 5 Priority Gaps:")
    for i, gap in enumerate(gaps[:5], 1):
        print(f"{i}. {' + '.join(gap['combo'])} (Priority: {gap['priority']:.1f}, Seeds: {gap['count']})")

    if args.depth == 2:
        all_features = sorted(feature_coverage.keys())
        write_matrix_csv(combination_matrix, all_features, args.output_matrix)
    else:
        print(f"Skipping matrix CSV (only supported for depth=2)")

    write_gaps_markdown(gaps, feature_coverage, seed_features,
                       len(seed_features), args.output_gaps)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Detailed WebGL Feature Coverage Analysis Tool

Provides comprehensive analysis of WebGL2 fuzzing corpus including:
- Granular API call frequency analysis
- Feature co-occurrence matrix
- Per-seed complexity scoring
- API parameter diversity metrics
- Coverage heatmaps
- Edge case detection
- Extension usage tracking
"""

import os
import re
import sys
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
import argparse


class WebGLFeatureAnalyzer:
    """Comprehensive WebGL feature coverage analyzer"""

    def __init__(self, corpus_dir: str):
        self.corpus_dir = Path(corpus_dir)
        self.seeds = list(self.corpus_dir.glob("mutation_b*.html"))

        # Feature detection patterns
        self.features = {
            'Buffer Operations': [
                'createBuffer', 'deleteBuffer', 'bindBuffer',
                'bufferData', 'bufferSubData', 'copyBufferSubData',
                'getBufferParameter', 'getBufferSubData'
            ],
            'Uniform Buffer Objects': [
                'UNIFORM_BUFFER', 'uniformBlockBinding', 'bindBufferBase',
                'bindBufferRange', 'getUniformBlockIndex', 'getActiveUniformBlockParameter',
                'uniformBlockBinding'
            ],
            'Transform Feedback': [
                'TRANSFORM_FEEDBACK', 'transformFeedbackVaryings', 'beginTransformFeedback',
                'endTransformFeedback', 'pauseTransformFeedback', 'resumeTransformFeedback',
                'bindTransformFeedback', 'createTransformFeedback'
            ],
            'Texture Operations': [
                'createTexture', 'deleteTexture', 'bindTexture',
                'texImage2D', 'texImage3D', 'texSubImage2D', 'texSubImage3D',
                'texStorage2D', 'texStorage3D', 'copyTexImage2D', 'copyTexSubImage2D',
                'texParameteri', 'texParameterf', 'generateMipmap'
            ],
            '3D Textures': [
                'TEXTURE_3D', 'texImage3D', 'texStorage3D',
                'texSubImage3D', 'copyTexSubImage3D', 'compressedTexImage3D'
            ],
            'Texture Arrays': [
                'TEXTURE_2D_ARRAY', 'texStorage3D', 'texSubImage3D',
                'framebufferTextureLayer', 'TEXTURE_CUBE_MAP_ARRAY'
            ],
            'Framebuffer Objects': [
                'createFramebuffer', 'deleteFramebuffer', 'bindFramebuffer',
                'framebufferTexture2D', 'framebufferTextureLayer', 'framebufferRenderbuffer',
                'checkFramebufferStatus', 'readPixels', 'blitFramebuffer',
                'invalidateFramebuffer', 'invalidateSubFramebuffer'
            ],
            'Multiple Render Targets': [
                'drawBuffers', 'COLOR_ATTACHMENT1', 'COLOR_ATTACHMENT2',
                'COLOR_ATTACHMENT3', 'COLOR_ATTACHMENT4', 'readBuffer',
                'clearBufferfv', 'clearBufferiv', 'clearBufferuiv'
            ],
            'Instanced Rendering': [
                'drawArraysInstanced', 'drawElementsInstanced', 'vertexAttribDivisor'
            ],
            'Vertex Array Objects': [
                'createVertexArray', 'deleteVertexArray', 'bindVertexArray'
            ],
            'Sync Objects': [
                'fenceSync', 'clientWaitSync', 'waitSync',
                'deleteSync', 'getSyncParameter', 'SYNC_'
            ],
            'Query Objects': [
                'createQuery', 'deleteQuery', 'beginQuery', 'endQuery',
                'getQueryParameter', 'getQuery', 'ANY_SAMPLES_PASSED',
                'TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN'
            ],
            'Sampler Objects': [
                'createSampler', 'deleteSampler', 'bindSampler',
                'samplerParameteri', 'samplerParameterf', 'getSamplerParameter'
            ],
            'Integer Textures': [
                'R32I', 'RGBA32I', 'R32UI', 'RGBA32UI',
                'R16I', 'RGBA16I', 'R16UI', 'RGBA16UI',
                'R8I', 'RGBA8I', 'R8UI', 'RGBA8UI'
            ],
            'Depth/Stencil Ops': [
                'DEPTH_TEST', 'STENCIL_TEST', 'depthFunc', 'depthMask',
                'stencilFunc', 'stencilOp', 'stencilMask', 'stencilFuncSeparate',
                'stencilOpSeparate', 'clearDepth', 'clearStencil'
            ],
            'Blending': [
                'BLEND', 'blendFunc', 'blendFuncSeparate',
                'blendEquation', 'blendEquationSeparate', 'blendColor'
            ],
            'Renderbuffers': [
                'createRenderbuffer', 'deleteRenderbuffer', 'bindRenderbuffer',
                'renderbufferStorage', 'renderbufferStorageMultisample', 'getRenderbufferParameter'
            ],
            'Pixel Operations': [
                'readPixels', 'copyTexImage2D', 'copyTexSubImage2D',
                'copyTexSubImage3D', 'pixelStorei'
            ]
        }

        # WebGL2 extensions
        self.extensions = [
            'EXT_color_buffer_float', 'EXT_texture_filter_anisotropic',
            'WEBGL_compressed_texture_s3tc', 'WEBGL_compressed_texture_etc',
            'WEBGL_compressed_texture_astc', 'WEBGL_depth_texture',
            'OES_texture_float', 'OES_texture_half_float',
            'WEBGL_draw_buffers', 'EXT_blend_minmax',
            'EXT_sRGB', 'OES_standard_derivatives'
        ]

    def read_seed(self, seed_path: Path) -> str:
        """Read seed file content"""
        try:
            with open(seed_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {seed_path}: {e}", file=sys.stderr)
            return ""

    def count_api_calls(self, content: str, api_pattern: str) -> int:
        """Count occurrences of an API call pattern"""
        return len(re.findall(api_pattern, content))

    def analyze_seed_features(self, seed_path: Path) -> Dict:
        """Analyze all features in a single seed"""
        content = self.read_seed(seed_path)

        analysis = {
            'filename': seed_path.name,
            'lines': len(content.split('\n')),
            'features': {},
            'api_calls': {},
            'extensions': [],
            'metrics': {}
        }

        # Feature detection with counts
        for feature_name, api_list in self.features.items():
            feature_count = 0
            api_details = {}

            for api in api_list:
                count = self.count_api_calls(content, api)
                if count > 0:
                    feature_count += count
                    api_details[api] = count

            analysis['features'][feature_name] = {
                'present': feature_count > 0,
                'total_calls': feature_count,
                'apis_used': api_details
            }

        # Extension detection
        for ext in self.extensions:
            if ext in content:
                analysis['extensions'].append(ext)

        # Complexity metrics
        analysis['metrics'] = {
            'try_catch_blocks': self.count_api_calls(content, r'try\s*{'),
            'gl_calls': self.count_api_calls(content, r'gl\.'),
            'const_declarations': self.count_api_calls(content, r'^\s*const\s+[a-zA-Z]'),
            'numeric_literals': self.count_api_calls(content, r'gl\.[a-zA-Z]+\([^)]*\d+'),
            'bind_calls': self.count_api_calls(content, r'gl\.bind'),
            'create_calls': self.count_api_calls(content, r'gl\.create'),
            'delete_calls': self.count_api_calls(content, r'gl\.delete'),
            'enable_disable': self.count_api_calls(content, r'gl\.(enable|disable)'),
            'draw_calls': self.count_api_calls(content, r'gl\.(drawArrays|drawElements)'),
            'shader_lines': self.count_shader_complexity(content)
        }

        # Calculate complexity score
        m = analysis['metrics']
        analysis['metrics']['complexity_score'] = (
            m['try_catch_blocks'] * 2 +
            m['gl_calls'] +
            m['bind_calls'] * 1.5 +
            m['create_calls'] * 2 +
            m['delete_calls'] * 3 +
            len(analysis['extensions']) * 5 +
            m['shader_lines'] * 0.5
        )

        return analysis

    def count_shader_complexity(self, content: str) -> int:
        """Count shader code complexity"""
        shader_match = re.findall(r'shaderSource\([^,]+,\s*`([^`]*)`', content)
        total_lines = 0
        for shader in shader_match:
            total_lines += len(shader.split('\n'))
        return total_lines

    def analyze_corpus(self) -> Dict:
        """Analyze entire corpus"""
        print(f"Analyzing {len(self.seeds)} seeds...", file=sys.stderr)

        corpus_analysis = {
            'total_seeds': len(self.seeds),
            'seeds': [],
            'feature_matrix': defaultdict(list),
            'api_frequency': Counter(),
            'extension_usage': Counter(),
            'feature_cooccurrence': defaultdict(lambda: defaultdict(int)),
            'complexity_distribution': []
        }

        for seed_path in sorted(self.seeds):
            analysis = self.analyze_seed_features(seed_path)
            corpus_analysis['seeds'].append(analysis)

            # Build feature matrix
            present_features = [f for f, data in analysis['features'].items() if data['present']]
            for feature in present_features:
                corpus_analysis['feature_matrix'][feature].append(analysis['filename'])

            # API frequency
            for feature_data in analysis['features'].values():
                for api, count in feature_data['apis_used'].items():
                    corpus_analysis['api_frequency'][api] += count

            # Extension usage
            for ext in analysis['extensions']:
                corpus_analysis['extension_usage'][ext] += 1

            # Feature co-occurrence
            for i, f1 in enumerate(present_features):
                for f2 in present_features[i+1:]:
                    corpus_analysis['feature_cooccurrence'][f1][f2] += 1
                    corpus_analysis['feature_cooccurrence'][f2][f1] += 1

            # Complexity distribution
            corpus_analysis['complexity_distribution'].append({
                'filename': analysis['filename'],
                'score': analysis['metrics']['complexity_score']
            })

        return corpus_analysis

    def generate_report(self, analysis: Dict, format: str = 'markdown') -> str:
        """Generate comprehensive analysis report"""
        if format == 'json':
            return json.dumps(analysis, indent=2)

        # Markdown report
        report = []
        report.append("# Comprehensive WebGL Coverage Analysis\n")
        report.append(f"**Total Seeds**: {analysis['total_seeds']}\n")
        report.append(f"**Generated**: {Path.cwd()}\n\n")

        # Feature Coverage Summary
        report.append("## 1. Feature Coverage Summary\n")
        report.append("| Feature Category | Seeds | Coverage | Total API Calls | Avg Calls/Seed |")
        report.append("|------------------|-------|----------|-----------------|----------------|")

        for feature_name in sorted(self.features.keys()):
            seeds_with_feature = len(analysis['feature_matrix'][feature_name])
            coverage_pct = (seeds_with_feature * 100) // analysis['total_seeds']

            total_calls = sum(
                seed['features'][feature_name]['total_calls']
                for seed in analysis['seeds']
            )
            avg_calls = total_calls / seeds_with_feature if seeds_with_feature > 0 else 0

            report.append(f"| {feature_name} | {seeds_with_feature}/{analysis['total_seeds']} | "
                         f"{coverage_pct}% | {total_calls} | {avg_calls:.1f} |")

        report.append("\n")

        # Top 20 Most Used APIs
        report.append("## 2. Most Used WebGL APIs (Top 20)\n")
        report.append("| Rank | API Call | Total Uses | Avg per Seed |")
        report.append("|------|----------|------------|--------------|")

        for rank, (api, count) in enumerate(analysis['api_frequency'].most_common(20), 1):
            avg = count / analysis['total_seeds']
            report.append(f"| {rank} | `{api}` | {count} | {avg:.1f} |")

        report.append("\n")

        # Extension Usage
        report.append("## 3. WebGL Extension Usage\n")
        if analysis['extension_usage']:
            report.append("| Extension | Seeds Using | Coverage |")
            report.append("|-----------|-------------|----------|")
            for ext, count in sorted(analysis['extension_usage'].items(), key=lambda x: -x[1]):
                pct = (count * 100) // analysis['total_seeds']
                report.append(f"| `{ext}` | {count} | {pct}% |")
        else:
            report.append("No extensions detected in corpus.\n")

        report.append("\n")

        # Feature Co-occurrence
        report.append("## 4. Feature Co-occurrence (Top 15 Pairs)\n")
        report.append("| Feature 1 | Feature 2 | Seeds with Both |")
        report.append("|-----------|-----------|-----------------|")

        cooccurrence_pairs = []
        seen = set()
        for f1, partners in analysis['feature_cooccurrence'].items():
            for f2, count in partners.items():
                pair = tuple(sorted([f1, f2]))
                if pair not in seen:
                    seen.add(pair)
                    cooccurrence_pairs.append((f1, f2, count))

        for f1, f2, count in sorted(cooccurrence_pairs, key=lambda x: -x[2])[:15]:
            report.append(f"| {f1} | {f2} | {count} |")

        report.append("\n")

        # Complexity Analysis
        report.append("## 5. Seed Complexity Analysis\n")

        complexity_scores = [s['score'] for s in analysis['complexity_distribution']]
        avg_complexity = sum(complexity_scores) / len(complexity_scores)
        min_complexity = min(complexity_scores)
        max_complexity = max(complexity_scores)

        report.append(f"**Average Complexity Score**: {avg_complexity:.1f}\n")
        report.append(f"**Range**: {min_complexity:.1f} - {max_complexity:.1f}\n\n")

        # Top 10 most complex seeds
        report.append("### Most Complex Seeds (Top 10)\n")
        report.append("| Rank | Filename | Complexity Score |")
        report.append("|------|----------|------------------|")

        top_complex = sorted(analysis['complexity_distribution'],
                            key=lambda x: -x['score'])[:10]
        for rank, item in enumerate(top_complex, 1):
            report.append(f"| {rank} | {item['filename']} | {item['score']:.1f} |")

        report.append("\n")

        # Aggregate Metrics
        report.append("## 6. Aggregate Corpus Metrics\n")

        total_lines = sum(s['lines'] for s in analysis['seeds'])
        total_try_catch = sum(s['metrics']['try_catch_blocks'] for s in analysis['seeds'])
        total_gl_calls = sum(s['metrics']['gl_calls'] for s in analysis['seeds'])
        total_binds = sum(s['metrics']['bind_calls'] for s in analysis['seeds'])
        total_creates = sum(s['metrics']['create_calls'] for s in analysis['seeds'])
        total_deletes = sum(s['metrics']['delete_calls'] for s in analysis['seeds'])

        report.append(f"- **Total Lines**: {total_lines:,}")
        report.append(f"- **Total Try-Catch Blocks**: {total_try_catch}")
        report.append(f"- **Total GL API Calls**: {total_gl_calls:,}")
        report.append(f"- **Total Bind Operations**: {total_binds}")
        report.append(f"- **Total Create Operations**: {total_creates}")
        report.append(f"- **Total Delete Operations**: {total_deletes}")
        report.append(f"- **Avg Lines/Seed**: {total_lines // analysis['total_seeds']}")
        report.append(f"- **Avg Try-Catch/Seed**: {total_try_catch / analysis['total_seeds']:.1f}")
        report.append(f"- **Avg GL Calls/Seed**: {total_gl_calls // analysis['total_seeds']}")
        report.append(f"- **Mutation Target Density**: 1 target per {total_lines / (total_binds + total_creates + total_deletes):.1f} lines\n")

        # Coverage Gaps
        report.append("## 7. Coverage Gaps & Recommendations\n")

        gaps = []
        for feature_name in sorted(self.features.keys()):
            seeds_with_feature = len(analysis['feature_matrix'][feature_name])
            coverage_pct = (seeds_with_feature * 100) // analysis['total_seeds']

            if coverage_pct < 20:
                needed = (analysis['total_seeds'] * 20 // 100) - seeds_with_feature
                gaps.append((feature_name, coverage_pct, seeds_with_feature, needed))

        if gaps:
            report.append("**Features below 20% coverage threshold:**\n")
            report.append("| Feature | Current Coverage | Seeds Needed |")
            report.append("|---------|------------------|--------------|")
            for feature, pct, current, needed in sorted(gaps, key=lambda x: x[1]):
                report.append(f"| {feature} | {pct}% ({current} seeds) | +{needed} |")
        else:
            report.append("✅ All features meet 20% coverage threshold!\n")

        report.append("\n")

        # API Diversity Analysis
        report.append("## 8. API Diversity Analysis\n")

        for feature_name in sorted(self.features.keys()):
            apis_available = len(self.features[feature_name])
            apis_used = set()

            for seed in analysis['seeds']:
                apis_used.update(seed['features'][feature_name]['apis_used'].keys())

            apis_used_count = len(apis_used)
            diversity_pct = (apis_used_count * 100) // apis_available if apis_available > 0 else 0

            if diversity_pct < 100:
                unused = set(self.features[feature_name]) - apis_used
                report.append(f"\n**{feature_name}**: {diversity_pct}% diversity ({apis_used_count}/{apis_available} APIs used)")
                if len(unused) <= 5:
                    report.append(f"\n- Unused APIs: `{', '.join(sorted(unused))}`")

        report.append("\n")

        return '\n'.join(report)

    def generate_heatmap_data(self, analysis: Dict) -> str:
        """Generate CSV data for coverage heatmap visualization"""
        lines = []
        lines.append("Seed," + ",".join(sorted(self.features.keys())))

        for seed_data in sorted(analysis['seeds'], key=lambda x: x['filename']):
            row = [seed_data['filename']]
            for feature in sorted(self.features.keys()):
                present = '1' if seed_data['features'][feature]['present'] else '0'
                row.append(present)
            lines.append(",".join(row))

        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Detailed WebGL feature coverage analysis tool'
    )
    parser.add_argument(
        '--corpus-dir',
        default='agent_outputs',
        help='Directory containing mutation_b*.html seeds (default: agent_outputs)'
    )
    parser.add_argument(
        '--format',
        choices=['markdown', 'json'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--output',
        help='Output file (default: stdout)'
    )
    parser.add_argument(
        '--heatmap',
        help='Generate CSV heatmap data to specified file'
    )

    args = parser.parse_args()

    # Run analysis
    analyzer = WebGLFeatureAnalyzer(args.corpus_dir)

    if not analyzer.seeds:
        print(f"Error: No mutation_b*.html files found in {args.corpus_dir}",
              file=sys.stderr)
        sys.exit(1)

    analysis = analyzer.analyze_corpus()

    # Generate report
    report = analyzer.generate_report(analysis, format=args.format)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    # Generate heatmap if requested
    if args.heatmap:
        heatmap_data = analyzer.generate_heatmap_data(analysis)
        with open(args.heatmap, 'w') as f:
            f.write(heatmap_data)
        print(f"Heatmap data written to {args.heatmap}", file=sys.stderr)


if __name__ == '__main__':
    main()

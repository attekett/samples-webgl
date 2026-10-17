"""Screenshot analysis pipeline for corpus visual validation.

Checks every screenshot in screenshots/ for:
  1. Blank/near-blank renders (uniform color frames)
  2. Visual duplicates via perceptual hashing (visual monoculture)
  3. Non-determinism by diffing against a baseline snapshot directory

Usage:
    ./venv/bin/python scripts/analyze_screenshots.py [--dir screenshots] \
        [--json OUT.json] [--threshold-blank 2.0] [--threshold-dup 6]

Determinism workflow:
    cp -r screenshots /tmp/shots_run1
    # ... re-run tests ...
    ./venv/bin/python scripts/analyze_screenshots.py --baseline-dir /tmp/shots_run1
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image


def load_gray(path, size):
    img = Image.open(path).convert("L").resize((size, size))
    return list(img.tobytes())


def stats(path):
    pixels = load_gray(path, 64)
    n = len(pixels)
    mean = sum(pixels) / n
    var = sum((p - mean) ** 2 for p in pixels) / n
    return {"mean": mean, "stddev": var ** 0.5}


def ahash(path, size=16):
    pixels = load_gray(path, size)
    mean = sum(pixels) / len(pixels)
    bits = 0
    for i, p in enumerate(pixels):
        if p > mean:
            bits |= (1 << i)
    return bits


def hamming(a, b):
    return bin(a ^ b).count("1")


def find_blank(screenshots, blank_stddev):
    blanks = []
    for path in sorted(screenshots):
        s = stats(path)
        if s["stddev"] < blank_stddev:
            blanks.append({"file": str(path), **s})
    return blanks


def find_duplicates(screenshots, dup_distance):
    hashes = {path: ahash(path) for path in screenshots}
    remaining = sorted(hashes.keys())
    groups = []
    while remaining:
        head = remaining[0]
        group = [head]
        rest = []
        for other in remaining[1:]:
            if hamming(hashes[head], hashes[other]) <= dup_distance:
                group.append(other)
            else:
                rest.append(other)
        if len(group) > 1:
            groups.append(group)
        remaining = rest
    return groups


def check_determinism(screenshots, baseline_dir, dup_distance):
    baseline = Path(baseline_dir)
    diffs = []
    missing_baseline = []
    for path in sorted(screenshots):
        ref = baseline / path.name
        if not ref.exists():
            missing_baseline.append(str(path))
            continue
        dist = hamming(ahash(path), ahash(ref))
        if dist > dup_distance:
            diffs.append({"file": str(path), "hamming_vs_baseline": dist})
    return diffs, missing_baseline


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dir', type=Path, default=Path('screenshots'))
    parser.add_argument('--json', type=Path, default=None,
                        help='Write full results JSON here')
    parser.add_argument('--threshold-blank', type=float, default=2.0,
                        help='Stddev below this = blank frame')
    parser.add_argument('--threshold-dup', type=int, default=6,
                        help='Hamming distance at/below this = visual duplicate')
    parser.add_argument('--baseline-dir', type=Path, default=None,
                        help='Previous run screenshot dir for determinism diff')
    args = parser.parse_args()

    shots = sorted(args.dir.glob('*.png'))
    if not shots:
        print(f"No PNG screenshots found in {args.dir}")
        sys.exit(1)

    print(f"Analyzing {len(shots)} screenshots in {args.dir}")

    blanks = find_blank(shots, args.threshold_blank)
    print(f"\nBlank/near-blank frames (stddev < {args.threshold_blank}): "
          f"{len(blanks)}")
    for b in blanks[:20]:
        print(f"  {b['file']}  stddev={b['stddev']:.2f} mean={b['mean']:.1f}")
    if len(blanks) > 20:
        print(f"  ... and {len(blanks) - 20} more")

    dup_groups = find_duplicates(shots, args.threshold_dup)
    dup_frames = sum(len(g) - 1 for g in dup_groups)
    print(f"\nVisually duplicate groups (hamming <= {args.threshold_dup}): "
          f"{len(dup_groups)} groups, {dup_frames} redundant frames")
    for g in dup_groups[:10]:
        names = ', '.join(Path(x).name for x in g[:4])
        more = f" (+{len(g)-4} more)" if len(g) > 4 else ""
        print(f"  [{len(g)}] {names}{more}")
    if len(dup_groups) > 10:
        print(f"  ... and {len(dup_groups) - 10} more groups")

    det_diffs, det_missing = [], []
    if args.baseline_dir:
        det_diffs, det_missing = check_determinism(
            shots, args.baseline_dir, args.threshold_dup)
        print(f"\nDeterminism vs {args.baseline_dir}: "
              f"{len(det_diffs)} changed, {len(det_missing)} new files")
        for d in det_diffs[:20]:
            print(f"  CHANGED {d['file']} hamming={d['hamming_vs_baseline']}")
        for m in det_missing[:20]:
            print(f"  NEW     {m}")

    total_issues = len(blanks) + dup_frames + len(det_diffs)
    print(f"\nSummary: {total_issues} issues "
          f"({len(blanks)} blank, {dup_frames} duplicate, "
          f"{len(det_diffs)} non-deterministic)")

    if args.json:
        args.json.write_text(json.dumps({
            "analyzed": len(shots),
            "blank": blanks,
            "duplicate_groups": [[str(x) for x in g] for g in dup_groups],
            "determinism_changed": det_diffs,
            "determinism_new": det_missing,
        }, indent=2))
        print(f"Results written to {args.json}")


if __name__ == '__main__':
    main()

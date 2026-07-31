"""Find API files that are deployed but no longer generated.

The gh-pages branch accumulates files forever: Hugo copies static/api into
public/ but never removes files that a previous build produced. Renaming a
shop id therefore leaves the old file behind, still served over HTTP but
referenced by nothing.

The generated output is the only authority on what should exist, so run
`make generate` first and compare its output against the deployed branch:

    make generate
    python3 scripts/find_stale_api.py

Note that a file being stale is a property of the *current* data. Restoring
archived data (data/kitchen_cars_past.json) brings shops back into the
generated set, so always regenerate before trusting the result.
"""

import argparse
import os
import subprocess
import sys


def deployed_files(branch, prefix):
    """List files under prefix on the given git branch."""
    out = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", branch, prefix],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return {p for p in out.split("\0") if p}


def generated_files(output_dir, prefix):
    """List files under output_dir/prefix, as paths relative to output_dir."""
    results = set()
    for root, _, files in os.walk(os.path.join(output_dir, prefix)):
        for name in files:
            path = os.path.join(root, name)
            results.add(os.path.relpath(path, output_dir))
    return results


def find_stale(output_dir, branch, prefix):
    deployed = deployed_files(branch, prefix)
    generated = generated_files(output_dir, prefix)
    if not generated:
        print(f"No generated files under {output_dir}/{prefix}. Run 'make generate' first.",
              file=sys.stderr)
        sys.exit(2)
    return sorted(deployed - generated), sorted(generated - deployed), deployed, generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find stale API files on the deployed branch")
    parser.add_argument("-o", "--output-dir", default="static",
                        help="Directory the generator wrote to (default: static)")
    parser.add_argument("-b", "--branch", default="origin/gh-pages",
                        help="Deployed branch to audit (default: origin/gh-pages)")
    parser.add_argument("-p", "--prefix", default="api/",
                        help="Path prefix to compare (default: api/)")
    args = parser.parse_args()

    stale, undeployed, deployed, generated = find_stale(args.output_dir, args.branch, args.prefix)

    print(f"deployed: {len(deployed)}, generated: {len(generated)}")
    print(f"\nStale ({len(stale)}) - on {args.branch} but no longer generated:")
    for path in stale:
        print(f"  {path}")
    print(f"\nNot yet deployed ({len(undeployed)}) - generated but missing from {args.branch}:")
    for path in undeployed:
        print(f"  {path}")

    sys.exit(1 if stale else 0)

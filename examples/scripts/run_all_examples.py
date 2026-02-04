#!/usr/bin/env python3
"""
Automatically discover and run all examples in the examples directory.

This script scans the examples directory for valid test cases (those with
golden.py and kernels/kernel_config.py) and runs them all.

The examples are organized by runtime type under examples/{runtime}/.

Usage:
    python examples/scripts/run_all_examples.py --platform a2a3
    python examples/scripts/run_all_examples.py -p a2a3sim
    python examples/scripts/run_all_examples.py --runtime host_build_graph -p a2a3sim
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def discover_examples(examples_dir: Path, runtime_name: str = None) -> List[Tuple[Path, Path, str]]:
    """
    Discover all valid examples in the examples directory.

    An example is considered valid if it contains:
    - golden.py file
    - kernels/kernel_config.py file

    Args:
        examples_dir: Path to the examples directory
        runtime_name: Optional runtime name to filter examples (e.g., 'host_build_graph')

    Returns:
        List of tuples (kernels_dir, golden_py_path, runtime_name)
    """
    examples = []

    # Determine which runtime directories to scan
    if runtime_name:
        # Scan only the specified runtime directory
        runtime_dirs = [examples_dir / runtime_name]
    else:
        # Scan all runtime directories (exclude scripts directory)
        runtime_dirs = [
            item for item in examples_dir.iterdir()
            if item.is_dir() and item.name != 'scripts'
        ]

    # Scan each runtime directory for examples
    for runtime_dir in runtime_dirs:
        if not runtime_dir.exists():
            print(f"Warning: Runtime directory not found: {runtime_dir.name}")
            continue

        current_runtime = runtime_dir.name
        print(f"\nScanning runtime: {current_runtime}")

        # Scan all subdirectories in the runtime directory
        for item in runtime_dir.iterdir():
            if not item.is_dir():
                continue

            golden_py = item / "golden.py"
            kernels_dir = item / "kernels"
            kernel_config = kernels_dir / "kernel_config.py"

            # Check if this is a valid example
            if golden_py.exists() and kernel_config.exists():
                examples.append((kernels_dir, golden_py, current_runtime))
                print(f"  Found example: {item.name}")
            else:
                missing = []
                if not golden_py.exists():
                    missing.append("golden.py")
                if not kernel_config.exists():
                    missing.append("kernels/kernel_config.py")
                print(f"  Skipping {item.name}: missing {', '.join(missing)}")

    return examples


def run_example(kernels_dir: Path, golden_py: Path, platform: str,
                device: int = None, verbose: int = 1) -> bool:
    """
    Run a single example using run_example.py.

    Args:
        kernels_dir: Path to the kernels directory
        golden_py: Path to the golden.py file
        platform: Platform to run on (a2a3 or a2a3sim)
        device: Optional device ID
        verbose: Verbosity level (0=silent, 1=normal, 2=verbose)

    Returns:
        True if test passed, False otherwise
    """
    # Get the run_example.py script path
    script_dir = Path(__file__).parent
    run_example_script = script_dir / "run_example.py"

    # Build command
    cmd = [
        sys.executable,
        str(run_example_script),
        "-k", str(kernels_dir),
        "-g", str(golden_py),
        "-p", platform,
        "-v", str(verbose),
    ]

    if device is not None:
        cmd.extend(["-d", str(device)])

    # Run the test
    example_name = kernels_dir.parent.name
    print(f"\n{'=' * 60}")
    print(f"Running: {example_name} (platform: {platform})")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"FAILED: {example_name}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Discover and run all examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-p", "--platform",
        default="a2a3",
        choices=["a2a3", "a2a3sim"],
        help="Platform name: 'a2a3' for hardware, 'a2a3sim' for simulation (default: a2a3)"
    )

    parser.add_argument(
        "-d", "--device",
        type=int,
        default=None,
        help="Device ID (default: from PTO_DEVICE_ID env or 0)"
    )

    parser.add_argument(
        "-v", "--verbose",
        type=int,
        default=1,
        choices=[0, 1, 2],
        help="Verbosity level: 0=silent (errors only), 1=normal (default), 2=verbose (all output)"
    )

    parser.add_argument(
        "--examples-dir",
        type=Path,
        default=None,
        help="Path to examples directory (default: auto-detect)"
    )

    parser.add_argument(
        "--runtime",
        default=None,
        help="Runtime name (e.g., host_build_graph). If not specified, run all runtimes."
    )

    args = parser.parse_args()

    # Determine examples directory
    if args.examples_dir:
        examples_dir = args.examples_dir
    else:
        script_dir = Path(__file__).parent.resolve()
        examples_dir = script_dir.parent

    if not examples_dir.exists():
        print(f"Error: Examples directory not found: {examples_dir}")
        return 1

    print(f"Scanning for examples in: {examples_dir}")
    print(f"Platform: {args.platform}")
    if args.runtime:
        print(f"Runtime filter: {args.runtime}")
    else:
        print(f"Runtime filter: all")
    print()

    # Discover examples
    examples = discover_examples(examples_dir, args.runtime)

    if not examples:
        print("No valid examples found!")
        return 1

    print(f"\nFound {len(examples)} example(s)")
    print()

    # Run all examples
    failed = []
    passed = []

    for kernels_dir, golden_py, runtime_name in examples:
        example_name = f"{runtime_name}/{kernels_dir.parent.name}"
        success = run_example(
            kernels_dir,
            golden_py,
            args.platform,
            args.device,
            args.verbose
        )

        if success:
            passed.append(example_name)
        else:
            failed.append(example_name)

    # Print summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total: {len(examples)}")
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")

    if passed:
        print(f"\nPassed examples:")
        for name in passed:
            print(f"  ✓ {name}")

    if failed:
        print(f"\nFailed examples:")
        for name in failed:
            print(f"  ✗ {name}")
        return 1

    print(f"\n{'=' * 60}")
    print("ALL EXAMPLES PASSED!")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

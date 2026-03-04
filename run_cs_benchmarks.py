#!/usr/bin/env python3
"""
CS Benchmarks - Compare Claude Opus models with different reasoning efforts

This script runs multiple benchmark configurations to compare:
- Claude Opus 4.5 vs Claude Opus 4.6
- Different reasoning effort levels (low, medium, high, max)

Results are saved to separate directories for analysis.

Note: max effort is only available on Opus 4.6
"""

import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Benchmark configurations
# Format: (model_name, effort_level, output_reasoning, description)
CONFIGURATIONS = [
    # Claude Opus 4.6 - All effort levels
    ("claude-4-6-opus", "low", "false", "Opus 4.6 - Low Effort (speed/cost optimized)"),
    ("claude-4-6-opus", "medium", "false", "Opus 4.6 - Medium Effort (balanced)"),
    ("claude-4-6-opus", "high", "false", "Opus 4.6 - High Effort (default, best quality)"),
    ("claude-4-6-opus", "max", "false", "Opus 4.6 - Max Effort (absolute highest capability)"),

    # Claude Opus 4.5 - High effort only (for comparison baseline)
    ("claude-4-5-sonnet", "high", "false", "Opus 4.5 - High Effort (baseline)"),
]

# Tasks to run (None = all tasks, or specify specific task IDs)
# Examples: None for all, "level1_TCPServer" for single task
TASK_FILTER = None  # Set to None for --all, or a task_id string for --task

# Additional settings
MAX_TOOL_CALLS = 25
MAX_TOKENS = 8192
VERBOSE = False  # Set to True to see detailed agent reasoning during runs


def run_benchmark(model: str, effort: str, output_reasoning: str, description: str, results_base_dir: Path):
    """Run a single benchmark configuration."""
    print(f"\n{'='*80}")
    print(f"  {description}")
    print(f"  Model: {model}")
    print(f"  Effort: {effort} | Output Reasoning: {output_reasoning}")
    print(f"{'='*80}\n")

    # Create results directory with timestamp and config
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = model.replace(".", "_").replace("-", "_")
    results_dir = results_base_dir / f"{safe_model}_effort_{effort}_{timestamp}"

    # Build command
    cmd = [
        sys.executable,
        "run_benchmark.py",
        "--provider", "openai",
        "--model", model,
        "--report", str(results_dir),
        "--max-tool-calls", str(MAX_TOOL_CALLS),
        "--max-tokens", str(MAX_TOKENS),
        "--openai-header", "User-Agent:FAIS",
        "--openai-header", f"X-CS-REASONING-EFFORT:{effort}",
        "--openai-header", f"X-CS-OUTPUT-REASONING:{output_reasoning}",
    ]

    # Add task selection
    if TASK_FILTER:
        cmd.extend(["--task", TASK_FILTER])
    else:
        cmd.append("--all")

    # Add verbose flag if needed
    if VERBOSE:
        cmd.append("-v")

    # Run benchmark
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✓ Completed: {description}")
        print(f"  Results saved to: {results_dir}")
        return True, results_dir
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed: {description}")
        print(f"  Error: {e}")
        return False, None


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Run CS Benchmarks comparing Claude models with different reasoning efforts'
    )
    parser.add_argument(
        '--report',
        type=Path,
        default=Path(__file__).parent / "results_cs_comparison",
        help='Base directory for benchmark results (default: results_cs_comparison/)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all tasks (ignored, kept for compatibility)'
    )
    parser.add_argument(
        '--provider',
        type=str,
        default='openai',
        help='Provider to use (ignored, kept for compatibility)'
    )

    args = parser.parse_args()
    results_base_dir = args.report

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          CS Benchmarks - Claude Comparison                    ║
║                                                                              ║
║  Comparing Claude Opus 4.5 vs 4.6 with different reasoning effort levels    ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

    # Create base results directory
    results_base_dir.mkdir(parents=True, exist_ok=True)

    print(f"Base results directory: {results_base_dir}")
    print(f"Task filter: {'All tasks' if TASK_FILTER is None else TASK_FILTER}")
    print(f"Configurations to run: {len(CONFIGURATIONS)}")
    print(f"Max tool calls: {MAX_TOOL_CALLS}")
    print(f"Max tokens: {MAX_TOKENS}")
    print(f"Verbose: {VERBOSE}")

    # Confirmation
    print("\nPress Enter to start, or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(0)

    # Track results
    results = []
    start_time = datetime.now()

    # Run each configuration
    for i, (model, effort, output_reasoning, description) in enumerate(CONFIGURATIONS, 1):
        print(f"\n[Configuration {i}/{len(CONFIGURATIONS)}]")
        success, results_dir = run_benchmark(model, effort, output_reasoning, description, results_base_dir)
        results.append({
            "model": model,
            "effort": effort,
            "description": description,
            "success": success,
            "results_dir": results_dir,
        })

    # Print summary
    end_time = datetime.now()
    duration = end_time - start_time

    print(f"\n\n{'='*80}")
    print(f"  SUMMARY - CS Benchmarks Comparison")
    print(f"{'='*80}")
    print(f"Total time: {duration}")
    print(f"Completed: {sum(1 for r in results if r['success'])}/{len(results)}")
    print(f"\nResults:")

    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"  {status} {r['description']}")
        if r["results_dir"]:
            print(f"    → {r['results_dir']}")

    print(f"\n\nAll results saved to: {results_base_dir}")
    print("\nTo analyze results, compare the benchmark_report.json files in each directory:")
    print(f"  cd {results_base_dir}")
    print("  cat */benchmark_report.json | jq '.aggregate_metrics | {{total_score, main_score, bonus_score}}'")
    print("\n")

    # Exit with error if any failed
    if not all(r["success"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()

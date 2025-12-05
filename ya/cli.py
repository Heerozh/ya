"""Command line interface for ya benchmark framework."""

import argparse
import sys
import multiprocessing
from pathlib import Path

from .runner import run_benchmarks
from .stat import calculate_cpm, calculate_cps, calculate_kstat


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Ya - A Python async benchmark framework"
    )
    parser.add_argument(
        "script",
        type=str,
        help="Path to the Python script containing benchmark functions",
    )
    parser.add_argument(
        "-n",
        "--num-tasks",
        type=int,
        default=10,
        help="Number of TOTAL async tasks (default: 10)",
    )
    parser.add_argument(
        "-t",
        "--duration",
        type=float,
        default=5,
        help="Test duration in minutes (default: 5)",
    )

    args = parser.parse_args()

    # get number of workers
    cpu = multiprocessing.cpu_count()
    workers = cpu * 2
    workers = args.num_tasks if workers > args.num_tasks else workers
    num_tasks = max(1, int(args.num_tasks // workers))

    # Validate script path
    script_path = Path(args.script)
    if not script_path.exists():
        print(f"Error: Script file '{args.script}' not found", file=sys.stderr)
        return 1

    # Run benchmarks
    try:
        results_df = run_benchmarks(
            script_path=str(script_path.absolute()),
            num_tasks=num_tasks,
            num_workers=args.workers,
            duration_minutes=args.duration,
        )
        # import pandas as pd

        # results_df = pd.read_csv("benchmark_results.csv")  # For testing purpose

        # Display results
        if results_df is not None and not results_df.empty:
            print("\n" + "=" * 80)
            print("Benchmark Results Summary")
            print("=" * 80)

            cpm_stats = calculate_cpm(results_df)
            print("\nCalls Per Minute (CPM) Statistics:")
            print(cpm_stats.to_markdown(index=False))

            cps_stats = calculate_cps(results_df)
            print("\nAverage CPS (Calls Per Second) per Function:")
            print(cps_stats.to_markdown())

            k_stats = calculate_kstat(results_df)
            print("\nFunction Execution Time Statistics:")
            print(k_stats.to_markdown())

            print("=" * 80)

            # Optionally save to CSV
            output_file = "benchmark_results.csv"
            results_df.to_csv(output_file, index=False)
            print(f"\nFull results saved to: {output_file}")
        else:
            print("No benchmark results collected.")

        return 0
    except Exception as e:
        print(f"Error running benchmarks: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

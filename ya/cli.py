"""Command line interface for ya benchmark framework."""

import argparse
import sys
from pathlib import Path

from .runner import run_benchmarks
from .stat import calculate_cpm, calculate_cps


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
        help="Number of async tasks per worker (default: 10)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=5,
        help="Number of worker processes (default: 5)",
    )
    parser.add_argument(
        "-t",
        "--duration",
        type=int,
        default=1,
        help="Test duration in minutes (default: 1)",
    )

    args = parser.parse_args()

    # Validate script path
    script_path = Path(args.script)
    if not script_path.exists():
        print(f"Error: Script file '{args.script}' not found", file=sys.stderr)
        return 1

    # Run benchmarks
    try:
        results_df = run_benchmarks(
            script_path=str(script_path.absolute()),
            num_tasks=args.num_tasks,
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
            print(cpm_stats.to_markdown())

            cpm_stats = calculate_cps(results_df)
            print("\nAverage CPS (Calls Per Second) per Function:")
            print(cpm_stats.to_markdown(index=False))
            
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

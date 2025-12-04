"""Command line interface for ya benchmark framework."""

import argparse
import sys
from pathlib import Path
from .runner import run_benchmarks


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
        default=5,
        help="Test duration in minutes (default: 5)",
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
        
        # Display results
        if results_df is not None and not results_df.empty:
            print("\n" + "=" * 80)
            print("Benchmark Results Summary")
            print("=" * 80)
            
            # Group by benchmark and show statistics
            for benchmark_name in results_df['benchmark'].unique():
                bench_data = results_df[results_df['benchmark'] == benchmark_name]
                print(f"\nBenchmark: {benchmark_name}")
                print(f"  Total executions: {len(bench_data)}")
                print(f"  Execution time (seconds):")
                print(f"    Mean:   {bench_data['execution_time'].mean():.6f}")
                print(f"    Median: {bench_data['execution_time'].median():.6f}")
                print(f"    Min:    {bench_data['execution_time'].min():.6f}")
                print(f"    Max:    {bench_data['execution_time'].max():.6f}")
                print(f"    Std:    {bench_data['execution_time'].std():.6f}")
            
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

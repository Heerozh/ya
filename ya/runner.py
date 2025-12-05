"""Core benchmark runner implementation."""

import asyncio
import importlib.util
import inspect
import multiprocessing
import re
import sys
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple

import pandas as pd


def load_benchmark_module(script_path: str) -> Any:
    """
    Load a benchmark script as a Python module.

    Args:
        script_path: Path to the benchmark script

    Returns:
        The loaded module object
    """
    # Create a unique module name based on the script path and timestamp
    # to avoid conflicts when loading multiple modules
    module_name = f"benchmark_module_{abs(hash(script_path))}"

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load script: {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


def discover_benchmarks(script_path: str) -> Dict[str, Callable]:
    """
    Discover all benchmark functions from a script.

    Returns a dict mapping benchmark names to their function objects.
    """
    # Load the script as a module
    module = load_benchmark_module(script_path)

    # Find all functions starting with 'benchmark_' but not ending with '_setup' or '_teardown'
    benchmarks = {}
    for name, obj in inspect.getmembers(module):
        if (
            name.startswith("benchmark_")
            and not name.endswith("_setup")
            and not name.endswith("_teardown")
            and inspect.iscoroutinefunction(obj)
        ):
            benchmarks[name] = obj

    return benchmarks


async def run_single_executor(
    benchmark_func: Callable,
    benchmark_name: str,
    module: Any,
    duration_minutes: float,
) -> List[Tuple[float, float]]:
    """
    Run a single async executor for a benchmark.

    Returns a list of [calendar_minute, execution_time] tuples.
    """
    results = []

    # Run setup function if exists
    setup_name = f"{benchmark_name}_setup"
    setup_result = ()
    if hasattr(module, setup_name):
        setup_func = getattr(module, setup_name)
        if inspect.iscoroutinefunction(setup_func):
            setup_result = await setup_func()
            if setup_result is None:
                setup_result = ()
            if not isinstance(setup_result, tuple):
                setup_result = (setup_result,)

    # Record start time
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)

    # Run benchmark loop
    while time.time() < end_time:
        # Record calendar minute and execution time
        call_start = time.time()

        # Execute benchmark
        await benchmark_func(*setup_result)

        # Calculate execution time
        execution_time = (time.time() - call_start) * 1000.0  # in milliseconds

        # Store result
        results.append((call_start, execution_time))

    # Run teardown function if exists
    teardown_name = f"{benchmark_name}_teardown"
    if hasattr(module, teardown_name):
        teardown_func = getattr(module, teardown_name)
        if inspect.iscoroutinefunction(teardown_func):
            await teardown_func(*setup_result)

    return results


async def run_worker_async(
    script_path: str,
    benchmark_name: str,
    num_tasks: int,
    duration_minutes: float,
) -> List[Tuple[float, float]]:
    """
    Run multiple async tasks for a single benchmark in a worker process.

    Returns combined results from all tasks.
    """
    # Load the module in the worker process
    module = load_benchmark_module(script_path)

    # Get the benchmark function
    benchmark_func = getattr(module, benchmark_name)

    # Create tasks using asyncio.gather
    tasks = [
        run_single_executor(benchmark_func, benchmark_name, module, duration_minutes)
        for _ in range(num_tasks)
    ]

    # Gather results from all tasks
    all_results = await asyncio.gather(*tasks)

    # Flatten results
    combined_results = []
    for task_results in all_results:
        combined_results.extend(task_results)

    return combined_results


def worker_process_func(args: Tuple[str, str, int, float]) -> List[Tuple[float, float]]:
    """
    Worker process function for multiprocessing.Pool.map.

    This function runs the async event loop for the worker.
    """
    script_path, benchmark_name, num_tasks, duration_minutes = args

    # Run the async worker
    return asyncio.run(
        run_worker_async(script_path, benchmark_name, num_tasks, duration_minutes)
    )


def run_benchmarks(
    script_path: str,
    num_tasks: int,
    num_workers: int,
    duration_minutes: float,
    specific_task: str = "",
) -> pd.DataFrame:
    """
    Run all benchmarks and return results as a pandas DataFrame.

    Args:
        script_path: Path to the benchmark script
        num_tasks: Number of async tasks per worker
        num_workers: Number of worker processes
        duration_minutes: Duration to run each benchmark in minutes

    Returns:
        DataFrame with benchmark results
    """
    # Discover benchmarks
    benchmarks = discover_benchmarks(script_path)
    if specific_task:
        benchmarks = {
            name: func
            for name, func in benchmarks.items()
            if re.match(specific_task, name) or specific_task in name
        }

    if not benchmarks:
        print("No benchmark functions found (functions should start with 'benchmark_')")
        return pd.DataFrame()

    print(f"Found {len(benchmarks)} benchmark(s): {', '.join(benchmarks.keys())}")
    print(
        f"Running with {num_workers} workers, {num_tasks} tasks per worker, for {duration_minutes} minute(s)"
    )

    all_data = []

    # Run each benchmark
    for benchmark_name in benchmarks.keys():
        print(f"\nRunning benchmark: {benchmark_name}")

        # Prepare arguments for workers
        worker_args = [
            (script_path, benchmark_name, num_tasks, duration_minutes)
            for _ in range(num_workers)
        ]

        # Run workers using multiprocessing.Pool.map
        with multiprocessing.Pool(processes=num_workers) as pool:
            worker_results = pool.map(worker_process_func, worker_args)

        # Combine results from all workers
        for worker_idx, results in enumerate(worker_results):
            for timestamp, execution_time in results:
                all_data.append(
                    {
                        "benchmark": benchmark_name,
                        "worker": worker_idx,
                        "timestamp": timestamp,
                        "execution_time": execution_time,
                    }
                )

        print(f"  Collected {sum(len(r) for r in worker_results)} data points")

    # Create DataFrame
    if all_data:
        df = pd.DataFrame(all_data)
        return df
    else:
        return pd.DataFrame()

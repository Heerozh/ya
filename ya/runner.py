"""Core benchmark runner implementation."""

import asyncio
import importlib.util
import inspect
import multiprocessing
import re
import sys
import time
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
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load script: {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


def discover_benchmarks(script_path: str) -> Dict[str, list[str]]:
    """
    Discover all benchmark functions from a script.

    Returns a dict mapping benchmark names to their function objects.
    """
    # Load the script as a module
    module = load_benchmark_module(script_path)

    # Find all functions starting with 'benchmark_'
    benchmarks = {}
    for name, obj in inspect.getmembers(module):
        if name.startswith("benchmark_") and inspect.iscoroutinefunction(obj):
            # get fixtures
            fixtures = list(inspect.signature(obj).parameters.keys())
            benchmarks[name] = fixtures

    return benchmarks


async def run_fixture(module, name, cache):
    gens = []

    # get fixture func
    func = getattr(module, name)

    # get fixture dependencies
    dep_fixture = list(inspect.signature(func).parameters.keys())
    args = []
    if dep_fixture:
        for dep_name in dep_fixture:
            if dep_name in cache:
                args.append(cache[dep_name])
            else:
                new_gens, dep = await run_fixture(module, dep_name, cache)
                gens.extend(new_gens)
                args.append(dep)

    # get fixture value
    value = None
    if inspect.iscoroutinefunction(func):
        value = await func(*args)
    elif inspect.isasyncgenfunction(func):
        gen = func(*args)
        gens.append(gen)
        value = await gen.__anext__()
    else:
        raise RuntimeError(f"Fixtures function {name} must be async")

    # Cache the fixture value
    cache[name] = value
    return gens, value


async def run_single_executor(
    benchmark_func: Callable,
    benchmark_name: str,
    fixture_names: list[str],
    module: Any,
    duration_minutes: float,
) -> List[Tuple[float, float, Any]]:
    """
    Run a single async executor for a benchmark.

    Returns a list of [calendar_minute, execution_time] tuples.
    """
    results = []

    # Run setup function if exists
    fixture_cache: Dict[str, Any] = {}
    fixture_enumerators = []
    fixture_results = []
    for fixture_name in fixture_names:
        gens, value = await run_fixture(module, fixture_name, fixture_cache)
        fixture_enumerators.extend(gens)
        fixture_results.append(value)

    # Record start time
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)

    # Run benchmark loop
    while time.time() < end_time:
        # Record calendar minute and execution time
        call_start = time.time()

        # Execute benchmark
        rtn = await benchmark_func(*fixture_results)

        # Calculate execution time
        execution_time = (time.time() - call_start) * 1000.0  # in milliseconds

        # Store result
        results.append((call_start, execution_time, rtn))

    # Run teardown function if exists
    for gen in fixture_enumerators:
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    return results


async def run_worker_async(
    script_path: str,
    benchmark_name: str,
    fixtures: list[str],
    num_tasks: int,
    duration_minutes: float,
) -> List[Tuple[float, float, Any]]:
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
        run_single_executor(
            benchmark_func, benchmark_name, fixtures, module, duration_minutes
        )
        for _ in range(num_tasks)
    ]

    # Gather results from all tasks
    all_results = await asyncio.gather(*tasks)

    # Flatten results
    combined_results = []
    for task_results in all_results:
        combined_results.extend(task_results)

    return combined_results


def worker_process_func(
    args: Tuple[str, str, list[str], int, float],
) -> List[Tuple[float, float, Any]]:
    """
    Worker process function for multiprocessing.Pool.map.

    This function runs the async event loop for the worker.
    """
    script_path, benchmark_name, fixtures, num_tasks, duration_minutes = args

    # Run the async worker
    return asyncio.run(
        run_worker_async(
            script_path, benchmark_name, fixtures, num_tasks, duration_minutes
        )
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
            name: fixtures
            for name, fixtures in benchmarks.items()
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
    for benchmark_name, fixtures in benchmarks.items():
        print(f"\nRunning benchmark: {benchmark_name}")

        # Prepare arguments for workers
        worker_args = [
            (script_path, benchmark_name, fixtures, num_tasks, duration_minutes)
            for _ in range(num_workers)
        ]

        # Run workers using multiprocessing.Pool.map
        if num_workers > 1:
            print(f"  Using multiprocessing with {num_workers} workers")
            with multiprocessing.Pool(processes=num_workers) as pool:
                worker_results = pool.map(worker_process_func, worker_args)
        else:
            print("  Running in the main process")
            worker_results = [worker_process_func(args) for args in worker_args]

        # Combine results from all workers
        for worker_idx, results in enumerate(worker_results):
            for timestamp, execution_time, rtn in results:
                all_data.append(
                    {
                        "benchmark": benchmark_name,
                        "worker": worker_idx,
                        "timestamp": timestamp,
                        "execution_time": execution_time,
                        "return_value": rtn,
                    }
                )

        print(f"  Collected {sum(len(r) for r in worker_results)} data points")

    # Create DataFrame
    if all_data:
        df = pd.DataFrame(all_data)
        return df
    else:
        return pd.DataFrame()

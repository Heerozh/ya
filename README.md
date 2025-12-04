# ya

ya is a Python async benchmark framework for measuring the performance of asynchronous functions.

ya 是一个简易的 Python 高性能异步基准测试框架，主要用于压测吞吐量。

## Installation

```bash
pip install -e .
```

## Usage

```bash
ya <script.py> -n <num_tasks> -w <num_workers> -t <duration_minutes>
```

### Options

- `script.py`: Path to Python script containing benchmark functions
- `-n, --num-tasks`: Number of async tasks per worker process (default: 10)
- `-w, --workers`: Number of worker processes (default: 5)
- `-t, --duration`: Test duration in minutes (default: 5)

## Writing Benchmarks

Create a Python script with async functions that start with `benchmark_`:

```python
import asyncio

# This function will be benchmarked
async def benchmark_my_function():
    await asyncio.sleep(0.01)
    # Your async code here

# Optional: Setup function (runs once per async task before benchmarking)
async def benchmark_my_function_setup():
    # Setup code here
    pass

# Optional: Teardown function (runs once per async task after benchmarking)
async def benchmark_my_function_teardown():
    # Cleanup code here
    pass
```

## How It Works

1. **Discovery**: Ya finds all async functions starting with `benchmark_` (excluding `_setup` and `_teardown` suffixes)
2. **Worker Processes**: Spawns `-w` worker processes using `multiprocessing.Pool.map`
3. **Async Tasks**: Each worker creates `-n` async tasks using `asyncio.gather`
4. **Execution Loop**: Each task:
   - Calls `benchmark_<name>_setup()` if it exists
   - Enters a while loop for `-t` minutes
   - Records [calendar minute, execution time] for each benchmark call
   - Calls `benchmark_<name>_teardown()` if it exists
5. **Result Collection**: Main process merges all results into a pandas DataFrame
6. **Output**: Displays summary statistics and saves detailed results to `benchmark_results.csv`

## Example

```bash
# Run benchmark with 2 workers, 3 tasks per worker, for 1 minute
ya my_benchmark.py -n 3 -w 2 -t 1
```

## Output

ya 会收集所有基准测试结果并生成统计数据。

Full results are saved to `benchmark_results.csv` with columns:

- `benchmark`: Benchmark function name
- `worker`: Worker process ID
- `calendar_minute`: Calendar minute when the call started
- `execution_time`: Time taken to execute the benchmark function (in milliseconds)

收集的统计数据为：

- CPM (calls per minute), average Throughput (CPS calls per second)
- Mean, k95, k99 response times

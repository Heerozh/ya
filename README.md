# ya

ya is a Python async benchmark framework for measuring the performance of asynchronous functions.

ya 是一个简易的 Python 高性能多进程异步基准测试框架，主要用于压测吞吐量。
因为基于异步，所以可以单机跑出非常高的吞吐量。

## Installation

```bash
uv add --dev https://github.com/Heerozh/ya.git
```

## Usage

```bash
ya <script.py> -n <num_async_tasks> -t <duration_minutes>
```

### Options

- `script.py`: Path to Python script containing benchmark functions
- `-n, --num-tasks`: Number of TOTAL async tasks (default: 200)
- `-t, --duration`: Test duration in minutes (default: 5), can be float

## Writing Benchmarks

Create a Python script with async functions that start with `benchmark_`:

```python
import asyncio

# Optional: Setup function (runs once per async task before benchmarking)
async def benchmark_my_function_setup():
    # Setup code here
    return data1, data2

# This function will be benchmarked
async def benchmark_my_function(data1, data2):
    await asyncio.sleep(0.01)
    # Your async code here

# Optional: Teardown function (runs once per async task after benchmarking)
async def benchmark_my_function_teardown(data1, data2):
    # Cleanup code here
    pass
```

## How It Works

1. **Discovery**: Ya finds all async functions starting with `benchmark_` (excluding `_setup` and `_teardown` suffixes)
2. **Worker Processes**: Spawns `cpu_core * 2` worker processes using `multiprocessing.Pool.map`
3. **Async Tasks**: Each worker creates `num-tasks//worker` async tasks using `asyncio.gather`
4. **Execution Loop**: Each task:
   - Calls `benchmark_<name>_setup()` if it exists
   - Enters a while loop for `-t` minutes
   - Records [start time, execution time] for each benchmark call
   - Calls `benchmark_<name>_teardown()` if it exists
5. **Result Collection**: Main process merges all results into a pandas DataFrame
6. **Output**: Displays summary statistics and saves detailed results to `benchmark_results.csv`

## Example

```bash
ya my_benchmark.py -n 200 -t 1
```

## Output

ya 会收集所有基准测试结果并生成统计数据。

Full results are saved to `benchmark_results.csv` with columns:

- `benchmark`: Benchmark function name
- `worker`: Worker process ID
- `timestamp`: Start time when the call started
- `execution_time`: Time taken to execute the benchmark function (in milliseconds)

收集的统计数据为 Statistics：

- CPM (calls per minute), average Throughput (CPS calls per second)
- Mean, k95, k99 response times

注意，CPM/CPS数据，必须目标服务器跑满CPU才正确。
Remember, CPM/CPS data is only accurate if the target server has 100% CPU utilization.

## 输出示例 Output Example

Found 2 benchmark(s): benchmark_cpu_calculation, benchmark_simple_sleep
Running with 24 workers, 8 tasks per worker, for 0.1 minute(s)

Calls Per Minute (CPM) Statistics:

| benchmark                 | execution_time            | execution_count   |
|:--------------------------|:--------------------------|:------------------|
| benchmark_cpu_calculation | 2025-12-05 12:05:00+08:00 | 93,750            |
| benchmark_simple_sleep    | 2025-12-05 12:05:00+08:00 | 69,000            |

Average CPS (Calls Per Second) per Function:

|                           | CPS           |
|:--------------------------|:--------------|
| benchmark_cpu_calculation | 15,366,455.71 |
| benchmark_simple_sleep    | 11,531,440.76 |

Function Execution Time Statistics:

|                           |   Mean |   k95 |   k99 |   Count |   Min |   Max |   Median |
|:--------------------------|-------:|------:|------:|--------:|------:|------:|---------:|
| benchmark_cpu_calculation |  12.3  | 20.71 | 26.52 |   93750 |  1.11 | 58.84 |    14.49 |
| benchmark_simple_sleep    |  16.72 | 22.06 | 24.31 |   69000 | 10.06 | 48.35 |    15.82 |

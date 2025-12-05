"""Example benchmark script for testing ya framework."""

import asyncio
import random


async def data1():
    """
    fixture with task scope:
    run once per benchmark task, cleanup after it ends
    """
    yield 1
    # 压测结束后执行到这
    print("cleanup data1")


async def data2():
    return 2


# Example benchmark 1: Simple async sleep
async def benchmark_simple_sleep(data1, data2):
    """A simple benchmark that sleeps for a short time."""
    await asyncio.sleep(0.01)
    return data1 * data2


# Example benchmark 2: CPU-bound calculation
async def benchmark_cpu_calculation():
    """A benchmark that does some CPU-intensive work."""
    # Simulate some work
    await asyncio.sleep(0.001)
    # 返回正态分布的int范围随机数
    return int(random.gauss(5, 0.5))

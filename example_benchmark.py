"""Example benchmark script for testing ya framework."""

import asyncio


# Example benchmark 1: Simple async sleep
async def benchmark_simple_sleep():
    """A simple benchmark that sleeps for a short time."""
    await asyncio.sleep(0.01)


async def benchmark_simple_sleep_setup():
    """Setup function for simple_sleep benchmark."""
    pass


async def benchmark_simple_sleep_teardown():
    """Teardown function for simple_sleep benchmark."""
    pass


# Example benchmark 2: CPU-bound calculation
async def benchmark_cpu_calculation():
    """A benchmark that does some CPU-intensive work."""
    # Simulate some work
    result = sum(i * i for i in range(1000))
    await asyncio.sleep(0.001)
    return result


async def benchmark_cpu_calculation_setup():
    """Setup function for cpu_calculation benchmark."""
    pass


async def benchmark_cpu_calculation_teardown():
    """Teardown function for cpu_calculation benchmark."""
    pass

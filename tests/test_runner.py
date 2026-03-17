import asyncio
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from ya import runner


def write_script(tmp_path: Path, content: str) -> Path:
    script_path = tmp_path / "bench_script.py"
    script_path.write_text(textwrap.dedent(content), encoding="utf-8")
    return script_path


def test_discover_benchmarks_only_returns_async_benchmarks(tmp_path: Path):
    script_path = write_script(
        tmp_path,
        """
        async def fixture_dep():
            return "dep"

        async def benchmark_alpha(fixture_dep):
            return fixture_dep

        async def helper():
            return "ignore"

        def benchmark_sync():
            return "ignore"

        async def benchmark_beta():
            return "ok"
        """,
    )

    benchmarks = runner.discover_benchmarks(str(script_path))

    assert benchmarks == {
        "benchmark_alpha": ["fixture_dep"],
        "benchmark_beta": [],
    }


def test_run_fixture_resolves_dependencies_and_caches_results():
    events: list[str] = []

    async def fixture_base():
        events.append("base:setup")
        yield "base"
        events.append("base:teardown")

    async def fixture_child(fixture_base):
        events.append(f"child:{fixture_base}")
        return f"{fixture_base}-child"

    module = SimpleNamespace(
        fixture_base=fixture_base,
        fixture_child=fixture_child,
    )
    cache: dict[str, object] = {}

    async def exercise():
        generators, value = await runner.run_fixture(module, "fixture_child", cache)
        with pytest.raises(StopAsyncIteration):
            await generators[0].__anext__()
        return generators, value

    generators, value = asyncio.run(exercise())

    assert value == "base-child"
    assert cache == {
        "fixture_base": "base",
        "fixture_child": "base-child",
    }
    assert len(generators) == 1
    assert events == ["base:setup", "child:base", "base:teardown"]


def test_run_single_executor_runs_fixture_setup_and_teardown(monkeypatch: pytest.MonkeyPatch):
    events: list[str] = []

    async def fixture_value():
        events.append("fixture:setup")
        yield 3
        events.append("fixture:teardown")

    async def benchmark(fixture_value):
        events.append(f"benchmark:{fixture_value}")
        return fixture_value * 2

    module = SimpleNamespace(fixture_value=fixture_value)
    time_values = iter([0.0, 0.0, 0.05, 0.10, 61.0])
    monkeypatch.setattr(runner.time, "time", lambda: next(time_values))

    results = asyncio.run(
        runner.run_single_executor(
            benchmark,
            "benchmark_demo",
            ["fixture_value"],
            module,
            duration_minutes=1,
        )
    )

    assert results == [(0.05, 50.0, 6, 1)]
    assert events == [
        "fixture:setup",
        "benchmark:3",
        "fixture:teardown",
    ]


def test_run_worker_async_flattens_results_and_calls_task_teardown(monkeypatch: pytest.MonkeyPatch):
    state = {"teardown_calls": 0}

    async def task_teardown():
        state["teardown_calls"] += 1

    module = SimpleNamespace(benchmark_demo=object(), task_teardown=task_teardown)

    async def fake_run_single_executor(
        benchmark_func,
        benchmark_name,
        fixture_names,
        loaded_module,
        duration_minutes,
    ):
        return [(1.0, 2.0, benchmark_name, 1)]

    monkeypatch.setattr(runner, "load_benchmark_module", lambda _: module)
    monkeypatch.setattr(runner, "run_single_executor", fake_run_single_executor)

    results = asyncio.run(
        runner.run_worker_async(
            "script.py",
            "benchmark_demo",
            ["fixture_a"],
            num_tasks=3,
            duration_minutes=0.1,
        )
    )

    assert results == [
        (1.0, 2.0, "benchmark_demo", 1),
        (1.0, 2.0, "benchmark_demo", 1),
        (1.0, 2.0, "benchmark_demo", 1),
    ]
    assert state["teardown_calls"] == 1


def test_run_benchmarks_filters_tasks_and_normalizes_execution_time(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        runner,
        "discover_benchmarks",
        lambda _: {
            "benchmark_keep": ["fixture_x"],
            "benchmark_skip": [],
        },
    )
    monkeypatch.setattr(
        runner,
        "worker_process_func",
        lambda args: [
            (1.0, 10.0, "ok", 2),
            (2.0, 4.0, "ok", 1),
        ],
    )

    result = runner.run_benchmarks(
        script_path="bench.py",
        num_tasks=2,
        num_workers=1,
        duration_minutes=0.5,
        specific_task="keep",
    )

    assert isinstance(result, pd.DataFrame)
    assert result["benchmark"].tolist() == ["benchmark_keep", "benchmark_keep"]
    assert result["worker"].tolist() == [0, 0]
    assert result["execution_time"].tolist() == [5.0, 4.0]
    assert result["execution_count"].tolist() == [2, 1]


def test_run_benchmarks_returns_empty_dataframe_when_no_match(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    monkeypatch.setattr(
        runner,
        "discover_benchmarks",
        lambda _: {"benchmark_alpha": []},
    )

    result = runner.run_benchmarks(
        script_path="bench.py",
        num_tasks=1,
        num_workers=1,
        duration_minutes=0.1,
        specific_task="missing",
    )

    assert result.empty
    assert "No benchmark functions found" in capsys.readouterr().out

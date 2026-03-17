import sys
from pathlib import Path

import pandas as pd
import pytest

from ya import cli


class DummyTable:
    def __init__(self, name: str):
        self.name = name

    def to_markdown(self) -> str:
        return f"| {self.name} |"


class DummyResults:
    empty = False

    def __init__(self):
        self.saved: tuple[str, bool] | None = None

    def to_csv(self, path: str, index: bool = False):
        self.saved = (path, index)


def test_main_returns_error_for_missing_script(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path):
    missing_path = tmp_path / "missing.py"
    monkeypatch.setattr(sys, "argv", ["ya", str(missing_path)])

    exit_code = cli.main()

    assert exit_code == 1
    assert f"Error: Script file '{missing_path}' not found" in capsys.readouterr().err


def test_main_runs_benchmark_and_prints_summary(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path):
    script_path = tmp_path / "bench.py"
    script_path.write_text("# benchmark script\n", encoding="utf-8")

    captured_kwargs: dict[str, object] = {}
    results = DummyResults()

    def fake_run_benchmarks(**kwargs):
        captured_kwargs.update(kwargs)
        return results

    monkeypatch.setattr(cli, "run_benchmarks", fake_run_benchmarks)
    monkeypatch.setattr(cli, "calculate_cpm", lambda _: DummyTable("cpm"))
    monkeypatch.setattr(cli, "calculate_cps", lambda _: DummyTable("cps"))
    monkeypatch.setattr(cli, "calculate_kstat", lambda _: DummyTable("kstat"))
    monkeypatch.setattr(cli, "calculate_rtn_stat", lambda _: DummyTable("rtn"))
    monkeypatch.setattr(cli.multiprocessing, "cpu_count", lambda: 4)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ya", str(script_path), "-n", "3", "-p", "10", "-t", "0.5", "--task", "demo"],
    )

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured_kwargs == {
        "script_path": str(script_path.absolute()),
        "num_tasks": 1,
        "num_workers": 3,
        "duration_minutes": 0.5,
        "specific_task": "demo",
    }
    assert "Benchmark Results Summary" in captured.out
    assert "Full results saved to: benchmark_results.csv" in captured.out
    assert results.saved == ("benchmark_results.csv", False)


def test_main_handles_empty_results(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path):
    script_path = tmp_path / "bench.py"
    script_path.write_text("# benchmark script\n", encoding="utf-8")

    monkeypatch.setattr(cli, "run_benchmarks", lambda **_: pd.DataFrame())
    monkeypatch.setattr(cli.multiprocessing, "cpu_count", lambda: 2)
    monkeypatch.setattr(sys, "argv", ["ya", str(script_path), "-n", "2"])

    exit_code = cli.main()

    assert exit_code == 0
    assert "No benchmark results collected." in capsys.readouterr().out


def test_main_handles_runner_exception(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path):
    script_path = tmp_path / "bench.py"
    script_path.write_text("# benchmark script\n", encoding="utf-8")

    def raise_error(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "run_benchmarks", raise_error)
    monkeypatch.setattr(sys, "argv", ["ya", str(script_path)])

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error running benchmarks: boom" in captured.err

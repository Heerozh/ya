from zoneinfo import ZoneInfo

import pandas as pd

from ya import stat


def test_calculate_cpm_groups_counts_by_minute(monkeypatch):
    monkeypatch.setattr(stat, "local_tz", ZoneInfo("UTC"))
    df = pd.DataFrame(
        [
            {
                "benchmark": "benchmark_alpha",
                "timestamp": 0,
                "execution_count": 2,
            },
            {
                "benchmark": "benchmark_alpha",
                "timestamp": 30,
                "execution_count": 3,
            },
            {
                "benchmark": "benchmark_alpha",
                "timestamp": 61,
                "execution_count": 4,
            },
        ]
    )

    result = stat.calculate_cpm(df)

    assert result["execution_count"].tolist() == ["5", "4"]
    assert result["execution_time"].astype(str).tolist() == [
        "1970-01-01 00:00:00+00:00",
        "1970-01-01 00:01:00+00:00",
    ]


def test_calculate_cpm_pivots_after_three_minutes(monkeypatch):
    monkeypatch.setattr(stat, "local_tz", ZoneInfo("UTC"))
    df = pd.DataFrame(
        [
            {"benchmark": "benchmark_alpha", "timestamp": 0, "execution_count": 1},
            {"benchmark": "benchmark_alpha", "timestamp": 61, "execution_count": 2},
            {"benchmark": "benchmark_alpha", "timestamp": 121, "execution_count": 3},
        ]
    )

    result = stat.calculate_cpm(df)

    assert result.loc["benchmark_alpha"].to_dict() == {
        "00:01:00": "1",
        "00:02:00": "2",
        "00:03:00": "3",
    }


def test_calculate_cps_trims_edges_and_handles_short_series():
    alpha_rows = [
        {
            "benchmark": "benchmark_alpha",
            "timestamp": idx,
            "execution_count": 1,
        }
        for idx in range(10)
    ]
    beta_rows = [
        {
            "benchmark": "benchmark_beta",
            "timestamp": 100,
            "execution_count": 1,
        }
    ]

    result = stat.calculate_cps(pd.DataFrame(alpha_rows + beta_rows))

    assert result.loc["benchmark_alpha", "CPS"] == "1.14"
    assert result.loc["benchmark_beta", "CPS"] == "0.00"


def test_calculate_kstat_and_return_stats():
    df = pd.DataFrame(
        [
            {
                "benchmark": "benchmark_alpha",
                "execution_time": 1.0,
                "execution_count": 1,
                "return_value": "ok",
            },
            {
                "benchmark": "benchmark_alpha",
                "execution_time": 2.0,
                "execution_count": 2,
                "return_value": "ok",
            },
            {
                "benchmark": "benchmark_alpha",
                "execution_time": 3.0,
                "execution_count": 3,
                "return_value": "fail",
            },
        ]
    )

    kstat = stat.calculate_kstat(df)
    rtn_stat = stat.calculate_rtn_stat(df)

    assert kstat.loc["benchmark_alpha"].to_dict() == {
        "Mean": 2.0,
        "k50": 2.0,
        "k90": 2.8,
        "k99": 2.98,
        "Count": "6",
        "Min": 1.0,
        "Max": 3.0,
        "Median": 2.0,
    }
    assert rtn_stat.to_dict("records") == [
        {
            "benchmark": "benchmark_alpha",
            "return_value": "fail",
            "count": 3,
            "percentage": 50.0,
        },
        {
            "benchmark": "benchmark_alpha",
            "return_value": "ok",
            "count": 3,
            "percentage": 50.0,
        },
    ]

"""
把压测执行数据 （函数名，timestamp，执行耗时毫秒数据）统计成以下内容：

表1. CPM执行次数统计
列为 （函数名，执行时间[分钟]，执行次数）
每行为每个函数，timestamp精确到分钟的的执行次数综合

表2. CPS执行次数统计
列为 （函数名1，函数名2, ...）
每行为各个函数的平均每秒执行次数，注意去掉头尾10%的timestamp数据，作为预热和冷却。
"""

import numpy as np
import pandas as pd
from tzlocal import get_localzone  # 需要安装：pip install tzlocal

local_tz = get_localzone()  # 获取系统本地时区


def calculate_cpm(df):
    """
    计算每个函数每分钟的执行次数
    """
    df = df.copy()
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], unit="s")
        .dt.tz_localize("UTC")  # 标记为UTC时间
        .dt.tz_convert(local_tz)  # 转换为本地时间
    )

    # 提取分钟级时间
    df["minute"] = df["timestamp"].dt.floor("min")

    # 按函数名和分钟分组统计
    cpm_stats = (
        df.groupby(["benchmark", "minute"]).size().reset_index(name="execution_count")
    )

    # 重命名列
    cpm_stats = cpm_stats.rename(
        columns={"minute": "execution_time", "execution_count": "execution_count"}
    )

    cpm_stats["execution_count"] = cpm_stats["execution_count"].apply(
        lambda x: f"{x:,}"
    )  # 千分位格式化

    return cpm_stats[["benchmark", "execution_time", "execution_count"]]


def calculate_cps(df):
    """
    计算每个函数的平均每秒执行次数，去掉头尾10%的数据
    """
    df = df.copy()
    # 按函数名分组
    functions = df["benchmark"].unique()

    # 准备结果DataFrame
    results = {}

    for func in functions:
        func_data = df[df["benchmark"] == func].copy()

        # 按时间戳排序
        func_data = func_data.sort_values("timestamp").reset_index(drop=True)

        # 去掉头尾10%的数据（预热和冷却阶段）
        n = len(func_data)
        trim_count = int(n * 0.1)

        if trim_count > 0:
            trimmed_data = func_data.iloc[trim_count:-trim_count]
        else:
            trimmed_data = func_data

        if len(trimmed_data) <= 1:
            # 如果数据太少，无法计算CPS
            results[func] = 0
            continue

        # 计算时间跨度（秒）
        time_span_seconds = (
            trimmed_data["timestamp"].max() - trimmed_data["timestamp"].min()
        ) / 1000.0

        if time_span_seconds > 0:
            # 计算CPS（执行次数/时间跨度）
            cps = len(trimmed_data) / time_span_seconds
        else:
            cps = len(trimmed_data)  # 如果时间跨度为0，返回执行次数

        results[func] = f"{cps:,.2f}"  # 千分位，保留2位小数

    # 转换为DataFrame（横排格式）
    cps_df = pd.DataFrame.from_dict(results, orient="index")

    return cps_df


# 计算按函数分组的统计
def calculate_kstat(df):
    """按函数分组计算统计"""
    df = df.copy()
    # 按函数名分组
    functions = df["benchmark"].unique()

    # 准备结果DataFrame
    results = {}

    for func in functions:
        func_data = df[df["benchmark"] == func].execution_time.copy()

        results[func] = {
            "Mean": round(func_data.mean(), 2),
            "k95": round(np.percentile(func_data, 95), 2),
            "k99": round(np.percentile(func_data, 99), 2),
            "Count": len(func_data),
            "Min": round(func_data.min(), 2),
            "Max": round(func_data.max(), 2),
            "Median": round(func_data.median(), 2),
        }

    return pd.DataFrame.from_dict(results, orient="index")

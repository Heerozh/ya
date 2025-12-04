"""
把压测执行数据 （函数名，timestamp，执行耗时毫秒数据）统计成以下内容：

表1. CPM执行次数统计
列为 （函数名，执行时间[分钟]，执行次数）
每行为每个函数，timestamp精确到分钟的的执行次数综合

表2. CPS执行次数统计
列为 （函数名1，函数名2, ...）
每行为各个函数的平均每秒执行次数，注意去掉头尾10%的timestamp数据，作为预热和冷却。
"""
import pandas as pd


def calculate_cpm(df):
    """
    计算每个函数每分钟的执行次数
    """
    # 确保timestamp是datetime类型（如果原始是毫秒时间戳）
    if pd.api.types.is_numeric_dtype(df['timestamp']):
        # 假设是毫秒时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    elif isinstance(df['timestamp'].iloc[0], (int, float)):
        # 如果是秒级时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # 提取分钟级时间
    df['minute'] = df['timestamp'].dt.floor('min')
    
    # 按函数名和分钟分组统计
    cpm_stats = df.groupby(['function_name', 'minute']).size().reset_index(name='execution_count')
    
    # 重命名列
    cpm_stats = cpm_stats.rename(columns={
        'minute': 'execution_time',
        'execution_count': 'execution_count'
    })
    
    return cpm_stats[['function_name', 'execution_time', 'execution_count']]

def calculate_cps(df):
    """
    计算每个函数的平均每秒执行次数，去掉头尾10%的数据
    """
    # 按函数名分组
    functions = df['function_name'].unique()
    
    # 准备结果DataFrame
    results = {}
    
    for func in functions:
        func_data = df[df['function_name'] == func].copy()
        
        # 按时间戳排序
        func_data = func_data.sort_values('timestamp').reset_index(drop=True)
        
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
        time_span_seconds = (trimmed_data['timestamp'].max() - trimmed_data['timestamp'].min()) / 1000.0
        
        if time_span_seconds > 0:
            # 计算CPS（执行次数/时间跨度）
            cps = len(trimmed_data) / time_span_seconds
        else:
            cps = len(trimmed_data)  # 如果时间跨度为0，返回执行次数
        
        results[func] = round(cps, 2)
    
    # 转换为DataFrame（横排格式）
    cps_df = pd.DataFrame([results])
    
    return cps_df
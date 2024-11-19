import itertools
import random
import time

# 設定參數
total_packets = 100  # 總封包數
proportions = [(x, 100 - x) for x in range(0, 101, 10)]  # 窮舉比例 (path1%, path2%)
packet_order_length = 5  # 規律長度
results = []  # 用於記錄所有測試結果

# 模擬 path1 和 path2 的傳輸行為
def simulate_path(path, packet_id):
    if path == "path1":
        success = random.random() > 0.1  # 10% 丟包
        delay = 0 if success else None  # 無延遲
    elif path == "path2":
        success = random.random() > 0.05  # 5% 機率延遲
        delay = 0.5 if success else None  # 500 ms 延遲
    return success, delay

# 計算性能指標
def evaluate_performance(sequence):
    success_count = 0
    total_delay = 0
    failed_packets = 0
    for i, path in enumerate(sequence):
        success, delay = simulate_path(path, i + 1)
        if success:
            success_count += 1
            total_delay += delay or 0
        else:
            failed_packets += 1
    average_delay = total_delay / (success_count or 1)
    success_rate = success_count / len(sequence)
    return average_delay, success_rate

# 窮舉所有比例與順序
for prop in proportions:
    path1_count = prop[0] * total_packets // 100
    path2_count = total_packets - path1_count

    # 生成所有可能的順序
    sequence_options = itertools.permutations(
        ["path1"] * path1_count + ["path2"] * path2_count, total_packets
    )
    unique_sequences = set(sequence_options)  # 去重，避免重複測試

    # 測試每個順序的性能
    for sequence in unique_sequences:
        avg_delay, success_rate = evaluate_performance(sequence)
        results.append({
            "proportion": prop,
            "sequence": sequence,
            "average_delay": avg_delay,
            "success_rate": success_rate,
        })

# 找到最佳結果
best_result = min(results, key=lambda x: (x["average_delay"], -x["success_rate"]))

# 輸出最佳結果
print("最佳結果:")
print(f"分配比例: {best_result['proportion']}")
print(f"分配順序: {best_result['sequence']}")
print(f"平均延遲: {best_result['average_delay']} 秒")
print(f"成功率: {best_result['success_rate'] * 100}%")

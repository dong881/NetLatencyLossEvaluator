# 設定分隔符號
delimiter = "|"

# 產生連接的字串
encoded_data = delimiter.join(f"Packet {i}" for i in range(1, 1001))

# 輸出編碼後的資料
print("Encoded Data:")
print(encoded_data)

# 解碼成原始的列表
decoded_packets = encoded_data.split(delimiter)

# 驗證解碼是否準確
print("\nDecoded Packets:")
for packet in decoded_packets[:10]:  # 只顯示前 10 筆以免輸出過多
    print(packet)

# 確認總數
print(f"\nTotal packets decoded: {len(decoded_packets)}")

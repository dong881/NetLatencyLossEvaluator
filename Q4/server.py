import socket
import time
import lzma

# 壓縮資料
def compress_with_lzma(data: str) -> bytes:
    return lzma.compress(data.encode("utf-8"))

# 生成包含分隔符號的完整數據
def generate_packet_data(start: int, end: int, delimiter: str = "|") -> str:
    return delimiter.join(f"Packet {i}" for i in range(start, end + 1))

# UDP 伺服器邏輯
def udp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_address = ('192.168.88.111', 5408)  # 設定目標地址

    print("Server starting to send packets")

    while True:
        user_input = input("Enter 'g' to send packets, 'q' to quit: ")
        if user_input == 'g':
            # 生成完整數據
            full_data = generate_packet_data(1, 100000)
            compressed_data = compress_with_lzma(full_data)  # 壓縮整段數據

            print(f"Compressed data size: {len(compressed_data)} bytes")

            # 記錄開始時間
            start_time = time.time()

            # 分批傳送壓縮數據
            batch_size = 1024  # 每次傳送的數據塊大小
            for i in range(0, len(compressed_data), batch_size):
                chunk = compressed_data[i:i + batch_size]
                server_socket.sendto(chunk, proxy_address)  # 傳送每個數據塊
                print(f"Sent chunk {i // batch_size + 1}: {len(chunk)} bytes")
                time.sleep(0.1)  # 避免過快發送造成網絡擁塞

            # 記錄結束時間
            end_time = time.time()

            # 計算總耗時和吞吐量
            total_time = end_time - start_time
            throughput = len(compressed_data) / total_time / 1024  # KB/s
            print(f"\nTotal time to send: {total_time:.2f} seconds")
            print(f"Throughput: {throughput:.2f} KB/s")

        elif user_input.lower() == 'q':
            print("Exiting server.")
            break

# 啟動伺服器
udp_server()

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
            batch_size = 1020  # 每次傳送的數據塊大小（去掉4字節序號）
            sequence_number = 0  # 封包序號
            for i in range(0, len(compressed_data), batch_size):
                chunk = compressed_data[i:i + batch_size]
                sequence_number_bytes = sequence_number.to_bytes(4, "big")  # 4字節序號

                # 若是最後一批數據，添加 END 標記
                if i + batch_size >= len(compressed_data):
                    chunk += b"END"

                packet = sequence_number_bytes + chunk  # 組合序號和數據塊
                server_socket.sendto(packet, proxy_address)  # 傳送封包
                print(f"Sent chunk {sequence_number}: {len(chunk)} bytes")
                sequence_number += 1
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

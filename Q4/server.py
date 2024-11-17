import socket
import threading
import time
import lzma

# 壓縮資料
def compress_with_lzma(data: str) -> bytes:
    return lzma.compress(data.encode("utf-8"))

# 生成包含分隔符號的完整數據
def generate_packet_data(start: int, end: int, delimiter: str = "|") -> str:
    return delimiter.join(f"Packet {i}" for i in range(start, end + 1))

# 接收 ACK 的執行緒
def ack_listener(ack_server_socket, ack_event, rtt_result):
    while True:
        ack_message, _ = ack_server_socket.recvfrom(1024)
        ack_data = ack_message.decode("utf-8").split(":")
        if ack_data[0] == "ACK":  # 確認收到 ACK
            rtt_result["ack_time"] = time.time()
            rtt_result["max_sequence"] = int(ack_data[1])  # 記錄最大序列號
            ack_event.set()  # 通知主線程已接收到 ACK

# UDP 伺服器邏輯
def udp_server():
    # 發送封包的套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_address = ('192.168.88.111', 5408)  # 目標地址

    # 接收 ACK 的套接字
    ack_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ack_server_socket.bind(('192.168.88.21', 5409))  # 綁定 ACK 監聽埠

    # 啟動執行緒接收 ACK
    ack_event = threading.Event()
    rtt_result = {"ack_time": None, "max_sequence": None}
    threading.Thread(target=ack_listener, args=(ack_server_socket, ack_event, rtt_result), daemon=True).start()

    print("Server starting to send packets and listening for ACKs")

    while True:
        user_input = input("Enter 'g' to send packets, 'q' to quit: ")
        if user_input == 'g':
            # 每次開始傳輸時重置事件和結果
            ack_event.clear()
            rtt_result["ack_time"] = None
            rtt_result["max_sequence"] = None

            # 生成完整數據
            full_data = generate_packet_data(1, 100000)
            print(f"Original data size: {len(full_data)} bytes")
            # 記錄開始時間
            start_time = time.time()
            compressed_data = compress_with_lzma(full_data)  # 壓縮整段數據
            print(f"Compressed data size: {len(compressed_data)} bytes")
            print(f"Compression ratio: {len(compressed_data) / len(full_data) * 100:.2f}%")

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
                # print(f"Sent chunk {sequence_number}: {len(chunk)} bytes")
                sequence_number += 1
                time.sleep(0.1)  # 避免過快發送造成網絡擁塞

            # 等待 ACK 確認
            print("Waiting for ACK from client...")
            ack_event.wait()  # 等待 ACK 事件觸發

            # 記錄結束時間
            end_time = rtt_result["ack_time"]

            # 如果沒有收到 ACK，處理錯誤
            if end_time is None:
                print("Error: No ACK received")
                continue

            # 計算總傳輸時間和吞吐量
            total_time = end_time - start_time
            throughput = len(compressed_data) / total_time / 1024  # KB/s

            print(f"\nTotal packets sent: {sequence_number}")
            print(f"Total time to send and acknowledge: {total_time:.2f} seconds")
            print(f"Throughput: {throughput:.2f} KB/s")

        elif user_input.lower() == 'q':
            print("Exiting server.")
            break

# 啟動伺服器
udp_server()

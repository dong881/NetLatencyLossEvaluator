# server main
import socket
import time
import lzma

# 壓縮資料
def compress_with_lzma(data: str) -> bytes:
    return lzma.compress(data.encode("utf-8"))

# 解壓縮資料（供參考）
def decompress_with_lzma(compressed_data: bytes) -> str:
    return lzma.decompress(compressed_data).decode("utf-8")

# 生成包含分隔符號的完整數據
def generate_packet_data(start: int, end: int, delimiter: str = "|") -> str:
    return delimiter.join(f"Packet {i}" for i in range(start, end + 1))

# UDP 伺服器邏輯
def udp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_address = ('192.168.88.111', 5408)  # 設定目標地址

    print("Server starting to send packets")

    while True:
        user_input = input("Enter '1' to send packets, 'q' to quit: ")
        if user_input == '1':
            # 生成完整數據
            full_data = generate_packet_data(1, 1000)
            compressed_data = compress_with_lzma(full_data)  # 壓縮整段數據
            print(f"Compressed data size: {len(compressed_data)} bytes")
            
            # 分批傳送壓縮數據
            batch_size = 1024  # 每次傳送的數據塊大小
            for i in range(0, len(compressed_data), batch_size):
                chunk = compressed_data[i:i + batch_size]
                print(chunk)
                server_socket.sendto(chunk, proxy_address)  # 傳送每個數據塊
                print(f"Sent chunk {i // batch_size + 1}: {len(chunk)} bytes")
                time.sleep(0.1)  # 避免過快發送造成網絡擁塞

        elif user_input.lower() == 'q':
            print("Exiting server.")
            break

# 啟動伺服器
udp_server()

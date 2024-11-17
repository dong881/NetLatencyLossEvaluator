import socket
import select
import lzma

# 解壓縮
def decompress_with_lzma(compressed_data: bytes) -> str:
    return lzma.decompress(compressed_data).decode("utf-8")

# 拆分數據
def split_packets(data: str, delimiter: str = "|") -> list:
    return data.split(delimiter)

# 客戶端主程式
def udp_client():
    # 建立套接字
    socket_5405 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_5407 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 綁定至指定埠口
    socket_5405.bind(('192.168.88.12', 5405))
    socket_5407.bind(('192.168.88.12', 5407))

    print("Client listening on ports 5405 and 5407")

    sockets = [socket_5405, socket_5407]  # 監控的套接字列表
    buffer = b""  # 暫存接收數據的緩衝區

    while True:
        # 使用 select 等待任一套接字接收數據
        readable, _, _ = select.select(sockets, [], [])

        for sock in readable:
            message, _ = sock.recvfrom(1024)  # 接收訊息
            buffer += message  # 將訊息累加到緩衝區

            # 假設較小的數據塊表示資料結束
            if len(message) < 1024:
                try:
                    # 解壓縮數據
                    decompressed_data = decompress_with_lzma(buffer)

                    # 拆分並顯示每個 Packet
                    packets = split_packets(decompressed_data)
                    print("\nPackets received:")
                    for packet in packets:
                        print(packet)

                    # 顯示總封包數
                    total_packets = len(packets)
                    print(f"\nTotal packets received: {total_packets}")

                except lzma.LZMAError:
                    print("Error: Failed to decompress data")
                finally:
                    buffer = b""  # 清空緩衝區準備接收下一批數據
udp_client()
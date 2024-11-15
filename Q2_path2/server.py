#路徑 rapi@raspberrypi:~/NetLatencyLossEvaluator/Q2_path2/server.py
import socket
import time

def udp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    proxy2_address = ('192.168.88.111', 5408)  # 設定 Proxy 2 的 IP 和埠
    print("Server starting to send packets via Proxy2")

    # 重複傳輸 100 次，每次傳輸 10 個封包
    for cycle in range(100):  # 外層迴圈，重複 100 次
        for i in range(1, 11):  # 內層迴圈，發送 10 個封包
            message = f"Packet {i} (Cycle {cycle + 1})"
            server_socket.sendto(message.encode(), proxy2_address)
            print(f"Sent: {message}")
            time.sleep(0.1)  # 每個封包間隔 100 ms

    server_socket.close()
    print("Server finished sending packets.")

udp_server()

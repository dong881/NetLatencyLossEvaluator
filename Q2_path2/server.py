#位置 rapi@raspberrypi:~/NetLatencyLossEvaluator/Q2_path2/server.py
import socket
import time
import random

def udp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    proxy2_address = ('192.168.88.111', 5454)  #已設定為實際server ip和port(Q2 path2)
    print("Server starting to send packets via Proxy2")

    # 將範圍從 10 改為 100，讓伺服器發送 100 個封包
    for i in range(1, 101):
        message = f"Packet {i}"

        # 模擬發送延遲（這裡不影響代理的 500 ms 延遲）
        if random.random() < 0.05:
            print(f"Delaying packet {i} by 500 ms before sending")
            time.sleep(0.5)  # 模擬延遲

        server_socket.sendto(message.encode(), proxy2_address)
        print(f"Sent: {message}")
        time.sleep(0.1)  # 保持 0.1 秒間隔

    server_socket.close()

udp_server()

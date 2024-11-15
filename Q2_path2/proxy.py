#路徑 rapi@raspberrypi:~/NetLatencyLossEvaluator/Q2_path2/proxy.py
import socket
import time
import random

def udp_proxy2():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_socket.bind(('0.0.0.0', 5408))  # 綁定到埠 5408，監聽所有 IP

    client_address = ('192.168.88.12', 5407)  # 客戶端的 IP 和埠
    print("Proxy2 ready to forward packets from server to client")

    # 處理 1000 個封包（10 個封包 * 100 次）
    for i in range(1000):
        data, _ = proxy_socket.recvfrom(1024)

        # 加入 5% 的機率延遲
        if random.random() < 0.05:
            print(f"Delaying packet {i+1} by 500 ms")
            time.sleep(0.5)  # 延遲 500 毫秒

        proxy_socket.sendto(data, client_address)
        print(f"Forwarded: {data.decode()}")

    proxy_socket.close()
    print("Proxy2 finished forwarding packets.")

udp_proxy2()

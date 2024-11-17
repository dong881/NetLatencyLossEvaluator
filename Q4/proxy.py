import socket
import threading
import time
import random

# 延遲處理函數
def delay_packet(data, client_address, proxy_socket):
    time.sleep(0.5)  # 模擬延遲
    proxy_socket.sendto(data, client_address)
    print(f"Forwarded after delay: {len(data)} bytes")  # 輸出資料長度

# 主代理函數
def udp_proxy2_delay():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_socket.bind(('192.168.88.111', 5408))  # 綁定代理的地址和端口

    # 設定接收端地址
    client_address = ('192.168.88.12', 5407)
    print("Proxy2 with 5% delay")

    while True:
        # 接收數據
        data, _ = proxy_socket.recvfrom(1024)

        # 隨機延遲或立即轉發
        if random.random() < 0.05:  # 5% 的機率觸發延遲
            threading.Thread(target=delay_packet, args=(data, client_address, proxy_socket)).start()
            print(f"Packet delayed: {len(data)} bytes")  # 輸出資料長度
        else:
            proxy_socket.sendto(data, client_address)  # 直接轉發數據
            print(f"Forwarded immediately: {len(data)} bytes")  # 輸出資料長度

# 啟動代理
udp_proxy2_delay()

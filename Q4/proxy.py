import socket
import threading
import time
import random

def delay_packet(data, client_address, proxy_socket):
    time.sleep(0.5)  # 模擬延遲
    proxy_socket.sendto(data, client_address)
    print(f"[Proxy2] Forwarded after delay: {len(data)} bytes")

def udp_proxy1_loss():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_socket.bind(('192.168.88.111', 5406))
    client_address = ('192.168.88.12', 5405)
    print("[Proxy1] Started - 10% packet loss")

    while True:
        try:
            data, _ = proxy_socket.recvfrom(1024)
            if random.random() > 0.1:  # 90% chance to forward
                proxy_socket.sendto(data, client_address)
                print(f"[Proxy1] Forwarded: {len(data)} bytes")
            else:
                print(f"[Proxy1] Packet lost: {len(data)} bytes")
        except Exception as e:
            print(f"[Proxy1] Error: {e}")

def udp_proxy2_delay():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_socket.bind(('192.168.88.111', 5408))
    client_address = ('192.168.88.12', 5407)
    print("[Proxy2] Started - 5% delay")

    while True:
        try:
            data, _ = proxy_socket.recvfrom(1024)
            if random.random() < 0.05:  # 5% chance of delay
                # 使用新的線程處理延遲封包,不影響主線程
                threading.Thread(
                    target=delay_packet, 
                    args=(data, client_address, proxy_socket),
                    daemon=True  # 設為daemon線程,這樣主程式結束時會自動結束
                ).start()
                print(f"[Proxy2] Packet delayed: {len(data)} bytes")
            else:
                proxy_socket.sendto(data, client_address)
                print(f"[Proxy2] Forwarded immediately: {len(data)} bytes")
        except Exception as e:
            print(f"[Proxy2] Error: {e}")

def main():
    # 創建兩個線程分別運行proxy1和proxy2
    proxy1_thread = threading.Thread(target=udp_proxy1_loss, daemon=True)
    proxy2_thread = threading.Thread(target=udp_proxy2_delay, daemon=True)
    
    # 啟動線程
    proxy1_thread.start()
    proxy2_thread.start()
    
    try:
        # 保持主程式運行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down proxies...")

if __name__ == "__main__":
    main()
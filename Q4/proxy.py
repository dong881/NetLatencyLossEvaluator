import socket
import threading
import time
import random

# 全局變數來追蹤統計數據
stats = {
    'last_packet_time': None,  # 最近一次收到封包的時間
    'start_time': None,        # 開始計算的時間
    'packet_count': 0,         # 總處理封包數量
    'data_total': 0,           # 總傳輸的資料大小
    'idle_logged': False,      # 是否已記錄 Idle 狀態
}


def reset_stats():
    """重置統計數據"""
    stats['start_time'] = None
    stats['last_packet_time'] = None
    stats['packet_count'] = 0
    stats['data_total'] = 0
    stats['idle_logged'] = False


def log_idle_state():
    """記錄並輸出 Idle 狀態的統計數據"""
    if stats['packet_count'] > 0 and stats['start_time'] is not None:
        elapsed_time = time.time() - stats['start_time']
        avg_throughput = stats['data_total'] / elapsed_time if elapsed_time > 0 else 0
        print(f"{'=' * 50}\n[Idle State] No packets received for 3 seconds\n"
              f"Time: {time.time()}, Packets: {stats['packet_count']}, "
              f"Total Data: {stats['data_total']} bytes, "
              f"Average Throughput: {avg_throughput:.2f} bytes/sec\n{'=' * 50}")
        stats['idle_logged'] = True  # 標記已記錄 Idle 狀態


def check_idle_state():
    """檢查是否進入 Idle 狀態"""
    while True:
        time.sleep(1)  # 每秒檢查一次
        if stats['last_packet_time'] is not None:
            time_since_last_packet = time.time() - stats['last_packet_time']
            if time_since_last_packet > 3 and not stats['idle_logged']:
                log_idle_state()


def udp_proxy1_loss():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_socket.bind(('192.168.88.111', 5406))
    client_address = ('192.168.88.12', 5405)
    print("[Proxy1] Started - 10% packet loss")

    while True:
        try:
            data, _ = proxy_socket.recvfrom(1024)
            current_time = time.time()

            # 更新統計數據
            if stats['start_time'] is None:
                stats['start_time'] = current_time
            stats['last_packet_time'] = current_time
            stats['packet_count'] += 1
            stats['data_total'] += len(data)
            stats['idle_logged'] = False  # 清除 Idle 狀態標記

            if random.random() > 0.1:  # 90% chance to forward
                proxy_socket.sendto(data, client_address)
                print(f"[Proxy1] Forwarded: {len(data)} bytes at {current_time}")
            else:
                print(f"[Proxy1] Packet lost: {len(data)} bytes")
        except Exception as e:
            print(f"[Proxy1] Error: {e}")


def delay_packet(data, client_address, proxy_socket):
    time.sleep(0.5)  # 模擬延遲
    proxy_socket.sendto(data, client_address)
    print(f"[Proxy2] Forwarded after delay: {len(data)} bytes at {time.time()}")


def udp_proxy2_delay():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_socket.bind(('192.168.88.111', 5408))
    client_address = ('192.168.88.12', 5407)
    print("[Proxy2] Started - 5% delay")

    while True:
        try:
            data, _ = proxy_socket.recvfrom(1024)
            current_time = time.time()

            # 更新統計數據
            if stats['start_time'] is None:
                stats['start_time'] = current_time
            stats['last_packet_time'] = current_time
            stats['packet_count'] += 1
            stats['data_total'] += len(data)
            stats['idle_logged'] = False  # 清除 Idle 狀態標記

            if random.random() < 0.05:  # 5% chance of delay
                threading.Thread(
                    target=delay_packet, 
                    args=(data, client_address, proxy_socket),
                    daemon=True  # 設為daemon線程,這樣主程式結束時會自動結束
                ).start()
                print(f"[Proxy2] Packet delayed: {len(data)} bytes")
            else:
                proxy_socket.sendto(data, client_address)
                print(f"[Proxy2] Forwarded immediately: {len(data)} bytes, at {current_time}")
        except Exception as e:
            print(f"[Proxy2] Error: {e}")


def main():
    # 創建兩個線程分別運行 proxy1 和 proxy2
    proxy1_thread = threading.Thread(target=udp_proxy1_loss, daemon=True)
    proxy2_thread = threading.Thread(target=udp_proxy2_delay, daemon=True)
    idle_check_thread = threading.Thread(target=check_idle_state, daemon=True)
    
    # 啟動線程
    proxy1_thread.start()
    proxy2_thread.start()
    idle_check_thread.start()
    
    try:
        # 保持主程式運行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down proxies...")


if __name__ == "__main__":
    main()

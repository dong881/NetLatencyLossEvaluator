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
    'loss_count': 0,           # 損失封包數
    'delay_count': 0           # 延遲封包數
}

def reset_stats():
    """重置統計數據"""
    stats['start_time'] = None
    stats['last_packet_time'] = None
    stats['packet_count'] = 0
    stats['data_total'] = 0
    stats['idle_logged'] = False
    stats['loss_count'] = 0
    stats['delay_count'] = 0


def log_idle_state():
    """記錄並輸出 Idle 狀態的統計數據"""
    if stats['packet_count'] > 0 and stats['start_time'] is not None:
        elapsed_time = stats['last_packet_time'] - stats['start_time']
        loss_rate = (stats['loss_count'] / stats['packet_count']) * 100 if stats['packet_count'] > 0 else 0
        delay_rate = (stats['delay_count'] / stats['packet_count']) * 100 if stats['packet_count'] > 0 else 0

        # 段落輸出 Idle State
        print("=" * 50)
        print(f"[Idle State] No packets received for 1 seconds")
        print(f"  Time: {elapsed_time:.2f} seconds")
        print(f"  Packets: {stats['packet_count']} | Total Data: {stats['data_total']} bytes")
        print(f"  Loss Count: {stats['loss_count']} | Loss Rate: {loss_rate:.2f}%")
        print(f"  Delay Count: {stats['delay_count']} | Delay Rate: {delay_rate:.2f}%")
        print("=" * 50)
        stats['idle_logged'] = True  # 標記已記錄 Idle 狀態
        reset_stats()  # 重置統計數據


def check_idle_state():
    """檢查是否進入 Idle 狀態"""
    while True:
        time.sleep(0.5)  # 每0.5秒檢查一次
        if stats['last_packet_time'] is not None:
            time_since_last_packet = time.time() - stats['last_packet_time']
            if time_since_last_packet > 1 and not stats['idle_logged']:
                log_idle_state()


def format_log(time, tag, message):
    """格式化輸出行"""
    return f"{time%100:.2f} [{tag}] {message}\n"


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
                print(format_log(current_time, "Proxy1", f"Forwarded: {len(data)} bytes"), end="")
            else:
                stats['loss_count'] += 1  # 增加丟包計數
                print(format_log(current_time, "Proxy1", f"Packet lost: {len(data)} bytes"), end="")
        except Exception as e:
            print(format_log(time.time(), "Proxy1", f"Error: {e}"), end="")


def delay_packet(data, client_address, proxy_socket):
    time.sleep(0.5)  # 模擬延遲
    proxy_socket.sendto(data, client_address)
    print(format_log(time.time(), "Proxy2", f"Forwarded after delay: {len(data)} bytes"), end="")


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
                stats['delay_count'] += 1  # 增加延遲計數
                threading.Thread(
                    target=delay_packet, 
                    args=(data, client_address, proxy_socket),
                    daemon=True  # 設為daemon線程,這樣主程式結束時會自動結束
                ).start()
                print(format_log(current_time, "Proxy2", f"Packet delayed: {len(data)} bytes"), end="")
            else:
                proxy_socket.sendto(data, client_address)
                print(format_log(current_time, "Proxy2", f"Forwarded: {len(data)} bytes"), end="")
        except Exception as e:
            print(format_log(time.time(), "Proxy2", f"Error: {e}"), end="")


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
        print("\n[System] Shutting down proxies...")


if __name__ == "__main__":
    main()

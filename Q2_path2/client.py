#位置 mini@miniPC:~/Q2_path2$ code client.py
import socket
import time

def udp_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind(('192.168.88.12', 5407))#已設定為實際client ip和port(Q2 path2)
    print("Client listening on port 5407")

    # 這邊將範圍從 10 改為 100，讓客戶端接收 100 個封包方便觀察
    for i in range(100):
        start_time = time.time()  # 開始接收時間
        message, _ = client_socket.recvfrom(1024)
        elapsed_time = time.time() - start_time  # 計算接收延遲

        if elapsed_time > 0.5:  # 如果接收延遲超過 500 ms
            print(f"Received (delayed): {message.decode()} with delay of {elapsed_time:.2f} seconds")
        else:
            print(f"Received: {message.decode()}")

    client_socket.close()

udp_client()

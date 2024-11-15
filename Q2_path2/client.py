#路徑 mini@miniPC:~/Q2_path2/client.py
import socket
import time

def udp_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind(('192.168.88.12', 5407))  #已設定為實際client ip和port(Q2 path2)
    print("Client listening on port 5407")

    # 接收10個封包*100次循環=1000個封包
    for i in range(1000):
        start_time = time.time()
        message, _ = client_socket.recvfrom(1024)
        elapsed_time = time.time() - start_time  # 計算接收延遲

        # 打印接收封包的延遲情況
        if elapsed_time > 0.5:  # 延遲超過 500 ms
            print(f"Received (delayed): {message.decode()} with delay of {elapsed_time:.2f} seconds")
        else:
            print(f"Received: {message.decode()}")

    client_socket.close()
    print("Client finished receiving packets.")

udp_client()

import socket
import random

def udp_proxy1_loss():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_socket.bind(('192.168.88.111', 5406))

    client_address = ('192.168.88.12', 5405)
    print("Proxy1 with 10% packet loss")

    while True:
        data, _ = proxy_socket.recvfrom(1024)
        if random.random() > 0.1:  # 90% chance to forward
            proxy_socket.sendto(data, client_address)
            print(f"Forwarded: {data.decode()}")
        else:
            print(f"Packet lost: {data.decode()}")

udp_proxy1_loss()

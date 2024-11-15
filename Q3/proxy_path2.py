import socket
import threading
import time
import random

def delay_packet(data, client_address, proxy_socket):
    time.sleep(0.5)
    proxy_socket.sendto(data, client_address)
    print(f"Forwarded after delay: {data.decode()}")

def udp_proxy2_delay():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_socket.bind(('192.168.88.111', 5408))

    client_address = ('192.168.88.12', 5407)
    print("Proxy2 with 5% delay")

    while True:
        data, _ = proxy_socket.recvfrom(1024)
        if random.random() < 0.05:  # 5% chance to delay
            threading.Thread(target=delay_packet, args=(data, client_address, proxy_socket)).start()
            print(f"Packet delayed: {data.decode()}")
        else:
            proxy_socket.sendto(data, client_address)
            print(f"Forwarded immediately: {data.decode()}")

udp_proxy2_delay()

#server main
import socket
import time

def udp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    proxy_address = ('192.168.88.111', 5406)
    print("Server starting to send packets")

    for _ in range(10):
        for i in range(1, 11):
            message = f"Packet {i}"
            server_socket.sendto(message.encode(), proxy_address)
            print(f"Sent: {message}")
            time.sleep(0.1)

    server_socket.close()

udp_server()

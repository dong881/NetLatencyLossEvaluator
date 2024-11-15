#server main
import socket
import time
import threading

def send_packer(server_socket, proxy_address):
    for i in range(1, 11):
        message = f"Packet {i}"
        server_socket.sendto(message.encode(), proxy_address)
        print(f"Sent: {message}")
        time.sleep(0.1)

    user_input = input()
    if user_input == '1':
        send_packer(server_socket, proxy_address)

def recieve_ack(server_socket):
    message, _ = server_socket.recvfrom(1024)
    print(f"Received ack: {message.decode()}")


def udp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('192.168.88.21', 5409))
    proxy_address = ('192.168.88.111', 5406)
    print("Server is listening...")

    user_input = input()
    if user_input == '1':
        threading.Thread(target=send_packer, args=(server_socket, proxy_address)).start()

    while True:
        recieve_ack(server_socket)
    

udp_server()

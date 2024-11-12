import socket

def udp_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind(('192.168.88.12', 5405))  # Client's address and port
    print("Client listening on port 5405")

    for i in range(10):
        message, _ = client_socket.recvfrom(1024)
        print(f"Client received: {message.decode()}")

    client_socket.close()

udp_client()

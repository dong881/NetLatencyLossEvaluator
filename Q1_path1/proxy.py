import socket

def udp_proxy():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_socket.bind(('192.168.88.111', 5406))  # Proxy's address and port
    client_address = ('192.168.88.12', 5405)  # Address of the client

    print("Proxy listening on port 5406")

    while True:
        message, _ = proxy_socket.recvfrom(1024)
        print(f"Proxy received: {message.decode()}")
        proxy_socket.sendto(message, client_address)  # Forward to client
        print(f"Proxy forwarded: {message.decode()} to client")

    
    proxy_socket.close()

udp_proxy()

import socket
from datetime import datetime

#Client main
def udp_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind(('192.168.88.12', 5405))  # Client's address and port
    print("Client listening on port 5405")

    last_time = None  # Record the time when the last message was received

    while True:
        message, _ = client_socket.recvfrom(1024)
        current_time = datetime.now()

        if last_time is None:
            time_difference = "N/A"  # first recieve
        else: # Calculate time difference 
            time_diff = (current_time - last_time).total_seconds() * 1000 
            time_difference = f"{time_diff:.2f} ms"

        print(f"Client received: {message.decode()} (Time since last: {time_difference})")

        ack_server_address = ('192.168.88.21', 5409)
        print("send ack to server")
        ack_message = message.decode()
        client_socket.sendto(ack_message.encode(), ack_server_address)

        last_time = current_time

udp_client()

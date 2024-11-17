import socket
import select
from datetime import datetime

# Client main
def udp_client():
    # Create sockets for both ports
    socket_5405 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_5407 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind each socket to its respective port
    socket_5405.bind(('192.168.88.12', 5405))
    socket_5407.bind(('192.168.88.12', 5407))

    print("Client listening on ports 5405 and 5407")

    sockets = [socket_5405, socket_5407]  # List of sockets to monitor
    last_time = None  # Record the time when the last message was received

    while True:
        # Use select to wait for data on any socket
        readable, _, _ = select.select(sockets, [], [])

        for sock in readable:
            message, _ = sock.recvfrom(1024)  # Receive message
            current_time = datetime.now()

            if last_time is None:
                time_difference = "N/A"  # First receive
            else:
                time_diff = (current_time - last_time).total_seconds() * 1000
                time_difference = f"{time_diff:.2f} ms"

            print(f"Client received on port {sock.getsockname()[1]}: {message.decode()} (Time since last: {time_difference})")

            # Send acknowledgment back to the server
            ack_server_address = ('192.168.88.21', 5409)
            print("Sending ACK to server")
            ack_message = message.decode()
            sock.sendto(ack_message.encode(), ack_server_address)

            last_time = current_time

udp_client()

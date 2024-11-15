import socket
from datetime import datetime

#Client main
def udp_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind(('192.168.88.12', 5407))  # Client's address and port
    print("Client listening on port 5405")

    last_time = None  # Record the time when the last message was received
    packet_count = 0  # Count of packets received
    total_bytes = 0   # Total bytes of the last 10 packets
    start_time = None # Start time for calculating throughput of 10 packets

    while True:
        message, _ = client_socket.recvfrom(1024)
        current_time = datetime.now()
        message_size = len(message)

        if last_time is None:
            time_difference = "N/A"  # first recieve
        else: # Calculate time difference
            time_diff = (current_time - last_time).total_seconds() * 1000
            time_difference = f"{time_diff:.2f} ms"

        print(f"Client received: {message.decode()} (Time since last: {time_difference})")

        # Update packet count and total bytes
        packet_count += 1
        total_bytes += message_size

        if packet_count == 1:
            start_time = current_time

        # Check if 10 packets have been received
        if packet_count == 10:
            # Calculate the throughput for the last 10 packets
            time_elapsed = (current_time - start_time).total_seconds()  # Time in seconds
            if time_elapsed > 0:
                throughput = (total_bytes / time_elapsed) * 8 / 1000  # Throughput in kbps
                print(f"Throughput for last 10 packets: {throughput:.2f} kbps, time elapsed: {time_elapsed:2f}")

            # Reset for the next 10 packets
            packet_count = 0
            total_bytes = 0
            start_time = current_time  # Reset start time for the next group

        last_time = current_time

udp_client()

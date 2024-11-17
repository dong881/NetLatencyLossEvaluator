import socket
import select
import lzma
from datetime import datetime

# 解壓縮
def decompress_with_lzma(compressed_data: bytes) -> str:
    return lzma.decompress(compressed_data).decode("utf-8")

# 拆分數據
def split_packets(data: str, delimiter: str = "|") -> list:
    return data.split(delimiter)

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
    buffer = b""  # Buffer to store received data

    while True:
        # Use select to wait for data on any socket
        readable, _, _ = select.select(sockets, [], [])

        for sock in readable:
            message, _ = sock.recvfrom(1024)  # Receive message
            buffer += message  # Append message to the buffer

            # Simulate checking if this is the last chunk (adjust logic based on real protocol)
            if len(message) < 1024:  # Assuming smaller chunk indicates end of data
                try:
                    # 解壓縮數據
                    decompressed_data = decompress_with_lzma(buffer)
                    
                    # 拆分並顯示每個 Packet
                    packets = split_packets(decompressed_data)
                    print("\nPackets received:")
                    for packet in packets:
                        print(packet)

                except lzma.LZMAError:
                    print("Error: Failed to decompress data")
                finally:
                    buffer = b""  # Clear buffer for the next set of data

                # Acknowledge receipt
                current_time = datetime.now()
                if last_time is None:
                    time_difference = "N/A"  # First receive
                else:
                    time_diff = (current_time - last_time).total_seconds() * 1000
                    time_difference = f"{time_diff:.2f} ms"

                print(f"\nClient received on port {sock.getsockname()[1]}: {len(buffer)} bytes (Time since last: {time_difference})")

                # Send acknowledgment back to the server
                ack_server_address = ('192.168.88.21', 5409)
                print("Sending ACK to server")
                ack_message = f"ACK for {len(packets)} packets"
                sock.sendto(ack_message.encode(), ack_server_address)

                last_time = current_time

udp_client()

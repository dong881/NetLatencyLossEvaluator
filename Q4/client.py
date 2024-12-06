import socket
import select
import lzma
from collections import defaultdict

class UDPClient:
    def __init__(self, ports=[5405, 5407], client_ip='192.168.88.12', server_ip='192.168.88.21', server_port=5409):
        # Initialize receive sockets
        self.receive_sockets = []
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((client_ip, port))
            self.receive_sockets.append(sock)
            
        # Initialize ACK socket
        self.ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = (server_ip, server_port)
        
        # Buffer for received packets
        self.buffer = {}
        self.received_sequences = set()
        self.total_expected_sequences = None  # Track total expected sequences
        
    def decompress_with_lzma(self, compressed_data: bytes) -> str:
        return lzma.decompress(compressed_data).decode("utf-8")
        
    def split_packets(self, data: str, delimiter: str = "|") -> list:
        return data.split(delimiter)
        
    def send_ack(self, sequence_number: int):
        """Send ACK for a specific sequence number"""
        ack_message = f"ACK:{sequence_number}".encode("utf-8")
        self.ack_socket.sendto(ack_message, self.server_address)
        
    def check_completion(self) -> bool:
        """Check if all expected packets have been received"""
        if self.total_expected_sequences is None:
            return False
        return self.total_expected_sequences == len(self.received_sequences)
        
    def process_complete_data(self):
        """Process and decompress complete data when all packets are received"""
        try:
            # Combine all packets in order
            sorted_data = b"".join(self.buffer[i] for i in range(self.total_expected_sequences))
            
            # Decompress data
            decompressed_data = self.decompress_with_lzma(sorted_data)
            packets = self.split_packets(decompressed_data)
            
            print(f"\nReceived and processed {len(packets)} packets successfully")
            
            # Clear buffers for next transmission
            self.buffer.clear()
            self.received_sequences.clear()
            self.total_expected_sequences = None  # Reset expected sequences
            
            return True
        except lzma.LZMAError as e:
            print(f"Error decompressing data: {e}")
            return False
            
    def start_receiving(self):
        """Main receive loop"""
        print("Client started listening for packets...")
        is_last = False
        while True:
            readable, _, _ = select.select(self.receive_sockets, [], [])
            
            for sock in readable:
                try:
                    message, _ = sock.recvfrom(65535)
                    
                    # Extract sequence number and data
                    sequence_number = int.from_bytes(message[:4], "big")
                    data = message[4:]
                    
                    # Check for END marker and total sequence count
                    if b"END" in data:
                        data, end_info = data.split(b"END", 1)
                        is_last = True
                        # Extract total sequence count from end_info
                        self.total_expected_sequences = sequence_number+1
                    
                    # Store data and send ACK
                    self.buffer[sequence_number] = data
                    self.received_sequences.add(sequence_number)
                    self.send_ack(sequence_number)
                    
                    # Process complete transmission if we have all packets
                    if is_last and self.check_completion():
                        self.process_complete_data()
                        is_last = False
                        
                except Exception as e:
                    print(f"Error processing packet: {e}")

# Usage
if __name__ == "__main__":
    client = UDPClient()
    client.start_receiving()
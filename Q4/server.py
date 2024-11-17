import socket
import threading
import time
import lzma
from collections import defaultdict

def compress_with_lzma(data: str) -> bytes:
    return lzma.compress(data.encode("utf-8"))

def generate_packet_data(start: int, end: int, delimiter: str = "|") -> str:
    return delimiter.join(f"Packet {i}" for i in range(start, end + 1))

class UDPServer:
    def __init__(self, server_ip='192.168.88.21', server_port=5409):
        self.server_address = (server_ip, server_port)
        
        # Define proxy paths
        self.proxy_ip = '192.168.88.111'
        self.proxy_path1 = (self.proxy_ip, 5406)  # Path 1 for last 5 packets
        self.proxy_path2 = (self.proxy_ip, 5408)  # Path 2 for regular packets
        
        # Socket for sending data
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Socket for receiving ACKs
        self.ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ack_socket.bind(self.server_address)
        
        # Thread-safe dictionary to track ACKs
        self.ack_received = defaultdict(bool)
        self.ack_lock = threading.Lock()
        
        # Timing control
        self.min_interval = 0.1  # 100ms minimum interval between sends
        self.last_send_time = 0
        
        # Sequence tracking
        self.total_sequences = 0
        self.last_five_start = 0
        
    def start_ack_listener(self):
        """Start a thread to listen for ACKs"""
        self.ack_thread = threading.Thread(target=self._ack_listener, daemon=True)
        self.ack_thread.start()
        
    def _ack_listener(self):
        """Listen for ACKs from client"""
        while True:
            try:
                ack_message, _ = self.ack_socket.recvfrom(1024)
                ack_data = ack_message.decode("utf-8").split(":")
                if ack_data[0] == "ACK":
                    sequence_number = int(ack_data[1])
                    with self.ack_lock:
                        self.ack_received[sequence_number] = True
            except Exception as e:
                print(f"Error in ACK listener: {e}")

    def wait_for_next_send(self):
        """Calculate and wait for the appropriate time before next send"""
        current_time = time.time()
        elapsed_since_last_send = current_time - self.last_send_time
        
        if elapsed_since_last_send < self.min_interval:
            sleep_time = self.min_interval - elapsed_since_last_send
            time.sleep(sleep_time)
    
    def get_proxy_address(self, sequence_number: int) -> tuple:
        """Determine which proxy path to use based on sequence number"""
        if sequence_number >= self.last_five_start:
            # print(f"Using Path 1 (port 5406) for packet {sequence_number}")
            return self.proxy_path2
        return self.proxy_path2
                
    def send_packet(self, sequence_number: int, data: bytes, is_last: bool = False):
        """Send a single packet with sequence number"""
        self.wait_for_next_send()
        
        sequence_number_bytes = sequence_number.to_bytes(4, "big")
        packet = sequence_number_bytes + data
        if is_last:
            packet += b"END"
            
        proxy_address = self.get_proxy_address(sequence_number)
        self.server_socket.sendto(packet, proxy_address)
        self.last_send_time = time.time()

    def get_unacked_sequences(self, timeout: float = 1.0) -> set:
        """Return set of sequence numbers that haven't been ACKed"""
        time.sleep(timeout)  # Wait for ACKs to arrive
        with self.ack_lock:
            return {seq for seq in range(self.total_sequences) 
                   if not self.ack_received[seq]}

    def handle_retransmissions(self, compressed_data: bytes, batch_size: int, 
                             max_retries: int = 3):
        """Handle retransmission of unacked packets"""
        retry_count = 0
        while retry_count < max_retries:
            unacked = self.get_unacked_sequences()
            if not unacked:
                return True
                
            print(f"Retransmitting {len(unacked)} packets, attempt {retry_count + 1}")
            for seq in sorted(unacked):
                chunk = compressed_data[seq * batch_size:(seq + 1) * batch_size]
                is_last = (seq == self.total_sequences - 1)
                self.send_packet(seq, chunk, is_last)
                
            retry_count += 1
            
        remaining_unacked = self.get_unacked_sequences()
        if remaining_unacked:
            print(f"Failed to transmit {len(remaining_unacked)} packets after {max_retries} attempts")
            return False
        return True

    def send_data(self, runTimes=5):
        """Main method to send data with reliability"""
        self.start_ack_listener()
        
        total_rtt = 0
        total_throughput = 0
        
        for run in range(runTimes):
            print(f"\nStarting transmission {run + 1}/{runTimes}")
            self.last_send_time = 0
            
            start_time = time.time()
            # Generate and compress data
            full_data = generate_packet_data(1, 100000)
            if run == 0:
                print(f"Original data size: {len(full_data)} bytes")
            
            compressed_data = compress_with_lzma(full_data)
            
            if run == 0:
                print(f"Compressed data size: {len(compressed_data)} bytes")
                print(f"Compression ratio: {len(compressed_data) / len(full_data) * 100:.2f}%")
                print("=====================================\n")
            
            # Reset ACK tracking
            with self.ack_lock:
                self.ack_received.clear()
            
            # Calculate sequences
            batch_size = 1020
            self.total_sequences = (len(compressed_data) + batch_size - 1) // batch_size
            self.last_five_start = max(0, self.total_sequences - 5)
            
            print(f"Total sequences: {self.total_sequences}")
            # print(f"Last 5 sequences start at: {self.last_five_start}")
            
            # First round: Send all packets without waiting for ACKs
            for seq in range(self.total_sequences):
                chunk = compressed_data[seq * batch_size:(seq + 1) * batch_size]
                is_last = (seq == self.total_sequences - 1)
                self.send_packet(seq, chunk, is_last)
            
            # Handle retransmissions
            if not self.handle_retransmissions(compressed_data, batch_size):
                print("Transmission failed")
                continue
            
            end_time = time.time()
            total_time = end_time - start_time
            throughput = len(compressed_data) / total_time / 1024  # KB/s
            
            # print(f"\nTransmission {run + 1} completed:")
            print(f"Total time: {total_time:.2f} seconds")
            print(f"Throughput: {throughput:.2f} KB/s")
            
            total_rtt += total_time
            total_throughput += throughput
        
        # Print final statistics
        print("\nFinal Statistics:")
        print(f"Average RTT in {runTimes} runs: {total_rtt/runTimes:.2f} seconds")
        print(f"Average Throughput in {runTimes} runs: {total_throughput/runTimes:.2f} KB/s")

if __name__ == "__main__":
    server = UDPServer()
    server.send_data(10)
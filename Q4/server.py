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
        
        # Control flags
        self.transmission_active = False
        self.current_batch_complete = threading.Event()
        
        # Statistics
        self.retransmission_count = 0
        
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
            print(f"Using Path 1 (port 5406) for packet {sequence_number}")
            return self.proxy_path1
        return self.proxy_path2
                
    def send_packet(self, sequence_number: int, data: bytes, is_last: bool = False):
        """Send a single packet with sequence number"""
        # Wait for appropriate send time
        self.wait_for_next_send()
        
        # Record start of processing time
        process_start = time.time()
        
        # Prepare packet
        sequence_number_bytes = sequence_number.to_bytes(4, "big")
        packet = sequence_number_bytes + data
        if is_last:
            packet += b"END"
            
        # Select appropriate proxy path
        proxy_address = self.get_proxy_address(sequence_number)
            
        # Send packet
        self.server_socket.sendto(packet, proxy_address)
        
        # Update last send time to include processing time
        self.last_send_time = time.time()
        
        # For debugging/monitoring
        processing_time = self.last_send_time - process_start
        if sequence_number % 100 == 0:  # Log every 100th packet
            print(f"Packet {sequence_number}: Processing time: {processing_time*1000:.2f}ms")
                
    def wait_for_ack(self, sequence_number: int, timeout: float = 1.0) -> bool:
        """Wait for ACK for a specific sequence number"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.ack_lock:
                if self.ack_received[sequence_number]:
                    return True
            time.sleep(0.01)
        return False
        
    def send_with_retry(self, sequence_number: int, data: bytes, is_last: bool = False, 
                       max_retries: int = 3, timeout: float = 1.0):
        """Send packet and retry if ACK not received"""
        retries = 0
        while retries < max_retries:
            self.send_packet(sequence_number, data, is_last)
            if self.wait_for_ack(sequence_number, timeout):
                return True
            print(f"Retransmitting packet {sequence_number}")
            self.retransmission_count += 1
            retries += 1
        return False

    def calculate_total_sequences(self, compressed_data: bytes, batch_size: int) -> int:
        """Calculate total number of sequences needed"""
        return (len(compressed_data) + batch_size - 1) // batch_size

    def send_data(self, runTimes=5):
        """Main method to send data with reliability"""
        self.start_ack_listener()
        
        total_rtt = 0
        total_throughput = 0
        
        for run in range(runTimes):
            print(f"\nStarting transmission {run + 1}/{runTimes}")
            
            # Reset timing for new transmission
            self.last_send_time = 0
            
            # Generate and compress data
            full_data = generate_packet_data(1, 100000)
            if run == 0:
                print(f"Original data size: {len(full_data)} bytes")
            
            start_time = time.time()
            compressed_data = compress_with_lzma(full_data)
            
            if run == 0:
                print(f"Compressed data size: {len(compressed_data)} bytes")
                print(f"Compression ratio: {len(compressed_data) / len(full_data) * 100:.2f}%")
                print("=====================================\n")
            
            # Reset ACK tracking for new transmission
            with self.ack_lock:
                self.ack_received.clear()
            
            # Calculate total sequences and set last five start
            batch_size = 1020
            self.total_sequences = self.calculate_total_sequences(compressed_data, batch_size)
            self.last_five_start = max(0, self.total_sequences - 5)
            
            print(f"Total sequences: {self.total_sequences}")
            print(f"Last 5 sequences start at: {self.last_five_start}")
            
            # Send data in chunks
            sequence_number = 0
            self.retransmission_count = 0
            
            for i in range(0, len(compressed_data), batch_size):
                chunk = compressed_data[i:i + batch_size]
                is_last = (i + batch_size >= len(compressed_data))
                
                if not self.send_with_retry(sequence_number, chunk, is_last):
                    print(f"Failed to send packet {sequence_number} after max retries")
                
                sequence_number += 1
            
            end_time = time.time()
            total_time = end_time - start_time
            throughput = len(compressed_data) / total_time / 1024  # KB/s
            
            print(f"Transmission {run + 1} completed:")
            print(f"Total time: {total_time:.2f} seconds")
            print(f"Throughput: {throughput:.2f} KB/s")
            print(f"Retransmissions: {self.retransmission_count}")
            
            total_rtt += total_time
            total_throughput += throughput
        
        # Print final statistics
        print("\nFinal Statistics:")
        print(f"Average RTT in {runTimes} runs: {total_rtt/runTimes:.2f} seconds")
        print(f"Average Throughput in {runTimes} runs: {total_throughput/runTimes:.2f} KB/s")

# Usage
if __name__ == "__main__":
    server = UDPServer()
    server.send_data(10)
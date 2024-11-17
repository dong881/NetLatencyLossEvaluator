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
        self.proxy_ip = '192.168.88.111'
        self.proxy_path1 = (self.proxy_ip, 5406)
        self.proxy_path2 = (self.proxy_ip, 5408)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ack_socket.bind(self.server_address)
        self.ack_received = defaultdict(bool)
        self.ack_lock = threading.Lock()
        self.min_interval = 0.1
        self.last_send_time = 0
        self.total_sequences = 0
        self.last_five_start = 0
        self.total_retransmissions = 0
        self.total_packets_sent = 0

    def start_ack_listener(self):
        self.ack_thread = threading.Thread(target=self._ack_listener, daemon=True)
        self.ack_thread.start()

    def _ack_listener(self):
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
        current_time = time.time()
        elapsed_since_last_send = current_time - self.last_send_time
        if elapsed_since_last_send < self.min_interval:
            time.sleep(self.min_interval - elapsed_since_last_send)

    def get_proxy_address(self, sequence_number: int) -> tuple:
        if sequence_number >= self.last_five_start:
            return self.proxy_path1
        return self.proxy_path2

    def send_packet(self, sequence_number: int, data: bytes, is_last: bool = False):
        self.wait_for_next_send()
        sequence_number_bytes = sequence_number.to_bytes(4, "big")
        packet = sequence_number_bytes + data
        if is_last:
            packet += b"END"
        proxy_address = self.get_proxy_address(sequence_number)
        self.server_socket.sendto(packet, proxy_address)
        self.total_packets_sent += 1
        self.last_send_time = time.time()

    def get_unacked_sequences(self) -> set:
        with self.ack_lock:
            return {seq for seq in range(self.total_sequences) if not self.ack_received[seq]}

    def handle_retransmissions(self, compressed_data: bytes, batch_size: int, max_retries: int = 5, timeout: float = 0.05):
        retry_count = 0
        while retry_count < max_retries:
            unacked = self.get_unacked_sequences()
            if not unacked:
                return True
            for seq in sorted(unacked):
                print(f"Retransmitting packet {seq}, attempt {retry_count + 1}")
                chunk = compressed_data[seq * batch_size:(seq + 1) * batch_size]
                is_last = (seq == self.total_sequences - 1)
                self.send_packet(seq, chunk, is_last)
                self.total_retransmissions += 1
            time.sleep(timeout)
            retry_count += 1
        remaining_unacked = self.get_unacked_sequences()
        if remaining_unacked:
            print(f"Failed to transmit {len(remaining_unacked)} packets after {max_retries} attempts")
            return False
        return True

    def send_data(self, runTimes=5):
        self.start_ack_listener()
        total_rtt = 0
        total_throughput = 0
        runs_completed = 0
        total_packet_loss_rate = 0
        total_packet_loss = 0

        for run in range(runTimes):
            self.last_send_time = 0
            self.total_packets_sent = 0
            self.total_retransmissions = 0
            start_time = time.time()
            full_data = generate_packet_data(1, 100000)
            if run == 0:
                print(f"Original data size: {len(full_data)} bytes")
            compressed_data = compress_with_lzma(full_data)
            with self.ack_lock:
                self.ack_received.clear()
            batch_size = 1020
            self.total_sequences = (len(compressed_data) + batch_size - 1) // batch_size
            self.last_five_start = max(0, self.total_sequences - 5)
            if run == 0:
                print(f"Compressed data size: {len(compressed_data)} bytes")
                print(f"Compression ratio: {len(compressed_data) / len(full_data) * 100:.2f}%")
                print(f"Total sequences: {self.total_sequences}")
                print("=====================================")
            print(f"\nStarting transmission {run + 1}/{runTimes}")
            for seq in range(self.total_sequences):
                chunk = compressed_data[seq * batch_size:(seq + 1) * batch_size]
                is_last = (seq == self.total_sequences - 1)
                self.send_packet(seq, chunk, is_last)
            time.sleep(0.05)
            if not self.handle_retransmissions(compressed_data, batch_size):
                print("Transmission failed")
                continue
            end_time = time.time()
            total_time = end_time - start_time
            throughput = len(compressed_data) / total_time / 1024
            packet_loss = self.total_retransmissions
            total_packet_loss += packet_loss
            packet_loss_rate = self.total_retransmissions / self.total_sequences
            total_packet_loss_rate += packet_loss_rate
            print(f"Total time: {total_time:.2f} seconds")
            total_rtt += total_time
            total_throughput += throughput
            runs_completed += 1

        print("\nFinal Statistics:")
        print(f"Average RTT in {runs_completed} runs: {total_rtt / runs_completed:.2f} seconds")
        print(f"Average Throughput in {runs_completed} runs: {total_throughput / runs_completed:.2f} KB/s")
        print(f"Average Packet Loss Rate: {(total_packet_loss_rate / runs_completed) * 100:.2f}% packets/sequence")
        print(f"Total Packet Loss: {total_packet_loss} packets")

if __name__ == "__main__":
    server = UDPServer()
    server.send_data(10)
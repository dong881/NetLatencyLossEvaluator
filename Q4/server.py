import socket
import threading
import time
import lzma
from collections import defaultdict
import queue
import json
from datetime import datetime
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os

def compress_with_lzma(data: str) -> bytes:
    return lzma.compress(data.encode("utf-8"))

def generate_packet_data(start: int, end: int, delimiter: str = "|") -> str:
    return delimiter.join(f"Packet {i}" for i in range(start, end + 1))
     
class UDPServerMonitor:
    def __init__(self):
        self.stats_queue = queue.Queue()
        self.current_session_id = None
        self.reset_stats()
        self._start_stats_processor()
        self.current_stats = {
            'start_time': None,
            'packets': [],
            'throughput_history': [],
            'total_data_sent': 0,
            'compression_stats': None,
            'active_transmission': False,
            'last_update': None,
            'error_count': 0,
            'path_stats': {
                'path1': {'packets': 0, 'success': 0},
                'path2': {'packets': 0, 'success': 0}
            },
            'performance_metrics': {
                'avg_rtt': 0,
                'packet_loss_rate': 0,
                'throughput': 0,
                'compression_ratio': 0
            },
            'historical_data': [],
            'transmission_status': 'idle'
        }

    # 在 UDPServerMonitor 類中增加一個方法來重置統計數據
    def reset_stats(self):
        self.current_stats = {
            'start_time': None,
            'packets': [],
            'throughput_history': [],
            'total_data_sent': 0,
            'compression_stats': None,
            'active_transmission': False,
            'last_update': None,
            'error_count': 0,
            'path_stats': {
                'path1': {'packets': 0, 'success': 0},
                'path2': {'packets': 0, 'success': 0}
            },
            'performance_metrics': {
                'avg_rtt': 0,
                'packet_loss_rate': 0,
                'throughput': 0,
                'compression_ratio': 0
            },
            'transmission_status': 'idle'
        }

    def _start_stats_processor(self):
        def process_stats():
            while True:
                try:
                    stat = self.stats_queue.get()
                    self._update_stats(stat)
                except Exception as e:
                    print(f"Error processing stats: {e}")
                    self.current_stats['error_count'] += 1
        
        thread = threading.Thread(target=process_stats, daemon=True)
        thread.start()

    def _update_stats(self, stat):
        stat_type = stat.get('type')
        current_time = datetime.now()
        
        if stat_type == 'packet_sent':
            self.current_stats['packets'].append({
                'id': stat['sequence'],
                'timestamp': stat['timestamp'],
                'size': stat['size'],
                'path': stat['path'],
                'status': 'sent'
            })
            path = 'path1' if stat['path'] == 'path1' else 'path2'
            self.current_stats['path_stats'][path]['packets'] += 1
            self.current_stats['total_data_sent'] += stat['size']
            
        elif stat_type == 'packet_acked':
            for packet in self.current_stats['packets']:
                if packet['id'] == stat['sequence']:
                    packet['status'] = 'acked'
                    packet['ack_time'] = current_time.isoformat()
                    path = packet['path']
                    self.current_stats['path_stats'][path]['success'] += 1
                    break
                    
        elif stat_type == 'transmission_start':
            self.current_stats['start_time'] = stat['timestamp']
            self.current_stats['transmission_status'] = 'active'
            
        elif stat_type == 'transmission_end':
            if self.current_stats['start_time']:
                duration = (current_time - datetime.fromisoformat(self.current_stats['start_time'])).total_seconds()
                throughput = self.current_stats['total_data_sent'] / duration if duration > 0 else 0
                self.current_stats['throughput_history'].append({
                    'timestamp': current_time.isoformat(),
                    'value': throughput
                })
                
        elif stat_type == 'compression_stats':
            self.current_stats['compression_stats'] = {
                'original_size': stat['original_size'],
                'compressed_size': stat['compressed_size'],
                'ratio': stat['ratio']
            }
            
        self.current_stats['last_update'] = current_time.isoformat()
        
        # Update performance metrics
        if self.current_stats['packets']:
            acked_packets = [p for p in self.current_stats['packets'] if p['status'] == 'acked']
            total_packets = len(self.current_stats['packets'])
            self.current_stats['performance_metrics'].update({
                'packet_loss_rate': 1 - (len(acked_packets) / total_packets) if total_packets > 0 else 0,
                'throughput': self.current_stats['total_data_sent'] / (time.time() - time.mktime(datetime.fromisoformat(self.current_stats['start_time']).timetuple())) if self.current_stats['start_time'] else 0
            })

    def get_current_stats(self):
        return json.dumps(self.current_stats)

    def record_event(self, event_type, **kwargs):
        self.stats_queue.put({'type': event_type, **kwargs})

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
        self.monitor = UDPServerMonitor()
        self.running = True
        self.current_transmission = None
        self._start_web_server()
        self.current_session_id = None
        
    def reset_stats(self):
        self.total_sequences = 0
        self.last_five_start = 0
        self.total_retransmissions = 0
        self.total_packets_sent = 0
        self.last_send_time = 0
        self.running = True
        self.ack_received.clear()
        self.monitor.reset_stats()
        
    def start_new_session(self):
        self.reset_stats()
        return self.current_session_id

    def end_current_session(self):
        if self.current_session_id:
            self.running = False  # Force stop the send_data loop
            stats = {
                'total_packets': self.total_packets_sent,
                'success_rate': len([p for p in self.monitor.current_stats['packets'] if p['status'] == 'acked']) / self.total_packets_sent if self.total_packets_sent > 0 else 0,
                'avg_throughput': self.monitor.current_stats['performance_metrics']['throughput']
            }
            self.current_session_id = None

    def _start_web_server(self):
        app = Flask(__name__, static_folder='static')
        CORS(app)

        @app.route('/')
        def index():
            return send_from_directory('static', 'index.html')

        @app.route('/api/stats')
        def get_stats():
            return self.monitor.get_current_stats()
        
        @app.route('/api/transmission/toggle', methods=['POST'])
        def toggle_transmission():
            if not self.current_transmission or not self.current_transmission.is_alive():
                self.start_new_session()
                self.current_transmission = threading.Thread(
                    target=self.send_data,
                    args=(1,),
                    daemon=True
                )
                self.current_transmission.start()
                return jsonify({'status': 'started', 'session_id': self.current_session_id})
            else:
                self.running = False
                self.end_current_session()
                return jsonify({'status': 'stopping'})

        def run_flask():
            app.run(host='0.0.0.0', port=8080, threaded=True)

        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

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
                        self.monitor.record_event('packet_acked',
                            sequence=sequence_number,
                            timestamp=datetime.now().isoformat()
                        )
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
        self.monitor.record_event('packet_sent', 
            sequence=sequence_number,
            timestamp=datetime.now().isoformat(),
            size=len(data),
            path='path1' if sequence_number >= self.last_five_start else 'path2'
        )
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
            if self.running == False: # Stop the transmission
                break
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
                self.monitor.record_event('transmission_start', 
                    timestamp=datetime.now().isoformat()
                )
                self.send_packet(seq, chunk, is_last)
                self.monitor.record_event('transmission_end',
                    timestamp=datetime.now().isoformat()
                )
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
    # Create static folder if it doesn't exist
    if not os.path.exists('static'):
        os.makedirs('static')
        
    server = UDPServer()
    while True:
        time.sleep(1)  # Keep the main thread alive
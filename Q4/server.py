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
        self.current_stats = {
            'compression': {
                'original_size': 0,
                'compressed_size': 0,
                'ratio': 0
            },
            'transmission': {
                'current_run': 0,
                'total_runs': 0,
                'status': 'idle'  # idle, running, compelted
            },
            'performance': {
                'total_rtt': 0,
                'average_rtt': 0,
                'total_throughput': 0,
                'average_throughput': 0,
                'total_packet_loss_rate': 0,
                'average_packet_loss_rate': 0
            },
            'paths': {
                'path1': {'packets': 0, 'success': 0},
                'path2': {'packets': 0, 'success': 0}
            },
            'packets': [], # List of {sequence, timestamp, path}
            
        }
        self._start_stats_processor()

    def reset_stats(self):
        self.__init__()

    def _start_stats_processor(self):
        def process_stats():
            while True:
                try:
                    stat = self.stats_queue.get()
                    self._update_stats(stat)
                except Exception as e:
                    print(f"Error processing stats: {e}")

        thread = threading.Thread(target=process_stats, daemon=True)
        thread.start()

    def _update_stats(self, stat):
        stat_type = stat.get('type')

        if stat_type == 'compression_info':
            self.current_stats['compression'].update({
                'original_size': stat['original_size'],
                'compressed_size': stat['compressed_size'],
                'ratio': stat['ratio']
            })

        elif stat_type == 'transmission_status':
            self.current_stats['transmission'].update({
                'current_run': stat['current_run'],
                'total_runs': stat['total_runs'],
                'status': stat['status']
            })

        elif stat_type == 'performance_update':
            self.current_stats['performance'].update({
                'total_rtt': stat['total_rtt'],
                'average_rtt': stat['average_rtt'],
                'total_throughput': stat['total_throughput'],
                'average_throughput': stat['average_throughput'],
                'total_packet_loss_rate': stat['total_packet_loss_rate'],
                'average_packet_loss_rate': stat['average_packet_loss_rate']
            })

        elif stat_type == 'packet_sent':
            self.current_stats['packets'].append({
                'sequence': stat['sequence'],
                'timestamp': stat['timestamp'],
                'path': stat['path'],
                'size': stat['size'],
                'type': 'sent',
                'status': 'sent'
            })
            self.current_stats['paths'][stat['path']]['packets'] += 1

        elif stat_type == 'packet_acked':
            self.current_stats['packets'].append({
                'sequence': stat['sequence'],
                'timestamp': stat['timestamp'],
                'type': 'acked',
                'status': 'sent'
            })
            for packet in self.current_stats['packets']:
                if packet['status'] == 'sent' and packet['sequence'] == stat['sequence']:
                    packet['status'] = 'acked'
                    self.current_stats['paths'][packet['path']]['success'] += 1
                    break

    def record_event(self, event_type, **kwargs):
        self.stats_queue.put({'type': event_type, **kwargs})

    def get_current_stats(self):
        return json.dumps(self.current_stats)

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
        self.monitor = UDPServerMonitor()
        self.running = True
        self.current_transmission = None
        self._start_web_server()
        self.current_session_id = None
        self.log_file = 'static/transmission_history.json'
        self.ensure_log_file()
        
    def ensure_log_file(self):
        if not os.path.exists('static'):
            os.makedirs('static')
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump([], f)

    def log_session(self, stats):
        try:
            with open(self.log_file, 'r') as f:
                history = json.load(f)
                
            session_log = {
                'timestamp': time.time(),
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_rtt': stats['total_rtt'],
                'total_packets': self.total_sequences,
                'throughput': stats['total_throughput'],
                'packet_loss_rate': stats['total_packet_loss_rate']
            }
            
            history.append(session_log)
            
            with open(self.log_file, 'w') as f:
                json.dump(history, f)
                
            # 更新統計資料
            self.update_historical_averages()
                
        except Exception as e:
            print(f"Error logging session: {e}")

    def clear_history(self):
        try:
            with open(self.log_file, 'w') as f:
                json.dump([], f)
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False

    def update_historical_averages(self):
        try:
            with open(self.log_file, 'r') as f:
                history = json.load(f)
                
            if not history:
                return
                
            total_rtt = sum(session['total_rtt'] for session in history)
            total_throughput = sum(session['throughput'] for session in history)
            total_loss_rate = sum(session['packet_loss_rate'] for session in history)
            count = len(history)
            
            self.monitor.record_event('historical_averages', 
                average_rtt=total_rtt/count,
                average_throughput=total_throughput/count,
                average_packet_loss_rate=total_loss_rate/count
            )
            
        except Exception as e:
            print(f"Error updating historical averages: {e}")
        
    def reset_stats(self):
        self.total_sequences = 0
        self.last_five_start = 0
        self.total_retransmissions = 0
        self.last_send_time = 0
        self.running = True
        self.ack_received.clear()
        self.monitor.reset_stats()
        
    def start_new_session(self):
        self.reset_stats()
        return self.current_session_id

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
                self.monitor.record_event('transmission_status',
                    current_run=0,
                    total_runs=0,
                    status='running'
                )
                self.start_new_session()
                self.current_transmission = threading.Thread(
                    target=self.send_data,
                    args=(1,),
                    daemon=True
                )
                self.current_transmission.start()
                return jsonify({'status': 'running', 'session_id': self.current_session_id})
            else:
                self.monitor.record_event('transmission_status',
                    current_run=0,
                    total_runs=0,
                    status='idle'
                )
                self.current_transmission.stop()
                self.reset_stats()
                return jsonify({'status': 'idle'})

        @app.route('/api/history', methods=['GET'])
        def get_history():
            try:
                with open(self.log_file, 'r') as f:
                    return jsonify(json.load(f))
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @app.route('/api/history/clear', methods=['POST']) 
        def clear_history():
            if self.clear_history():
                return jsonify({'status': 'success'})
            return jsonify({'status': 'error'}), 500

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
                            timestamp=time.time(),
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
        proxy_address = self.get_proxy_address(sequence_number)
        self.monitor.record_event('packet_sent', 
            sequence=sequence_number,
            timestamp=time.time(),
            size=len(data),
            path='path1' if proxy_address == self.proxy_path1 else 'path2'
        )
        self.server_socket.sendto(packet, proxy_address)
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
                self.monitor.record_event('compression_info',
                    original_size=len(full_data),
                    compressed_size=len(compressed_data), 
                    ratio=len(compressed_data)/len(full_data)* 100
                )
            print(f"\nStarting transmission {run + 1}/{runTimes}")
            self.monitor.record_event('transmission_status',
                current_run=run+1,
                total_runs=runTimes,
                status='running'
            )
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
            self.monitor.record_event('performance_update',
                total_rtt=total_rtt,
                average_rtt=total_rtt/runs_completed,
                total_throughput=total_throughput,
                average_throughput=total_throughput/runs_completed,
                total_packet_loss_rate=total_packet_loss_rate,
                average_packet_loss_rate=total_packet_loss_rate/runs_completed
            )
            self.monitor.record_event('transmission_status',
                current_run=run,
                total_runs=runTimes,
                status='compelted'
            )
            # 在傳輸結束時記錄session
            self.log_session({
                'total_rtt': total_rtt,
                'total_throughput': total_throughput,
                'total_packet_loss_rate': total_packet_loss_rate
            })

        print("\nFinal Statistics:")
        print(f"Average RTT in {runs_completed} runs: {total_rtt / runs_completed:.2f} seconds")
        print(f"Average Throughput in {runs_completed} runs: {total_throughput / runs_completed:.2f} KB/s")
        print(f"Average Packet Loss Rate: {(total_packet_loss_rate / runs_completed) * 100:.2f}% packets/sequence")
        print(f"Total Packet Loss: {total_packet_loss} packets")
        self.monitor.record_event('transmission_status',
            current_run=runTimes,
            total_runs=runTimes,
            status='idle'
        )

if __name__ == "__main__":
    # Create static folder if it doesn't exist
    if not os.path.exists('static'):
        os.makedirs('static')
        
    server = UDPServer()
    while True:
        time.sleep(1)  # Keep the main thread alive
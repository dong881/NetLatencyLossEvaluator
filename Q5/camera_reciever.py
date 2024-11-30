from flask import Flask, Response, render_template, jsonify
import socket
import struct
import time
import threading
from collections import defaultdict, deque

app = Flask(__name__)
current_frame = None
current_text = "等待文字數據..."
frame_lock = threading.Lock()
text_lock = threading.Lock()

# 資料類型標識
IMAGE_TYPE = 0b00
TEXT_TYPE = 0b01

class NetworkMetrics:
    def __init__(self, window_size=1.0):
        self.window_size = window_size
        self.frames = deque(maxlen=100)  # (timestamp, size)
        self.frame_timestamps = deque(maxlen=100)  # 接收時間
        self.total_bytes = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        
        # 延遲計算
        self.latencies = deque(maxlen=30)  # 儲存最近30個延遲樣本
        
        # 吞吐量計算
        self.throughput_window = deque(maxlen=30)  # (timestamp, bytes)
        self.last_throughput = 0
        self.last_update = time.time()

    def update(self, frame_size, send_timestamp):
        with self.lock:
            current_time = time.time()
            
            # 更新FPS計算
            self.frame_timestamps.append(current_time)
            
            # 更新吞吐量計算
            self.throughput_window.append((current_time, frame_size))
            
            # 清理舊數據
            while self.throughput_window and \
                  current_time - self.throughput_window[0][0] > self.window_size:
                self.throughput_window.popleft()
            
            # 計算延遲
            if send_timestamp > 0:
                latency = (current_time - send_timestamp) * 1000  # 轉換為毫秒
                if 0 <= latency <= 1000:  # 合理的延遲範圍
                    self.latencies.append(latency)

    def get_metrics(self):
        with self.lock:
            current_time = time.time()
            
            # 計算FPS
            recent_frames = [t for t in self.frame_timestamps 
                           if current_time - t <= self.window_size]
            fps = len(recent_frames)
            
            # 計算吞吐量 (kbps)
            if self.throughput_window:
                window_duration = current_time - self.throughput_window[0][0]
                if window_duration > 0:
                    total_bytes = sum(size for _, size in self.throughput_window)
                    throughput = (total_bytes * 8) / (window_duration * 1024)
                else:
                    throughput = self.last_throughput
            else:
                throughput = 0
            
            # 計算平均延遲
            latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
            
            self.last_throughput = throughput
            
            return {
                "fps": round(fps, 2),
                "throughput": round(throughput, 2),
                "latency": round(latency, 2)
            }

# 初始化網路指標監控器
metrics = NetworkMetrics()

class FrameAssembler:
    def __init__(self):
        self.buffer = defaultdict(dict)
        self.frame_timeouts = {}
        self.timeout = 1.0

    def cleanup_old_frames(self):
        current_time = time.time()
        expired_frames = [
            frame_id for frame_id, timestamp in self.frame_timeouts.items()
            if current_time - timestamp > self.timeout
        ]
        for frame_id in expired_frames:
            del self.buffer[frame_id]
            del self.frame_timeouts[frame_id]

    def add_chunk(self, frame_id, chunk_id, total_chunks, data_len, data):
        current_time = time.time()
        self.frame_timeouts[frame_id] = current_time
        self.cleanup_old_frames()

        if len(data) != data_len:
            return None

        self.buffer[frame_id][chunk_id] = data

        if len(self.buffer[frame_id]) == total_chunks:
            try:
                full_data = b''.join(self.buffer[frame_id][i] 
                                   for i in range(total_chunks))
                del self.buffer[frame_id]
                del self.frame_timeouts[frame_id]
                return full_data
            except KeyError:
                return None
        return None

def receive_data():
    global current_frame, current_text
    assembler = FrameAssembler()

    receiver1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver1.bind(('192.168.88.12', 5405))

    receiver2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver2.bind(('192.168.88.12', 5407))
    
    receivers = [receiver1, receiver2]
    for receiver in receivers:
        receiver.settimeout(1.0)
    print("啟動接收服務...")

    start_time = time.time()
    
    while True:
        for receiver in receivers:
            try:
                packet, _ = receiver.recvfrom(65535)
                if len(packet) < 1:
                    continue

                header = packet[0]
                data_type = (header & 0b11000000) >> 6

                if data_type == IMAGE_TYPE:
                    if len(packet) < 13:
                        continue
                    frame_id, total_chunks, chunk_id, data_len = struct.unpack('!IHHI', packet[1:13])
                    chunk_data = packet[13:]
                    complete_frame = assembler.add_chunk(frame_id, chunk_id, total_chunks, data_len, chunk_data)

                    if complete_frame:
                        with frame_lock:
                            current_frame = complete_frame
                            
                        # 更新性能指標
                        frame_timestamp = frame_id / 1000.0  # 轉換為秒
                        metrics.update(len(complete_frame), frame_timestamp)

                elif data_type == TEXT_TYPE:
                    with text_lock:
                        current_text = packet[1:].decode('utf-8')

            except socket.timeout:
                continue
            except Exception as e:
                print(f"接收錯誤: {e}")
                time.sleep(0.1)

def generate_frames():
    while True:
        with frame_lock:
            if current_frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       current_frame + b'\r\n')
        time.sleep(0.033)  # ~30 FPS

@app.route('/')
def index():
    return render_template('recv_index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/text_feed')
def text_feed():
    with text_lock:
        return current_text

@app.route('/performance_metrics')
def performance_metrics():
    return jsonify(metrics.get_metrics())

if __name__ == "__main__":
    thread = threading.Thread(target=receive_data)
    thread.daemon = True
    thread.start()
    app.run(host='0.0.0.0', port=8080, threaded=True)
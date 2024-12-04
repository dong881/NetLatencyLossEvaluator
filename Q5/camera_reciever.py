from flask import Flask, Response, render_template, jsonify
import socket
import struct
import time
import threading
from collections import defaultdict, deque

# 初始化 Flask 應用程式
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
        self.frame_timestamps = deque(maxlen=100)
        self.total_bytes = 0
        self.latency = 0
        self.lock = threading.Lock()
        
        # 吞吐量計算
        self.throughput_window = deque(maxlen=100)
        self.last_throughput = 0

    def update(self, frame_size):
        with self.lock:
            current_time = time.time()
            self.frame_timestamps.append(current_time)
            self.throughput_window.append((current_time, frame_size))

            # 清理過期的吞吐量數據
            self.throughput_window = deque(
                [(t, size) for t, size in self.throughput_window if current_time - t <= self.window_size]
            )

    def get_metrics(self):
        with self.lock:
            current_time = time.time()
            
            # FPS 計算
            recent_frames = [t for t in self.frame_timestamps if current_time - t <= self.window_size]
            fps = len(recent_frames) / self.window_size if recent_frames else 0
            
            # 吞吐量計算
            if self.throughput_window:
                total_bytes = sum(size for _, size in self.throughput_window)
                duration = current_time - self.throughput_window[0][0]
                throughput = (total_bytes * 8) / (duration * 1024) if duration > 0 else 0
            else:
                throughput = 0
            
            return {
                "fps": round(fps, 2),
                "throughput": round(throughput, 2),
                "latency": round(self.latency, 2)
            }

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
                full_data = b''.join(self.buffer[frame_id][i] for i in range(total_chunks))
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
                    # print(f"Frame ID: {frame_id}, Chunk ID: {chunk_id}, Total Chunks: {total_chunks}, Data Length: {data_len}")
                    complete_frame = assembler.add_chunk(frame_id, chunk_id, total_chunks, data_len, chunk_data)

                    if complete_frame:
                        with frame_lock:
                            current_frame = complete_frame
                        metrics.update(len(complete_frame))

                elif data_type == TEXT_TYPE:
                    if len(packet) < 9:
                        continue
                    timestamp_bytes = packet[1:9]
                    try:
                        with text_lock:
                            timestamp = struct.unpack('!Q', timestamp_bytes)[0]
                            current_time = int(time.time() * 1000000)  # 將 current_time 轉換為微秒
                            latency = current_time - timestamp
                            if latency < 0:
                                latency = 0
                            metrics.latency = (latency / 1000.0) # 將延遲轉換為 ms
                            current_text = timestamp
                    except struct.error:
                        pass

            except socket.timeout:
                continue
            except Exception as e:
                pass

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
        return jsonify({"text": current_text})

@app.route('/performance_metrics')
def performance_metrics():
    return jsonify(metrics.get_metrics())

if __name__ == "__main__":
    thread = threading.Thread(target=receive_data)
    thread.daemon = True
    thread.start()
    app.run(host='0.0.0.0', port=8080, threaded=True)
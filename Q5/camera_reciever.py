from flask import Flask, Response
import socket
import struct
import time
import threading
from collections import defaultdict

app = Flask(__name__)
current_frame = None  # 當前影像數據
current_text = "等待文字數據..."  # 當前文字數據
frame_lock = threading.Lock()
text_lock = threading.Lock()

# 資料類型標識
IMAGE_TYPE = 0b00
TEXT_TYPE = 0b01


class FrameAssembler:
    """負責組裝影像幀數據"""
    def __init__(self):
        self.buffer = defaultdict(dict)  # 分包緩衝區
        self.frame_timeouts = {}  # 每個幀的接收時間戳
        self.timeout = 1.0  # 幀超時時間（秒）

    def cleanup_old_frames(self):
        """清理超時的幀"""
        current_time = time.time()
        expired_frames = [
            frame_id for frame_id, timestamp in self.frame_timeouts.items()
            if current_time - timestamp > self.timeout
        ]
        for frame_id in expired_frames:
            del self.buffer[frame_id]
            del self.frame_timeouts[frame_id]

    def add_chunk(self, frame_id, chunk_id, total_chunks, data_len, data):
        """添加分包到緩衝區，並嘗試重組幀"""
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
    """接收並處理影像與文字數據"""
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

    while True:
        for receiver in receivers:
            try:
                packet, _ = receiver.recvfrom(65535)
                if len(packet) < 1:
                    continue

                # 解碼包頭 (2-bit 資料類型 + 其他數據)
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

                elif data_type == TEXT_TYPE:
                    with text_lock:
                        current_text = packet[1:].decode('utf-8')

            except socket.timeout:
                continue
            except Exception as e:
                print(f"接收錯誤: {e}")
                time.sleep(0.1)

def generate_frames():
    """生成影像數據流"""
    while True:
        with frame_lock:
            if current_frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       current_frame + b'\r\n')
        time.sleep(0.033)


@app.route('/')
def index():
    """前端主頁"""
    return """
    <html>
    <head>
        <title>即時數據顯示</title>
        <meta charset="utf-8">
        <style>
            body { text-align: center; font-family: Arial, sans-serif; }
            img { max-width: 100%; height: auto; }
            .text-data { margin-top: 20px; font-size: 20px; }
        </style>
    </head>
    <body>
        <h1>即時影像與文字數據</h1>
        <div>
            <img src="/video_feed" alt="影像流">
        </div>
        <div class="text-data" id="textData"></div>
        <script>
            function fetchTextData() {
                fetch('/text_feed')
                    .then(response => response.text())
                    .then(data => {
                        document.getElementById('textData').innerText = data;
                    });
            }
            setInterval(fetchTextData, 1000);  // 每秒更新文字數據
        </script>
    </body>
    </html>
    """


@app.route('/video_feed')
def video_feed():
    """影像流路由"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/text_feed')
def text_feed():
    """文字數據路由"""
    with text_lock:
        return current_text


if __name__ == "__main__":
    thread = threading.Thread(target=receive_data)
    thread.daemon = True
    thread.start()
    app.run(host='0.0.0.0', port=8080, threaded=True)
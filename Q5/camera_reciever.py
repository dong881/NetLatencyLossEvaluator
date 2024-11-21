from flask import Flask, Response
import socket
import struct
import time
import threading
from collections import defaultdict

app = Flask(__name__)
current_frame = None
frame_lock = threading.Lock()

class FrameAssembler:
    def __init__(self):
        self.buffer = defaultdict(dict)
    
    def add_chunk(self, frame_id, chunk_id, total_chunks, data_len, data):
        if len(data) != data_len:
            return None
            
        self.buffer[frame_id][chunk_id] = data
        
        if len(self.buffer[frame_id]) == total_chunks:
            try:
                full_data = b''
                for i in range(total_chunks):
                    if i not in self.buffer[frame_id]:
                        return None
                    full_data += self.buffer[frame_id][i]
                
                del self.buffer[frame_id]
                return full_data
            except Exception as e:
                print(f"組裝幀 {frame_id} 時出錯: {e}")
                return None
        return None

def receive_video():
    global current_frame
    assembler = FrameAssembler()
    
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(('192.168.88.12', 5405))
    receiver.settimeout(1.0)  # 設置較長的超時時間
    print("啟動接收服務...")
    
    while True:
        try:
            # 使用更大的接收緩衝區
            receiver.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535 * 10)
            
            packet, _ = receiver.recvfrom(65535)
            if len(packet) < 12:
                continue
            
            # 解析包頭
            frame_id, total_chunks, chunk_id, data_len = struct.unpack('!IHHI', packet[:12])
            chunk_data = packet[12:]
            
            # 添加接收確認
            try:
                receiver.sendto(struct.pack('!IHH', frame_id, chunk_id, 1), _)
            except:
                pass
                
            complete_frame = assembler.add_chunk(frame_id, chunk_id, total_chunks, data_len, chunk_data)
            
            if complete_frame is not None:
                with frame_lock:
                    current_frame = complete_frame
                print(f"\r接收幀 {frame_id}", end='')
                
        except socket.timeout:
            continue
        except Exception as e:
            print(f"\n接收錯誤: {type(e).__name__}: {str(e)}")
            time.sleep(0.1)  # 錯誤時短暫暫停

def generate_frames():
    while True:
        with frame_lock:
            if current_frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + 
                       current_frame + b'\r\n')
        time.sleep(0.033)

@app.route('/')
def index():
    return """
    <html>
    <head>
        <title>視訊串流</title>
        <meta charset="utf-8">
        <style>
            body { text-align: center; }
            img { max-width: 100%; }
        </style>
    </head>
    <body>
        <h1>即時視訊串流</h1>
        <img src="/video_feed">
    </body>
    </html>
    """

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    thread = threading.Thread(target=receive_video)
    thread.daemon = True
    thread.start()
    app.run(host='0.0.0.0', port=8080, threaded=True)
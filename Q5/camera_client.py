"""
This script sets up a Flask web server that streams video frames received over a UDP socket.

sudo apt-get install libgtk2.0-dev pkg-config
pip install Flask Flask-Response

Modules:
    cv2: OpenCV library for image processing.
    socket: Provides low-level networking interface.
    struct: Provides functions to interpret bytes as packed binary data.
    numpy: Library for numerical operations.
    flask: Micro web framework for Python.

Functions:
    generate_frames(): Generator function that receives video frame data in chunks over UDP,
                       reconstructs the frames, and yields them as JPEG-encoded images.
    video_feed(): Flask route that serves the video feed by calling generate_frames().

Global Variables:
    MAX_DGRAM (int): Maximum size of a UDP datagram.
    server_socket (socket): UDP socket for receiving video frame data.
    data (bytes): Byte string to store the reconstructed frame data.
    frame_dict (dict): Dictionary to store received chunks of frame data.
    expected_chunks (int or None): Number of expected chunks for the current frame.

Usage:
    Run this script to start the Flask web server. Access the video feed at http://<host>:5000/video_feed.
"""
import cv2
import socket
import struct
import numpy as np
from flask import Flask, Response

app = Flask(__name__)

# 定義數據塊大小
MAX_DGRAM = 65536

# 創建socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('192.168.88.12', 5405))
print("Waiting for data...")

data = b""
frame_dict = {}
expected_chunks = None

def generate_frames():
    global data, frame_dict, expected_chunks
    while True:
        packet, _ = server_socket.recvfrom(MAX_DGRAM)
        if not packet:
            break

        # 獲取總塊數和當前塊編號
        total_chunks = struct.unpack("B", packet[:1])[0]
        chunk_number = struct.unpack("B", packet[1:2])[0]
        chunk_data = packet[2:]

        # 將數據塊存儲在字典中
        frame_dict[chunk_number] = chunk_data

        # 設置預期的數據塊數量
        if expected_chunks is None:
            expected_chunks = total_chunks

        # 檢查是否接收到所有數據塊
        if len(frame_dict) == expected_chunks:
            # 重組數據
            data = b"".join([frame_dict[i] for i in sorted(frame_dict.keys())])
            frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

            # 將影像編碼為JPEG格式
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # 清空字典和重置預期塊數
            frame_dict.clear()
            expected_chunks = None

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
import cv2
import socket
import struct
import numpy as np
from flask import Flask, Response
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

MAX_DGRAM = 8192

# 創建 socket 並設置接收緩衝區大小
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
server_socket.bind(('192.168.88.12', 5405))
logger.info("Socket bound and listening on port 5405")

def validate_shape(shape):
    """驗證影像形狀是否合理"""
    height, width, channels = shape
    return (0 < height <= 2000 and 
            0 < width <= 2000 and 
            channels == 3)

def generate_frames():
    frame_dict = {}
    expected_chunks = None
    frame_shape = None
    
    while True:
        try:
            packet, addr = server_socket.recvfrom(MAX_DGRAM)
            if not packet:
                continue

            # 解析包類型
            packet_type = packet[0]
            
            # 處理幀頭包
            if packet_type == 0:  # 幀頭包
                try:
                    num_chunks = struct.unpack("B", packet[1:2])[0]
                    shape = struct.unpack("III", packet[2:14])
                    
                    if validate_shape(shape):
                        expected_chunks = num_chunks
                        frame_shape = shape
                        frame_dict.clear()
                        logger.debug(f"Valid header received: chunks={num_chunks}, shape={shape}")
                    else:
                        logger.warning(f"Invalid shape received: {shape}")
                except Exception as e:
                    logger.error(f"Header parsing error: {e}")
                continue

            # 處理數據包
            chunk_number = packet_type - 1  # 數據包類型從1開始
            if expected_chunks is None or chunk_number >= expected_chunks:
                continue

            chunk_data = packet[1:]
            frame_dict[chunk_number] = chunk_data

            # 檢查是否收到完整幀
            if len(frame_dict) == expected_chunks:
                try:
                    # 重組數據
                    data = b"".join(frame_dict[i] for i in range(expected_chunks))
                    
                    # 解碼影像
                    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                    
                    if frame is not None and frame.shape == frame_shape:
                        ret, buffer = cv2.imencode('.jpg', frame)
                        if ret:
                            frame_bytes = buffer.tobytes()
                            yield (b'--frame\r\n'
                                  b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                            logger.debug("Frame successfully sent")
                    else:
                        logger.warning("Frame decode failed or shape mismatch")
                
                except Exception as e:
                    logger.error(f"Frame processing error: {e}")
                
                frame_dict.clear()
                expected_chunks = None
                frame_shape = None

        except Exception as e:
            logger.error(f"Main loop error: {e}")
            continue

@app.route('/')
def index():
    return '<html><body><img src="/video_feed" width="640" height="480"></body></html>'

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    try:
        logger.info("Starting Flask server...")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    finally:
        server_socket.close()
        logger.info("Server stopped")
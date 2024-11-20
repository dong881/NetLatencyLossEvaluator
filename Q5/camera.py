import cv2
import socket
import struct

# 創建socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('192.168.88.21', 5409))
proxy_address = ('192.168.88.111', 5406)
print("Server is listening...")

# 使用OpenCV捕捉視訊
cap = cv2.VideoCapture(0)

# 定義每個數據包的最大大小
MAX_DGRAM = 2**16 - 64  # 65536 - 64

def send_frame(frame):
    # 將影像數據壓縮為JPEG格式
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    result, encoded_image = cv2.imencode('.jpg', frame, encode_param)
    data = encoded_image.tobytes()
    
    # 將數據分塊
    num_chunks = (len(data) // MAX_DGRAM) + 1
    for i in range(num_chunks):
        start = i * MAX_DGRAM
        end = start + MAX_DGRAM
        chunk = data[start:end]
        
        # 發送數據塊，包含總塊數和當前塊編號
        server_socket.sendto(struct.pack("B", num_chunks) + struct.pack("B", i) + chunk, proxy_address)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    send_frame(frame)

cap.release()
server_socket.close()
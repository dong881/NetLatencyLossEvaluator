import cv2
import socket
import struct
import numpy as np

# 創建socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('192.168.88.21', 5409))
proxy_address = ('192.168.88.111', 5406)
print("Server is listening...")

# 使用OpenCV捕捉視訊
cap = cv2.VideoCapture(0)

# 定義較小的數據包大小
MAX_DGRAM = 8192  # 降低到8KB

def send_frame(frame):
    try:
        # 壓縮影像品質
        _, encoded_frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        data = encoded_frame.tobytes()
        
        # 計算分塊數量
        num_chunks = (len(data) + MAX_DGRAM - 1) // MAX_DGRAM
        
        # 發送幀頭包 (類型0)
        header_packet = struct.pack("BB", 0, num_chunks) + struct.pack("III", *frame.shape)
        server_socket.sendto(header_packet, proxy_address)
        
        # 分塊發送數據 (類型1~n)
        for i in range(num_chunks):
            start = i * MAX_DGRAM
            end = min(start + MAX_DGRAM, len(data))
            chunk = data[start:end]
            
            # 包類型為塊編號+1
            packet = struct.pack("B", i + 1) + chunk
            server_socket.sendto(packet, proxy_address)
            
    except Exception as e:
        print(f"發送錯誤: {str(e)}")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("無法讀取鏡頭")
            break
        
        # 縮小影像尺寸以減少數據量
        frame = cv2.resize(frame, (640, 480))
        send_frame(frame)
        
except KeyboardInterrupt:
    print("程式執行被用戶中斷")
finally:
    cap.release()
    server_socket.close()
    print("已關閉鏡頭和socket連接")
import cv2
import socket
import struct
import numpy as np

# 定義數據塊大小
MAX_DGRAM = 65536

# 創建socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('192.168.88.12', 5405))
print("Waiting for data...")

data = b""
frame_dict = {}
expected_chunks = None

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

        # 顯示影像
        # 如果你在無頭環境中運行，請將這部分代碼替換為保存影像或其他處理方式
        cv2.imshow('Video', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # 清空字典和重置預期塊數
        frame_dict.clear()
        expected_chunks = None

server_socket.close()
cv2.destroyAllWindows()
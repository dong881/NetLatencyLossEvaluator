import cv2
import socket
import struct
import time

def main():
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proxy_address = ('192.168.88.12', 5405)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("無法開啟攝影機")
        return

    print(f"開始傳送影像至 {proxy_address}")
    frame_id = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            # 壓縮影像
            frame = cv2.resize(frame, (1920,1080))
            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 20])
            jpeg_bytes = jpeg.tobytes()
            
            # 分包
            chunk_size = 60000
            chunks = [jpeg_bytes[i:i+chunk_size] for i in range(0, len(jpeg_bytes), chunk_size)]
            total_chunks = len(chunks)
            
            print(f"\r幀 {frame_id}: 大小 {len(jpeg_bytes)}, 分包數 {total_chunks}", end='')
            
            # 發送每個分包
            for chunk_id, chunk in enumerate(chunks):
                # 包頭: 幀ID(4) + 總包數(2) + 包ID(2) + 數據長度(4)
                header = struct.pack('!IHHI', frame_id, total_chunks, chunk_id, len(chunk))
                packet = header + chunk
                
                try:
                    sender.sendto(packet, proxy_address)
                    time.sleep(0.001)
                except:
                    continue
            
            frame_id = (frame_id + 1) % 1000
            time.sleep(0.033)
            
    except KeyboardInterrupt:
        print("\n停止傳送")
    finally:
        cap.release()
        sender.close()

if __name__ == "__main__":
    main()
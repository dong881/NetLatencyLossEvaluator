import cv2
import socket
import struct
import time
import threading
from queue import PriorityQueue

# Packet Header Constants
IMAGE_TYPE = 0b00  # Image data identifier
TEXT_TYPE = 0b01   # Text data identifier
IMAGE_QOS = 0b100  # QoS for image data
# TEXT_QOS = 0b100   # QoS for text data
TEXT_QOS = 0b010   # QoS for text data

# Packet transmission details
IP_ADDRESS = "192.168.88.111"
PORT_MAPPING = {4: 5406, 2: 5408}

class Packet:
    """Represents a data packet with header and payload."""
    def __init__(self, data_type, qos, payload):
        self.header = struct.pack('!B', (data_type << 6) | qos)
        self.payload = payload
        self.qos = qos

    def get_packet(self):
        """Returns the complete packet."""
        return self.header + self.payload

class ImageProcessor:
    """Handles image capture, compression, and segmentation."""
    def __init__(self, chunk_size=65000):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise Exception("Unable to open the camera.")
        self.chunk_size = chunk_size

    def capture_image_packets(self, frame_id):
        """Captures a frame, compresses it, and splits it into packets."""
        ret, frame = self.cap.read()
        if not ret:
            return []

        # Compress image
        frame = cv2.resize(frame, (1920, 1080))
        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 20])
        jpeg_bytes = jpeg.tobytes()

        # Segment into chunks
        chunks = [jpeg_bytes[i:i + self.chunk_size] for i in range(0, len(jpeg_bytes), self.chunk_size)]
        packets = [
            Packet(IMAGE_TYPE, IMAGE_QOS, struct.pack('!IHHI', frame_id, len(chunks), chunk_id, len(chunk)) + chunk)
            for chunk_id, chunk in enumerate(chunks)
        ]
        return packets

    def release(self):
        """Releases the camera."""
        self.cap.release()

class TimestampGenerator:
    """Generates timestamp packets continuously."""
    def __init__(self):
        pass

    def generate_packet(self):
        """Generates a timestamp packet with Unix timestamp."""
        # 取得 Unix timestamp 並轉換為整數
        timestamp = int(time.time()*1000000)
        # 使用 struct.pack 將整數轉換為 8 bytes 的二進制格式
        timestamp_bytes = struct.pack('!Q', timestamp)
        return Packet(TEXT_TYPE, TEXT_QOS, timestamp_bytes)

class PacketTransmitter:
    """Manages the queuing and transmission of packets."""
    def __init__(self):
        self.queues = PriorityQueue()
        self.sockets = {qos: socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for qos in PORT_MAPPING}

    def enqueue_packet(self, packet):
        """Adds a packet to the queue."""
        self.queues.put((-packet.qos, time.time(), packet))  # PriorityQueue uses min-heap, so use -qos for max-priority

    def transmit(self):
        """Transmits packets based on QoS priority."""
        while True:
            if not self.queues.empty():
                _, _, packet = self.queues.get()
                port = PORT_MAPPING[packet.qos]
                self.sockets[packet.qos].sendto(packet.get_packet(), (IP_ADDRESS, port))

    def close(self):
        """Closes all sockets."""
        for sock in self.sockets.values():
            sock.close()

def main():
    image_processor = ImageProcessor()
    timestamp_generator = TimestampGenerator()
    transmitter = PacketTransmitter()

    frame_id = 0
    try:
        # Start transmitter in a separate thread
        threading.Thread(target=transmitter.transmit, daemon=True).start()

        while True:
            # Generate image packets
            image_packets = image_processor.capture_image_packets(frame_id)
            for packet in image_packets:
                transmitter.enqueue_packet(packet)

            # Generate timestamp packet
            timestamp_packet = timestamp_generator.generate_packet()
            transmitter.enqueue_packet(timestamp_packet)

            frame_id = (frame_id + 1) % 1000
            time.sleep(0.033)  # Simulate 30 FPS

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        image_processor.release()
        transmitter.close()

if __name__ == "__main__":
    main()
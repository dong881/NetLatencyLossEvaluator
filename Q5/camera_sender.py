from flask import Flask, render_template, request, jsonify
import cv2
import socket
import struct
import time
import threading
import json
from queue import PriorityQueue
from pathlib import Path

# 建立 Flask 應用
app = Flask(__name__)

qos_manager = None


# Packet Header Constants
IMAGE_TYPE = 0b00
TEXT_TYPE = 0b01

# Default QoS settings
DEFAULT_IMAGE_QOS = 4
DEFAULT_TEXT_QOS = 2


# Packet transmission details
IP_ADDRESS = "192.168.88.111"
PORT_MAPPING = {
    # 0: 5410,
    # 1: 5409,
    2: 4567,
    # 3: 5407,
    4: 5678,
    # 5: 5405,
    # 6: 5404,
    # 7: 5403,
    8: 5678,
}

# Flask 路由
@app.route('/')
def index():
    return render_template('control_index.html')

@app.route('/api/qos', methods=['GET', 'POST'])
def manage_qos():
    global qos_manager
    if request.method == 'POST':
        data = request.json
        qos_manager.update_qos(
            image_qos=data.get('image_qos'),
            text_qos=data.get('text_qos')
        )
        return jsonify({"status": "success"})
    else:
        return jsonify({
            "image_qos": qos_manager.image_qos,
            "text_qos": qos_manager.text_qos
        })

class QoSManager:
    """Manages QoS settings for different data types."""
    def __init__(self):
        self.config_file = Path("qos_config.json")
        self.image_qos = DEFAULT_IMAGE_QOS
        self.text_qos = DEFAULT_TEXT_QOS
        self.load_config()

    def load_config(self):
        """Loads QoS configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.image_qos = config.get('image_qos', DEFAULT_IMAGE_QOS)
                    self.text_qos = config.get('text_qos', DEFAULT_TEXT_QOS)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        """Saves current QoS configuration to file."""
        config = {
            'image_qos': self.image_qos,
            'text_qos': self.text_qos
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def update_qos(self, image_qos=None, text_qos=None):
        """Updates QoS settings and saves to config."""
        if image_qos is not None:
            self.image_qos = image_qos
        if text_qos is not None:
            self.text_qos = text_qos
        self.save_config()

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

    def capture_image_packets(self, frame_id, qos):
        """Captures a frame, compresses it, and splits it into packets."""
        ret, frame = self.cap.read()
        if not ret:
            return []

        frame = cv2.resize(frame, (1920, 1080))
        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 20])
        jpeg_bytes = jpeg.tobytes()

        chunks = [jpeg_bytes[i:i + self.chunk_size] 
                 for i in range(0, len(jpeg_bytes), self.chunk_size)]
        packets = [
            Packet(IMAGE_TYPE, qos, 
                  struct.pack('!IHHI', frame_id, len(chunks), chunk_id, len(chunk)) + chunk)
            for chunk_id, chunk in enumerate(chunks)
        ]
        return packets

    def release(self):
        """Releases the camera."""
        self.cap.release()

class TimestampGenerator:
    """Generates timestamp packets continuously."""
    def generate_packet(self, qos):
        """Generates a timestamp packet with Unix timestamp."""
        timestamp = int(time.time()*1000000)
        timestamp_bytes = struct.pack('!Q', timestamp)
        return Packet(TEXT_TYPE, qos, timestamp_bytes)

class PacketTransmitter:
    """Manages the queuing and transmission of packets."""
    def __init__(self):
        self.queues = PriorityQueue()
        self.sockets = {qos: socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
                       for qos in PORT_MAPPING}

    def enqueue_packet(self, packet):
        """Adds a packet to the queue."""
        self.queues.put((-packet.qos, time.time(), packet))

    def transmit(self):
        """Transmits packets based on QoS priority."""
        while True:
            if not self.queues.empty():
                _, _, packet = self.queues.get()
                port = PORT_MAPPING[packet.qos]
                self.sockets[packet.qos].sendto(
                    packet.get_packet(), 
                    (IP_ADDRESS, port)
                )

    def close(self):
        """Closes all sockets."""
        for sock in self.sockets.values():
            sock.close()

def main():
    global qos_manager
    qos_manager = QoSManager()
    image_processor = ImageProcessor()
    timestamp_generator = TimestampGenerator()
    transmitter = PacketTransmitter()

    frame_id = 0
    try:
        threading.Thread(target=transmitter.transmit, daemon=True).start()
        
        # 啟動 Flask 應用
        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), 
                        daemon=True).start()

        while True:
            image_packets = image_processor.capture_image_packets(
                frame_id, 
                qos_manager.image_qos
            )
            for packet in image_packets:
                transmitter.enqueue_packet(packet)

            timestamp_packet = timestamp_generator.generate_packet(
                qos_manager.text_qos
            )
            transmitter.enqueue_packet(timestamp_packet)

            frame_id = (frame_id + 1) % 1000
            time.sleep(0.033)

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        image_processor.release()
        transmitter.close()

if __name__ == "__main__":
    main()
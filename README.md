# NetLatencyLossEvaluator

## Team Members
- **M11302208 陳宥余**
- **M11302209 徐銘鴻**
- **M11302204 賴俊愷**
- **M11302229 陳均諭**
- **M11302206 李冠槿**

---

## Project Overview
This project, *NetLatencyLossEvaluator*, focuses on network performance evaluation through socket programming by simulating network delay and packet loss, targeting IoT applications that have strict latency requirements. The project involves creating UDP servers, proxies, and clients to measure the effect of delay and packet loss over various paths.

### Key Objectives
1. **Network Performance Evaluation**: Implement a system to monitor the effects of delay and packet loss on network performance, particularly within IoT applications.
2. **Socket Programming**: Develop UDP-based components to create paths between a server and client via intermediary proxies that simulate network behavior.
3. **Optimization and Enhancement**: Propose and test methods to optimize network paths and ensure reliable data transmission.

## Project Structure
The project includes the following components:

- **`client.py`**: Implements the UDP client, which listens for packets from the server. It is designed to handle two paths and record the delay and loss metrics of each packet.
  
- **`proxy.py`**: Includes the logic for two UDP proxies:
  - **UDP Proxy 1** simulates packet loss with a 10% drop rate.
  - **UDP Proxy 2** introduces a 500 ms delay with a 5% probability on each packet.
  
- **`server.py`**: Implements the UDP server that transmits packets to the client through the defined paths and manages the transmission intervals. It ensures that the client receives all packets in an optimal time frame.

## Project Requirements
1. **Socket Programming**: The communication among server, client, and proxies is implemented through UDP sockets.
2. **Network Path Simulation**:
   - **Path 1**: Server -> Proxy 1 -> Client (Port 5405-5406).
   - **Path 2**: Server -> Proxy 2 -> Client (Port 5407-5408).
   - **Path 3**: Direct connection from the server to the client.
3. **Loss and Delay Implementation**:
   - **Path 1**: Drops packets with a 10% probability.
   - **Path 2**: Adds a 500 ms delay with a 5% probability.
4. **Optimization Strategy**: Develop and implement a method for selecting paths to minimize transmission time for the client to receive all packets, given a large packet size (100,000 packets).

## Project Tasks

### Q1. Implement Path 1
- Develop `UDP Proxy 1` to forward packets from the server to the client with a 10% packet drop rate.
- Ensure packets are marked sequentially and transmitted every 100 ms.

### Q2. Implement Path 2
- Configure `UDP Proxy 2` to forward packets from the server to the client with a 5% probability of adding a 500 ms delay.
- Follow the same sequential marking and timing as in Path 1.

### Q3. Simulate Delay and Loss
- Implement logic for both UDP proxies to simulate packet drop and delay, verifying correct functionality through testing.

### Q4. Optimize Transmission Strategy
- Design an algorithm for the server to minimize packet reception time at the client.
- Log and report the total delay experienced by the client upon receiving all packets.

### Q5 (Optional). Hardware Implementation
- If hardware is available, implement and test the proposed optimization on physical devices such as the provided Mikrotik switch and Raspberry Pi.

## Running the Project
1. Set up Python 3.7 or later and install any required packages.
2. Run each script (`server.py`, `proxy.py`, and `client.py`) in separate terminal windows.
3. Monitor the client output to evaluate the delay and loss for each packet received.

## Results and Observations
- Detailed performance metrics, including delay and loss percentages for each path, will be analyzed.
- Observations and insights regarding the effect of different network conditions on IoT data transmission.

## Submission Details
- **Final Presentation**: December 12, 2024.
- **Final Report Deadline**: December 18, 2024.
- Format the final report using the IEEE template and submit the `.zip` file as specified.

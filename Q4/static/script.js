// Global state
let isTransmitting = false;
let currentSessionId = null;
let updateInterval = null;
let toggleBtn, statusText, timeline, throughputChart, packetChart;

// Move all DOM initialization into DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize UI Elements
    toggleBtn = document.getElementById('toggleBtn');
    statusText = document.getElementById('statusText');
    timeline = document.getElementById('packetTimeline');

    // Add event listeners
    toggleBtn.addEventListener('click', async () => {
        if (!isTransmitting) {
            await startTransmission();
        } else {
            await stopTransmission();
        }
    });

    // Initial stats fetch
    fetchStats();
    const themeToggle = document.getElementById('theme-toggle');
    
    // Check saved theme
    const savedTheme = localStorage.getItem('theme') || 'system';
    applyTheme(savedTheme);
    
    themeToggle.addEventListener('click', () => {
        const currentTheme = localStorage.getItem('theme') || 'system';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    });
});

// Transmission Control
async function startTransmission() {
    try {
        const response = await fetch('/api/transmission/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'started') {
            isTransmitting = true;
            currentSessionId = data.session_id;
            toggleBtn.textContent = 'Stop Transmission';
            toggleBtn.classList.add('active');
            startPeriodicUpdates();
        }
    } catch (error) {
        console.error('Failed to start transmission:', error);
    }
}

async function stopTransmission() {
    try {
        const response = await fetch('/api/transmission/toggle', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'stopping') {
            isTransmitting = false;
            toggleBtn.textContent = 'Start Transmission';
            toggleBtn.classList.remove('active');
            stopPeriodicUpdates();
        }
    } catch (error) {
        console.error('Failed to stop transmission:', error);
    }
}

// Data Updates
function startPeriodicUpdates() {
    updateInterval = setInterval(fetchStats, 1000);
}

function stopPeriodicUpdates() {
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
}

async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        updateUI(stats);
    } catch (error) {
        console.error('Error fetching stats:', error);
    }

    // {
    //     'compression': {'original_size', 'compressed_size', 'ratio'},
    //     'transmission': {'current_run', 'total_runs', 'status'},
    //     'performance': {'total_rtt', 'average_rtt', 'average_throughput', 'average_packet_loss_rate'},
    //     'paths': {'path1': {'packets', 'success'}, 'path2': {'packets', 'success'}},
    //     'packets': [{'sequence', 'timestamp', 'path', 'size', 'type', 'status'}]
    // }
}

function updateUI(stats) {
    updateStatus(stats);
    updateTimeline(stats);
}

function updateStatus(stats) {
    // Update Compression Stats
    document.getElementById('originalSize').textContent = (stats.compression.original_size / 1024).toFixed(2);
    document.getElementById('compressedSize').textContent = (stats.compression.compressed_size / 1024).toFixed(2);
    document.getElementById('compressionRatio').textContent = `${stats.compression.ratio.toFixed(1)}%`;

    // Update Transmission Stats
    document.getElementById('currentRun').textContent = stats.transmission.current_run;
    document.getElementById('totalRuns').textContent = stats.transmission.total_runs;
    document.getElementById('status').textContent = stats.transmission.status;

    // Update Performance Metrics
    document.getElementById('averageRtt').textContent = `${stats.performance.average_rtt.toFixed(2)} ms`;
    document.getElementById('totalRtt').textContent = `${stats.performance.total_rtt.toFixed(2)} ms`;
    document.getElementById('avgThroughput').textContent = `${stats.performance.average_throughput.toFixed(2)} KB/s`;
    document.getElementById('packetLossRate').textContent = `${stats.performance.average_packet_loss_rate.toFixed(1)}%`;

    // Update Path Statistics
    const path1 = stats.paths.path1;
    const path2 = stats.paths.path2;

    const path1SuccessRate = path1.packets > 0 ? (path1.success / path1.packets * 100).toFixed(1) : '0.0';
    const path2SuccessRate = path2.packets > 0 ? (path2.success / path2.packets * 100).toFixed(1) : '0.0';

    document.getElementById('path1Stats').textContent = 
        `${path1.success}/${path1.packets} packets (${path1SuccessRate}%)`;
    document.getElementById('path1Progress').style.width = `${path1SuccessRate}%`;

    document.getElementById('path2Stats').textContent = 
        `${path2.success}/${path2.packets} packets (${path2SuccessRate}%)`;
    document.getElementById('path2Progress').style.width = `${path2SuccessRate}%`;
}

function updatePathStats(pathStats) {
    ['path1', 'path2'].forEach(path => {
        const stats = pathStats[path];
        const successRate = stats.packets > 0 ? (stats.success / stats.packets * 100) : 0;
        document.getElementById(`${path}Progress`).style.width = `${successRate}%`;
        document.getElementById(`${path}Stats`).textContent = 
            `${stats.success}/${stats.packets} packets (${successRate.toFixed(1)}%)`;
    });
}

function updateTimeline(stats) {
    const path1Timeline = document.getElementById('path1Timeline');
    const path2Timeline = document.getElementById('path2Timeline');
    const ackTimeline = document.getElementById('ackTimeline');

    // Use single shared start time for all paths
    const globalStartTime = Math.min(...stats.packets.map(p => p.timestamp));
    const endTime = Math.max(...stats.packets.map(p => p.timestamp));
    const duration = (endTime - globalStartTime) / 1000;

    // Sort packets by timestamp
    const sortedPackets = [...stats.packets].sort((a, b) => a.timestamp - b.timestamp);

    // Track existing packets
    const existingPackets = {
        path1: new Set([...path1Timeline.children].map(el => el.dataset.packetId)),
        path2: new Set([...path2Timeline.children].map(el => el.dataset.packetId)),
        ack: new Set([...ackTimeline.children].map(el => el.dataset.packetId))
    };

    sortedPackets.forEach(packet => {
        const packetId = `${packet.path || 'ack'}-${packet.timestamp}`;
        
        // Skip if packet already exists
        if (packet.type === 'acked' && existingPackets.ack.has(packetId)) return;
        if (packet.path === 'path1' && existingPackets.path1.has(packetId)) return;
        if (packet.path === 'path2' && existingPackets.path2.has(packetId)) return;

        const packetEl = createPacketElement(packet);
        packetEl.dataset.packetId = packetId;
        
        const relativeTime = (packet.timestamp - globalStartTime) / 1000;
        const baseSpacing = relativeTime * 50;
        
        let extraSpacing = packet.path === 'path1' ? 25 : 0;
        packetEl.style.marginLeft = `${baseSpacing + extraSpacing}px`;

        // Append only new packets
        if (packet.type === 'acked') {
            ackTimeline.appendChild(packetEl);
        } else if (packet.path === 'path1') {
            path1Timeline.appendChild(packetEl);
        } else {
            path2Timeline.appendChild(packetEl);
        }
    });

    // Clean up old packets that are no longer in stats
    const currentPacketIds = new Set(sortedPackets.map(p => 
        `${p.path || 'ack'}-${p.timestamp}`
    ));

    [path1Timeline, path2Timeline, ackTimeline].forEach(track => {
        [...track.children].forEach(el => {
            if (!currentPacketIds.has(el.dataset.packetId)) {
                el.remove();
            }
        });
    });
}

function createPacketElement(packet) {
    const el = document.createElement('div');
    el.id = `packet-${packet.sequence}`;
    el.className = `packet packet-${packet.path || 'type-acked'}`;
    el.textContent = `#${packet.sequence}`;
    
    // Enhanced tooltip
    const time = new Date(packet.timestamp).toLocaleTimeString();
    const size = packet.size ? `${(packet.size / 1024).toFixed(2)}KB` : 'N/A';
    
    el.title = `Sequence: ${packet.sequence}
                    Time: ${time}
                    ${packet.path ? 'Path: ' + packet.path : ''}
                    ${packet.size ? 'Size: ' + size : ''}
                    Type: ${packet.type}
                    Status: ${packet.status}`;

    return el;
}

function applyTheme(theme) {
    // Remove any existing theme class
    document.body.classList.remove('light-theme', 'dark-theme');
    
    if (theme === 'system') {
        // Use system preference
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.body.classList.add('dark-theme');
        } else {
            document.body.classList.add('light-theme');
        }
    } else {
        // Use explicit theme choice
        document.body.classList.add(`${theme}-theme`);
    }
}
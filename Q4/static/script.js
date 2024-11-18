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
    statusText.textContent = stats.transmission_status;
    document.getElementById('totalPackets').textContent = stats.packets.length;
    
    const successRate = calculateSuccessRate(stats.packets);
    document.getElementById('successRate').textContent = `${successRate}%`;
    
    const currentThroughput = calculateThroughput(stats);
    document.getElementById('throughput').textContent = `${currentThroughput.toFixed(2)} KB/s`;
    
    updatePathStats(stats.path_stats);
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
    const newPackets = stats.packets.filter(packet => 
        !document.getElementById(`packet-${packet.id}`)
    );
    
    newPackets.forEach(packet => {
        const packetEl = createPacketElement(packet);
        timeline.appendChild(packetEl);
        timeline.scrollLeft = timeline.scrollWidth;
    });
}

function createPacketElement(packet) {
    const el = document.createElement('div');
    el.id = `packet-${packet.id}`;
    el.className = `packet packet-${packet.path}`;
    el.textContent = `#${packet.id}`;
    
    if (packet.status === 'acked') {
        el.classList.add('packet-ack');
    }
    
    return el;
}

// Utility Functions
function calculateSuccessRate(packets) {
    const successful = packets.filter(p => p.status === 'acked').length;
    return packets.length > 0 
        ? ((successful / packets.length) * 100).toFixed(1)
        : '0.0';
}

function calculateThroughput(stats) {
    if (!stats.start_time || !stats.packets.length) return 0;
    
    const totalData = stats.packets.reduce((sum, p) => sum + p.size, 0);
    const duration = moment().diff(moment(stats.start_time), 'seconds');
    return duration > 0 ? (totalData / duration) / 1024 : 0;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
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
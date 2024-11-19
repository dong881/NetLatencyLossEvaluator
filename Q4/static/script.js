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
    updateInterval = setInterval(fetchStats, 40);
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

// 在建立圖表之前，先定義並註冊插件
const customLabelsPlugin = {
    id: 'customLabels',
    afterDatasetsDraw: (chart) => {
        const ctx = chart.ctx;
        chart.data.datasets.forEach((dataset, i) => {
            const meta = chart.getDatasetMeta(i);
            dataset.data.forEach((datapoint, index) => {
                const text = datapoint.seqNum.toString();
                const position = meta.data[index].getProps(['x', 'y']);
                
                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.font = 'bold 12px Arial';
                ctx.fillStyle = 'white';
                ctx.fillText(text, position.x, position.y);
                ctx.restore();
            });
        });
    }
};

// 註冊插件
Chart.register(customLabelsPlugin);

function updateTimeline(stats) {
    const ctx = document.getElementById('packetTimelineChart').getContext('2d');

    // 前面的資料準備部分保持不變
    const sortedPackets = [...stats.packets].sort((a, b) => a.timestamp - b.timestamp);

    const path1Data = sortedPackets
        .filter(packet => packet.path === 'path1')
        .map(packet => ({
            x: packet.timestamp,
            y: 0.95,
            seqNum: packet.sequence
        }));
    
    const path2Data = sortedPackets
        .filter(packet => packet.path === 'path2')
        .map(packet => ({
            x: packet.timestamp,
            y: 1,
            seqNum: packet.sequence
        }));
    
    const ackData = sortedPackets
        .filter(packet => packet.type === 'acked')
        .map(packet => ({
            x: packet.timestamp,
            y: 1.05,
            seqNum: packet.sequence
        }));

    // 圖表更新邏輯保持不變
    let pointRadiussize = 28;
    if (window.packetTimelineChart && window.packetTimelineChart.data && window.packetTimelineChart.data.datasets) {
        window.packetTimelineChart.data.datasets[0].data = path1Data;
        window.packetTimelineChart.data.datasets[1].data = path2Data;
        window.packetTimelineChart.data.datasets[2].data = ackData;
        window.packetTimelineChart.update();
    } else {
        window.packetTimelineChart = new Chart(ctx, {
            type: 'scatter',
            data: {
            datasets: [
                {
                label: 'Path 1',
                data: path1Data,
                backgroundColor: 'rgba(75, 192, 192, 0.8)',
                pointStyle: 'rectRounded',
                pointRadius: pointRadiussize,
                pointHoverRadius: 18,
                showLine: false
                },
                {
                label: 'Path 2',
                data: path2Data,
                backgroundColor: 'rgba(153, 102, 255, 0.8)',
                pointStyle: 'rectRounded',
                pointRadius: pointRadiussize,
                pointHoverRadius: 18,
                showLine: false
                },
                {
                label: 'ACKs',
                data: ackData,
                backgroundColor: 'rgba(255, 159, 64, 0.8)',
                pointStyle: 'rectRounded',
                pointRadius: pointRadiussize,
                pointHoverRadius: 18,
                showLine: false
                }
            ]
            },
            options: {
            responsive: true,
            animation: {
                duration: 1000,
                easing: 'easeOutQuart'
            },
            plugins: {
                title: {
                display: true,
                text: 'Packet Timeline'
                },
                tooltip: {
                enabled: false // 關閉tooltip因為已經直接顯示序號
                },
            },
            scales: {
                x: {
                display: true,
                title: {
                    display: true,
                    text: 'Timestamp'
                }
                },
                y: {
                display: true,
                title: {
                    display: true,
                    text: 'Path'
                },
                min: 0.9,
                max: 1.1,
                ticks: {
                    callback: function(value) {
                    if (value === 0.95) return 'Path 1';
                    if (value === 1) return 'Path 2';
                    if (value === 1.05) return 'ACKs';
                    return '';
                    }
                }
                }
            }
            },
            plugins: [customLabelsPlugin]
        });
    }
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
// Global state
let isTransmitting = false;
let currentSessionId = null;
let updateInterval = null;
let toggleBtn, statusText, timeline, throughputChart, packetChart;

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
        
        if (data.status === 'running') {
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
        
        if (data.status === 'idle') {
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

// 在 fetchStats 函數中新增歷史資料的處理
async function fetchStats() {
    try {
        const [statsResponse, historyResponse] = await Promise.all([
            fetch('/api/stats'),
            fetch('/api/history')
        ]);
        
        const stats = await statsResponse.json();
        const history = await historyResponse.json();
        
        updateUI(stats);
        updateHistory(history);
    } catch (error) {
        console.error('Error fetching data:', error);
    }

    // {
    //     'compression': {'original_size', 'compressed_size', 'ratio'},
    //     'transmission': {'current_run', 'total_runs', 'status'},
    //     'performance': {'total_rtt', 'average_rtt', 'average_throughput', 'average_packet_loss_rate'},
    //     'paths': {'path1': {'packets', 'success'}, 'path2': {'packets', 'success'}},
    //     'packets': [{'sequence', 'timestamp', 'path', 'size', 'type', 'status'}]
    // }
}

// 修改 updateHistory 函數，增加處理空資料的情況
function updateHistory(history) {
    const tbody = document.getElementById('sessionHistory');
    tbody.innerHTML = '';
    
    if (!history || history.length === 0) {
        // 如果沒有資料，顯示一個空行提示並清空平均值
        const emptyRow = document.createElement('tr');
        emptyRow.innerHTML = `
            <td colspan="5" class="text-center text-gray-500 py-4">
                暫無歷史記錄
            </td>
        `;
        tbody.appendChild(emptyRow);
        
        // 清空平均值顯示
        document.getElementById('averageRtt').textContent = '0.00 ms';
        return;
    }
    
    // 計算歷史平均值
    const totalRtt = history.reduce((sum, session) => sum + session.total_rtt, 0);
    const averageRtt = totalRtt / history.length;
    
    // 更新平均 RTT 顯示
    document.getElementById('averageRtt').innerHTML = `${averageRtt.toFixed(2)} ms<br> / ${history.length} sessions`;    
    // 原有的歷史記錄顯示邏輯
    const reversedHistory = [...history].reverse();
    reversedHistory.forEach((session, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${history.length - index}</td>
            <td>${session.date}</td>
            <td>${session.total_rtt.toFixed(2)} ms</td>
            <td>${session.total_packets}</td>
            <td>${(session.packet_loss_rate * 100).toFixed(2)}%</td>
        `;
        tbody.appendChild(row);
    });
}

function updateUI(stats) {
    updateStatus(stats);
    updateTimeline(stats);
}

function updateStatus(stats) {
    // 確保安全地讀取和顯示數值
    const safeGetNumber = (obj, ...path) => {
        let current = obj;
        for (const key of path) {
            if (current == null || typeof current !== 'object') return 0;
            current = current[key];
        }
        return typeof current === 'number' ? current : 0;
    };

    // Update Compression Stats
    document.getElementById('originalSize').textContent = 
        (safeGetNumber(stats, 'compression', 'original_size') / 1024).toFixed(2);
    document.getElementById('compressedSize').textContent = 
        (safeGetNumber(stats, 'compression', 'compressed_size') / 1024).toFixed(2);
    document.getElementById('compressionRatio').textContent = 
        `${safeGetNumber(stats, 'compression', 'ratio').toFixed(1)}%`;

    // Update Transmission Stats
    document.getElementById('currentRun').textContent = 
        safeGetNumber(stats, 'transmission', 'current_run');
    document.getElementById('totalRuns').textContent = 
        safeGetNumber(stats, 'transmission', 'total_runs');
    document.getElementById('status').textContent = 
        stats?.transmission?.status || 'idle';

    // Update Performance Metrics
    document.getElementById('totalRtt').textContent = 
        `${safeGetNumber(stats, 'performance', 'total_rtt').toFixed(2)} ms`;
    document.getElementById('currentThroughput').textContent = 
        `${safeGetNumber(stats, 'performance', 'average_throughput').toFixed(2)} KB/s`;
    document.getElementById('packetLossRate').textContent = 
        `${(safeGetNumber(stats, 'performance', 'total_packet_loss_rate')*100).toFixed(2)}%`;

    // Update Path Statistics
    const path1 = stats?.paths?.path1 || { packets: 0, success: 0 };
    const path2 = stats?.paths?.path2 || { packets: 0, success: 0 };

    const path1SuccessRate = path1.packets > 0 ? (path1.success / path1.packets * 100).toFixed(1) : '0.0';
    const path2SuccessRate = path2.packets > 0 ? (path2.success / path2.packets * 100).toFixed(1) : '0.0';

    document.getElementById('path1Stats').textContent = 
        `${path1.success}/${path1.packets} packets (${path1SuccessRate}%)`;
    document.getElementById('path1Progress').style.width = `${path1SuccessRate}%`;

    document.getElementById('path2Stats').textContent = 
        `${path2.success}/${path2.packets} packets (${path2SuccessRate}%)`;
    document.getElementById('path2Progress').style.width = `${path2SuccessRate}%`;

    // Handle transmission status
    if (stats?.transmission?.status) {
        switch (stats.transmission.status) {
            case 'idle':
                isTransmitting = false;
                toggleBtn.textContent = 'Start Transmission';
                toggleBtn.classList.remove('active');
                stopPeriodicUpdates();
                break;
                
            case 'running':
                isTransmitting = true;
                toggleBtn.textContent = 'Stop Transmission';
                toggleBtn.classList.add('active');
                if (!updateInterval) {
                    startPeriodicUpdates();
                }
                break;
            case 'completed':
                if (window.packetTimelineChart && typeof window.packetTimelineChart.destroy === 'function') {
                    window.packetTimelineChart.destroy();
                    window.packetTimelineChart = null;
                }
                break;
            default:
                console.warn('Unknown transmission status:', stats.transmission.status);
        }
    }
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

// 檔案大小格式化函數
function formatFileSize(bytes) {
    console.log(bytes);
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

// 時間格式化函數
function formatDate(date) {
    return new Date(date).toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}


function updateTimeline(stats) {
    const ctx = document.getElementById('packetTimelineChart').getContext('2d');

    // 前面的資料準備部分保持不變
    const sortedPackets = [...stats.packets].sort((a, b) => a.timestamp - b.timestamp);

    const path1Data = sortedPackets
        .filter(packet => packet.path === 'path1')
        .map(packet => ({
            x: packet.timestamp,
            y: 1,
            seqNum: packet.sequence
        }));
    
    const path2Data = sortedPackets
        .filter(packet => packet.path === 'path2')
        .map(packet => ({
            x: packet.timestamp,
            y: 1.005,
            seqNum: packet.sequence
        }));
    
    const ackData = sortedPackets
        .filter(packet => packet.type === 'acked')
        .map(packet => ({
            x: packet.timestamp,
            y: 0.995,
            seqNum: packet.sequence
        }));

    // 圖表更新邏輯保持不變
    if (window.packetTimelineChart && window.packetTimelineChart.data && window.packetTimelineChart.data.datasets) {
        window.packetTimelineChart.data.datasets[0].data = path1Data;
        window.packetTimelineChart.data.datasets[1].data = path2Data;
        window.packetTimelineChart.data.datasets[2].data = ackData;
        window.packetTimelineChart.update();
    } else {
        let pointRadiussize = 26;
        let pointHoverRadiussize = 24;
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
                pointHoverRadius: pointHoverRadiussize,
                showLine: false
                },
                {
                label: 'Path 2',
                data: path2Data,
                backgroundColor: 'rgba(153, 102, 255, 0.8)',
                pointStyle: 'rectRounded',
                pointRadius: pointRadiussize,
                pointHoverRadius: pointHoverRadiussize,
                showLine: false
                },
                {
                label: 'ACKs',
                data: ackData,
                backgroundColor: 'rgba(255, 159, 64, 0.8)',
                pointStyle: 'rectRounded',
                pointRadius: pointRadiussize,
                pointHoverRadius: pointHoverRadiussize,
                showLine: false
                }
            ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 10,
                        right: 20,
                        bottom: 10,
                        left: 20
                    }
                },
                animation: {
                    duration: 300,
                    easing: 'easeOutQuart'
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Packet Timeline'
                    },
                    tooltip: {
                        enabled: true, // 確保啟用 tooltip
                        mode: 'point', // 設定為點模式
                        callbacks: {
                            label: function(context) {
                                try {
                                    const point = context.raw;
                                    if (!point) return null;
                    
                                    const time = (point.x % 1000).toFixed(3);
                                    
                                    // 安全地查找封包
                                    const packet = sortedPackets.find(p => 
                                        p.sequence === point.seqNum && 
                                        ((context.datasetIndex === 0 && p.path === 'path1') ||
                                        (context.datasetIndex === 1 && p.path === 'path2') ||
                                        (context.datasetIndex === 2 && p.type === 'acked'))
                                    );
                                    
                                    if (!packet) return [`序號: ${point.seqNum}`, `時間: ${time}`];
                                    
                                    const size = packet.size ? formatFileSize(packet.size) : 'N/A';
                                    
                                    return [
                                        `序號: ${point.seqNum}`,
                                        `時間: ${time}`,
                                        `大小: ${size}`
                                    ];
                                } catch (error) {
                                    console.error('Tooltip error:', error);
                                    return ['資料載入錯誤'];
                                }
                            }
                        }
                    },
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Timestamp'
                        },
                        min: sortedPackets[0].timestamp - 0.1,
                        // max: sortedPackets[0].timestamp + 2.5
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Path'
                        },
                        min: 0.989,
                        max: 1.011,
                        ticks: {
                            callback: function(value) {
                            if (value === 1) return 'Path 1';
                            if (value === 1.005) return 'Path 2';
                            if (value === 0.995) return 'ACKs';
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

// 修改 DOMContentLoaded 事件處理函式
document.addEventListener('DOMContentLoaded', () => {
    // 初始化其他 UI 元素
    toggleBtn = document.getElementById('toggleBtn');
    statusText = document.getElementById('statusText');
    timeline = document.getElementById('packetTimeline');

    // 新增清除歷史按鈕事件監聽
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        // 修改清除歷史按鈕的事件處理
        clearHistoryBtn.addEventListener('click', async () => {
            if (confirm('確定要清除所有歷史紀錄嗎？')) {
                try {
                    const response = await fetch('/api/history/clear', {
                        method: 'POST'
                    });
                    if (response.ok) {
                        // 直接更新為空列表，不需等待 fetchStats
                        updateHistory([]);
                        alert('歷史紀錄已清除');
                    }
                } catch (error) {
                    console.error('Failed to clear history:', error);
                    alert('清除失敗');
                }
            }
        });
    }

    // 主要按鈕事件監聽
    toggleBtn.addEventListener('click', async () => {
        if (!isTransmitting) {
            if (window.packetTimelineChart && typeof window.packetTimelineChart.destroy === 'function') {
                window.packetTimelineChart.destroy();
                window.packetTimelineChart = null;
            }
            await startTransmission();
        } else {
            await stopTransmission();
        }
    });

    // 主題切換相關
    const themeToggle = document.getElementById('theme-toggle');
    const savedTheme = localStorage.getItem('theme') || 'system';
    applyTheme(savedTheme);
    
    themeToggle.addEventListener('click', () => {
        const currentTheme = localStorage.getItem('theme') || 'system';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    });

    // 可選的初始資料載入
    // fetchStats();
    // 建立初始資料載入函式
    async function loadInitialData() {
        try {
            const [historyResponse, statsResponse] = await Promise.all([
                fetch('/api/history'),
                fetch('/api/stats')
            ]);

            if (historyResponse.ok) {
                const history = await historyResponse.json();
                updateHistory(history);
            } else {
                console.error('Failed to load initial history');
            }
            
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                updateUI(stats);
            }
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    // 呼叫初始資料載入函式
    loadInitialData();
});
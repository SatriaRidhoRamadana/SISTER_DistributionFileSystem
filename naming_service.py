"""
Distributed File System - Naming Service (Database Version)
Mengelola metadata file dan koordinasi antar storage nodes
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import uuid
import threading
import time
from datetime import datetime
import requests
import sys
import os

# Import database and replication manager
sys.path.append(os.path.dirname(__file__))
from database_schema import DFSDatabase
from replication_manager import ReplicationManager, HealthMonitor, RecoveryManager
from advanced_recovery import AdvancedRecoveryManager

app = Flask(__name__)
CORS(app)

# Initialize database
db = DFSDatabase("dfs.db")

# Initialize replication managers
replication_mgr = ReplicationManager(db, min_replicas=2)
health_monitor = HealthMonitor(db)
recovery_mgr = RecoveryManager(db, replication_mgr)
advanced_recovery = AdvancedRecoveryManager(db, replication_mgr)

class NamingService:
    def __init__(self):
        self.lock = threading.Lock()
    
    def select_nodes_for_upload(self, replication_factor=2):
        """Pilih node untuk upload file"""
        active_nodes = db.get_active_nodes()
        
        if len(active_nodes) < replication_factor:
            return None
        
        # Return top N nodes berdasarkan available space
        return active_nodes[:replication_factor]

naming_service = NamingService()

# === API Endpoints ===

@app.route('/')
def index():
    """Web UI Dashboard"""
    return render_template_string(WEB_UI_TEMPLATE)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "naming-service",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/nodes/register', methods=['POST'])
def register_node():
    """Register storage node"""
    data = request.json
    node_id = data.get('node_id')
    node_address = data.get('node_address')
    
    if not node_id or not node_address:
        return jsonify({"error": "node_id dan node_address required"}), 400
    
    db.register_node(node_id, node_address)
    
    return jsonify({
        "status": "success",
        "message": f"Node {node_id} registered"
    })

@app.route('/api/nodes/heartbeat', methods=['POST'])
def heartbeat():
    """Heartbeat dari storage node"""
    data = request.json
    node_id = data.get('node_id')
    available_space = data.get('available_space', 0)
    file_count = data.get('file_count', 0)
    
    if not node_id:
        return jsonify({"error": "node_id required"}), 400
    
    success = db.update_node_heartbeat(node_id, available_space, file_count)
    
    if success:
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": "Node not found"}), 404

@app.route('/api/nodes', methods=['GET'])
def list_nodes():
    """List semua storage nodes"""
    nodes = db.get_all_nodes()
    return jsonify({"nodes": nodes})

@app.route('/api/upload/request', methods=['POST'])
def upload_request():
    """Request untuk upload file"""
    data = request.json
    filename = data.get('filename')
    file_size = data.get('file_size')
    replication_factor = data.get('replication_factor', 2)
    
    if not filename or not file_size:
        return jsonify({"error": "filename dan file_size required"}), 400
    
    # Pilih nodes untuk upload
    selected_nodes = naming_service.select_nodes_for_upload(replication_factor)
    
    if not selected_nodes:
        return jsonify({
            "error": "Tidak cukup storage nodes aktif",
            "required": replication_factor,
            "available": len(db.get_active_nodes())
        }), 503
    
    # Buat file record
    file_id = str(uuid.uuid4())
    db.create_file(file_id, filename, file_size, replication_factor)
    
    # Buat replica records
    upload_nodes = []
    for node in selected_nodes:
        db.add_replica(file_id, node["node_id"], node["node_address"])
        upload_nodes.append({
            "node_id": node["node_id"],
            "upload_url": f"{node['node_address']}/upload/{file_id}"
        })
    
    return jsonify({
        "status": "success",
        "file_id": file_id,
        "upload_nodes": upload_nodes
    })

@app.route('/api/upload/confirm', methods=['POST'])
def upload_confirm():
    """Konfirmasi upload berhasil"""
    data = request.json
    file_id = data.get('file_id')
    node_id = data.get('node_id')
    checksum = data.get('checksum')
    
    if not all([file_id, node_id, checksum]):
        return jsonify({"error": "file_id, node_id, checksum required"}), 400
    
    # Update replica status
    db.update_replica_status(file_id, node_id, 'active')
    
    # Update file checksum if not set
    file_info = db.get_file(file_id)
    if file_info and not file_info['checksum']:
        db.update_file_checksum(file_id, checksum)
    
    return jsonify({"status": "success"})

@app.route('/api/download/<file_id>', methods=['GET'])
def download_request(file_id):
    """Request untuk download file"""
    file_info = db.get_file(file_id)
    
    if not file_info:
        return jsonify({"error": "File tidak ditemukan"}), 404
    
    # Get active replicas
    active_replicas = [
        replica for replica in file_info["replicas"]
        if replica["status"] == "active"
    ]
    
    if not active_replicas:
        return jsonify({"error": "Tidak ada replica aktif"}), 503
    
    download_urls = [
        f"{replica['node_address']}/download/{file_id}"
        for replica in active_replicas
    ]
    
    return jsonify({
        "file_id": file_id,
        "filename": file_info["filename"],
        "file_size": file_info["file_size"],
        "checksum": file_info["checksum"],
        "download_urls": download_urls
    })

@app.route('/api/files', methods=['GET'])
def list_files():
    """List semua file dengan pagination"""
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    result = db.list_files(limit, offset)
    return jsonify(result)

@app.route('/api/files/<file_id>', methods=['GET'])
def get_file(file_id):
    """Get file detail"""
    file_info = db.get_file(file_id)
    
    if not file_info:
        return jsonify({"error": "File tidak ditemukan"}), 404
    
    return jsonify(file_info)

@app.route('/api/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete file"""
    file_info = db.get_file(file_id)
    
    if not file_info:
        return jsonify({"error": "File tidak ditemukan"}), 404
    
    # Kirim delete request ke semua replicas
    for replica in file_info["replicas"]:
        try:
            requests.delete(
                f"{replica['node_address']}/delete/{file_id}",
                timeout=5
            )
        except:
            pass
    
    # Hapus dari database
    db.delete_file(file_id)
    
    return jsonify({"status": "success"})

@app.route('/api/stats', methods=['GET'])
def stats():
    """Statistik sistem"""
    stats = db.get_stats()
    
    # Add replication stats
    replication_stats = replication_mgr.get_stats()
    health_stats = health_monitor.get_stats()
    recovery_stats = recovery_mgr.get_stats()
    
    return jsonify({
        "total_nodes": stats['total_nodes'],
        "active_nodes": stats['active_nodes'],
        "total_files": stats['total_files'],
        "total_size_bytes": stats['total_size'],
        "total_size_mb": round(stats['total_size'] / (1024 * 1024), 2),
        "recent_uploads": stats['recent_uploads'],
        "replication": {
            "replications_performed": replication_stats['replications_performed'],
            "verifications_performed": replication_stats['verifications_performed'],
            "under_replicated_files": replication_stats['under_replicated_files'],
            "last_check": replication_stats['last_check'],
            "last_verification": replication_stats['last_verification']
        },
        "health": {
            "checks_performed": health_stats['checks_performed'],
            "nodes_failed": health_stats['nodes_failed'],
            "nodes_recovered": health_stats['nodes_recovered'],
            "last_check": health_stats['last_check']
        },
        "recovery": {
            "recovery_attempts": recovery_stats['recovery_attempts'],
            "last_recovery": recovery_stats['last_recovery']
        }
    })

@app.route('/api/history', methods=['GET'])
def history():
    """Upload history"""
    limit = int(request.args.get('limit', 50))
    history = db.get_upload_history(limit)
    return jsonify({"history": history})

@app.route('/api/replication/force', methods=['POST'])
def force_replication():
    """Force immediate replication check"""
    replication_mgr.force_check()
    return jsonify({"status": "success", "message": "Replication check triggered"})

@app.route('/api/replication/verify', methods=['POST'])
def force_verification():
    """Force immediate verification"""
    replication_mgr.force_verification()
    return jsonify({"status": "success", "message": "Verification triggered"})

@app.route('/api/system/status', methods=['GET'])
def system_status():
    """Get detailed system status"""
    return jsonify({
        "replication_manager": {
            "running": replication_mgr.running,
            "stats": replication_mgr.get_stats()
        },
        "health_monitor": {
            "running": health_monitor.running,
            "stats": health_monitor.get_stats()
        },
        "recovery_manager": {
            "running": recovery_mgr.running,
            "stats": recovery_mgr.get_stats()
        },
        "advanced_recovery": {
            "running": advanced_recovery.running,
            "stats": advanced_recovery.get_stats()
        }
    })

@app.route('/api/recovery/queue', methods=['GET'])
def recovery_queue():
    """Get recovery queue"""
    queue = advanced_recovery.get_recovery_queue()
    return jsonify({"queue": queue, "total": len(queue)})

@app.route('/api/recovery/history', methods=['GET'])
def recovery_history():
    """Get recovery history"""
    limit = int(request.args.get('limit', 50))
    history = advanced_recovery.get_recovery_history(limit)
    return jsonify({"history": history, "total": len(history)})

@app.route('/api/recovery/force/<file_id>', methods=['POST'])
def force_recovery(file_id):
    """Force recovery for specific file"""
    success = advanced_recovery.force_recovery(file_id)
    
    if success:
        return jsonify({"status": "success", "message": "Recovery queued"})
    else:
        return jsonify({"error": "File not found"}), 404

@app.route('/api/recovery/stats', methods=['GET'])
def recovery_stats():
    """Get detailed recovery statistics"""
    stats = advanced_recovery.get_stats()
    queue = advanced_recovery.get_recovery_queue()
    history = advanced_recovery.get_recovery_history(10)
    
    return jsonify({
        "stats": stats,
        "queue_summary": {
            "total": len(queue),
            "critical": sum(1 for q in queue if q['priority'] >= 15),
            "high": sum(1 for q in queue if 10 <= q['priority'] < 15),
            "normal": sum(1 for q in queue if q['priority'] < 10)
        },
        "recent_history": history
    })

def health_check_loop():
    """Background thread untuk cek health nodes"""
    while True:
        time.sleep(10)
        
        # Get active nodes akan otomatis mark inactive nodes
        db.get_active_nodes()

# Web UI Template
WEB_UI_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DFS - Distributed File System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-card .number {
            font-size: 3em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        .stat-card .label {
            color: #666;
            font-size: 1.1em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .content-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .panel {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .panel h2 {
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
        .upload-form {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .form-group label {
            font-weight: 600;
            color: #333;
        }
        .form-group input[type="file"],
        .form-group input[type="number"] {
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
        }
        .btn {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .btn:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .file-list, .node-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .file-item, .node-item {
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 10px;
            transition: all 0.3s ease;
        }
        .file-item:hover, .node-item:hover {
            background: #f8f9ff;
            border-color: #667eea;
        }
        .file-item h3, .node-item h3 {
            color: #333;
            font-size: 1.1em;
            margin-bottom: 8px;
        }
        .file-item p, .node-item p {
            color: #666;
            font-size: 0.9em;
            margin: 4px 0;
        }
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .status.active {
            background: #d4edda;
            color: #155724;
        }
        .status.inactive {
            background: #f8d7da;
            color: #721c24;
        }
        .file-actions {
            margin-top: 10px;
            display: flex;
            gap: 10px;
        }
        .btn-small {
            padding: 8px 16px;
            font-size: 0.9em;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .btn-small:hover {
            background: #5568d3;
        }
        .btn-small.danger {
            background: #dc3545;
        }
        .btn-small.danger:hover {
            background: #c82333;
        }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .alert.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .progress {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 15px 0;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }
        @media (max-width: 768px) {
            .content-grid {
                grid-template-columns: 1fr;
            }
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗄️ Distributed File System</h1>
            <p>Manage your distributed file storage with ease</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total Files</div>
                <div class="number" id="totalFiles">0</div>
            </div>
            <div class="stat-card">
                <div class="label">Active Nodes</div>
                <div class="number" id="activeNodes">0</div>
            </div>
            <div class="stat-card">
                <div class="label">Total Storage</div>
                <div class="number" id="totalStorage">0 MB</div>
            </div>
            <div class="stat-card">
                <div class="label">Auto Replications</div>
                <div class="number" id="replications">0</div>
            </div>
        </div>

        <div class="panel" style="margin-bottom: 20px;">
            <h2>🔄 Replication & Recovery Status</h2>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                <div style="padding: 15px; background: #f8f9ff; border-radius: 8px;">
                    <h3 style="margin-bottom: 10px; color: #667eea;">Replication</h3>
                    <p>Status: <span id="repStatus" class="status active">Running</span></p>
                    <p>Replications: <span id="repCount">0</span></p>
                    <p>Verifications: <span id="repVerify">0</span></p>
                    <p>Under-replicated: <span id="repUnder">0</span></p>
                </div>
                <div style="padding: 15px; background: #f8f9ff; border-radius: 8px;">
                    <h3 style="margin-bottom: 10px; color: #667eea;">Health Monitor</h3>
                    <p>Status: <span id="healthStatus" class="status active">Running</span></p>
                    <p>Checks: <span id="healthChecks">0</span></p>
                    <p>Failed: <span id="healthFailed">0</span></p>
                    <p>Recovered: <span id="healthRecovered">0</span></p>
                </div>
                <div style="padding: 15px; background: #f8f9ff; border-radius: 8px;">
                    <h3 style="margin-bottom: 10px; color: #667eea;">Recovery</h3>
                    <p>Status: <span id="advRecoveryStatus" class="status active">Running</span></p>
                    <p>Success: <span id="advRecoverySuccess">0</span></p>
                    <p>Failed: <span id="advRecoveryFailed">0</span></p>
                    <p>Success Rate: <span id="advRecoveryRate">0%</span></p>
                </div>
                <div style="padding: 15px; background: #f8f9ff; border-radius: 8px;">
                    <h3 style="margin-bottom: 10px; color: #667eea;">Recovery Queue</h3>
                    <p>Pending: <span id="queuePending">0</span></p>
                    <p>Critical: <span id="queueCritical">0</span></p>
                    <p>High: <span id="queueHigh">0</span></p>
                    <button class="btn-small" onclick="showRecoveryDetails()" style="margin-top: 5px;">View Details</button>
                </div>
            </div>
        </div>

        <div class="content-grid">
            <div class="panel">
                <h2>📤 Upload File</h2>
                <div id="uploadAlert"></div>
                <form class="upload-form" id="uploadForm">
                    <div class="form-group">
                        <label>Select File</label>
                        <input type="file" id="fileInput" required>
                    </div>
                    <div class="form-group">
                        <label>Replication Factor</label>
                        <input type="number" id="replicationFactor" min="2" max="5" value="2">
                    </div>
                    <div id="uploadProgress" style="display: none;">
                        <div class="progress">
                            <div class="progress-bar" id="progressBar">0%</div>
                        </div>
                    </div>
                    <button type="submit" class="btn" id="uploadBtn">Upload File</button>
                </form>
            </div>

            <div class="panel">
                <h2>🗄️ Storage Nodes</h2>
                <div class="node-list" id="nodeList">
                    <p style="text-align: center; color: #999;">Loading...</p>
                </div>
            </div>
        </div>

        <div class="panel" style="margin-top: 20px;">
            <h2>📂 Files</h2>
            <div class="file-list" id="fileList">
                <p style="text-align: center; color: #999;">Loading...</p>
            </div>
        </div>

        <!-- Recovery Details Modal -->
        <div id="recoveryModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000;">
            <div style="position: relative; max-width: 800px; margin: 50px auto; background: white; border-radius: 15px; padding: 30px; max-height: 80vh; overflow-y: auto;">
                <h2 style="margin-bottom: 20px;">🔧 Recovery System Details</h2>
                
                <div style="margin-bottom: 20px;">
                    <h3>📊 Statistics</h3>
                    <div id="recoveryStatsDetail" style="padding: 15px; background: #f8f9ff; border-radius: 8px;"></div>
                </div>

                <div style="margin-bottom: 20px;">
                    <h3>📋 Recovery Queue</h3>
                    <div id="recoveryQueueDetail" style="max-height: 200px; overflow-y: auto;"></div>
                </div>

                <div style="margin-bottom: 20px;">
                    <h3>📜 Recent History</h3>
                    <div id="recoveryHistoryDetail" style="max-height: 200px; overflow-y: auto;"></div>
                </div>

                <button class="btn" onclick="closeRecoveryDetails()" style="width: 100%;">Close</button>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin;

        // Load stats
        async function loadStats() {
            try {
                const res = await fetch(`${API_BASE}/api/stats`);
                const data = await res.json();
                
                document.getElementById('totalFiles').textContent = data.total_files;
                document.getElementById('activeNodes').textContent = data.active_nodes;
                document.getElementById('totalStorage').textContent = data.total_size_mb + ' MB';
                document.getElementById('replications').textContent = data.replication?.replications_performed || 0;
                
                // Update replication stats
                if (data.replication) {
                    document.getElementById('repCount').textContent = data.replication.replications_performed;
                    document.getElementById('repVerify').textContent = data.replication.verifications_performed;
                    document.getElementById('repUnder').textContent = data.replication.under_replicated_files;
                }
                
                // Update health stats
                if (data.health) {
                    document.getElementById('healthChecks').textContent = data.health.checks_performed;
                    document.getElementById('healthFailed').textContent = data.health.nodes_failed;
                    document.getElementById('healthRecovered').textContent = data.health.nodes_recovered;
                }
                
                // Update recovery stats
                if (data.recovery) {
                    document.getElementById('recoveryAttempts').textContent = data.recovery.recovery_attempts;
                }
                
                // Update advanced recovery stats
                loadAdvancedRecoveryStats();
            } catch (err) {
                console.error('Error loading stats:', err);
            }
        }

        // Load advanced recovery stats
        async function loadAdvancedRecoveryStats() {
            try {
                const res = await fetch(`${API_BASE}/api/recovery/stats`);
                const data = await res.json();
                
                if (data.stats) {
                    document.getElementById('advRecoverySuccess').textContent = data.stats.successful_recoveries;
                    document.getElementById('advRecoveryFailed').textContent = data.stats.failed_recoveries;
                    document.getElementById('advRecoveryRate').textContent = data.stats.success_rate.toFixed(1) + '%';
                }
                
                if (data.queue_summary) {
                    document.getElementById('queuePending').textContent = data.queue_summary.total;
                    document.getElementById('queueCritical').textContent = data.queue_summary.critical;
                    document.getElementById('queueHigh').textContent = data.queue_summary.high;
                }
            } catch (err) {
                console.error('Error loading recovery stats:', err);
            }
        }

        // Load nodes
        async function loadNodes() {
            try {
                const res = await fetch(`${API_BASE}/api/nodes`);
                const data = await res.json();
                
                const nodeList = document.getElementById('nodeList');
                
                if (data.nodes.length === 0) {
                    nodeList.innerHTML = '<p style="text-align: center; color: #999;">No nodes registered</p>';
                    return;
                }
                
                nodeList.innerHTML = data.nodes.map(node => `
                    <div class="node-item">
                        <h3>${node.node_id}</h3>
                        <p>Address: ${node.node_address}</p>
                        <p>Status: <span class="status ${node.status}">${node.status}</span></p>
                        <p>Files: ${node.total_files} | Space: ${(node.available_space / (1024**3)).toFixed(2)} GB</p>
                        <p style="font-size: 0.8em; color: #999;">Last seen: ${new Date(node.last_heartbeat).toLocaleString()}</p>
                    </div>
                `).join('');
            } catch (err) {
                console.error('Error loading nodes:', err);
            }
        }

        // Load files
        async function loadFiles() {
            try {
                const res = await fetch(`${API_BASE}/api/files`);
                const data = await res.json();
                
                const fileList = document.getElementById('fileList');
                
                if (data.files.length === 0) {
                    fileList.innerHTML = '<p style="text-align: center; color: #999;">No files uploaded</p>';
                    return;
                }
                
                fileList.innerHTML = data.files.map(file => `
                    <div class="file-item">
                        <h3>${file.filename}</h3>
                        <p>File ID: ${file.file_id}</p>
                        <p>Size: ${(file.file_size / (1024**2)).toFixed(2)} MB | Replicas: ${file.active_replicas}/${file.replica_count}</p>
                        <p style="font-size: 0.8em; color: #999;">Uploaded: ${new Date(file.upload_timestamp).toLocaleString()}</p>
                        <div class="file-actions">
                            <button class="btn-small" onclick="downloadFile('${file.file_id}')">Download</button>
                            <button class="btn-small danger" onclick="deleteFile('${file.file_id}')">Delete</button>
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                console.error('Error loading files:', err);
            }
        }

        // Upload file
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const fileInput = document.getElementById('fileInput');
            const replicationFactor = document.getElementById('replicationFactor').value;
            const file = fileInput.files[0];
            
            if (!file) return;
            
            const uploadBtn = document.getElementById('uploadBtn');
            const uploadProgress = document.getElementById('uploadProgress');
            const progressBar = document.getElementById('progressBar');
            const uploadAlert = document.getElementById('uploadAlert');
            
            uploadBtn.disabled = true;
            uploadProgress.style.display = 'block';
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
            uploadAlert.innerHTML = '';
            
            try {
                // Step 1: Request upload
                progressBar.style.width = '20%';
                progressBar.textContent = '20%';
                
                const reqRes = await fetch(`${API_BASE}/api/upload/request`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        filename: file.name,
                        file_size: file.size,
                        replication_factor: parseInt(replicationFactor)
                    })
                });
                
                if (!reqRes.ok) {
                    throw new Error('Upload request failed');
                }
                
                const reqData = await reqRes.json();
                
                // Step 2: Upload to nodes
                progressBar.style.width = '50%';
                progressBar.textContent = '50%';
                
                const uploadPromises = reqData.upload_nodes.map(node => {
                    const formData = new FormData();
                    formData.append('file', file);
                    return fetch(node.upload_url, {
                        method: 'POST',
                        body: formData
                    });
                });
                
                await Promise.all(uploadPromises);
                
                progressBar.style.width = '100%';
                progressBar.textContent = '100%';
                
                uploadAlert.innerHTML = '<div class="alert success">✅ File uploaded successfully!</div>';
                
                // Reset form
                fileInput.value = '';
                
                // Refresh data
                loadStats();
                loadFiles();
                
            } catch (err) {
                uploadAlert.innerHTML = `<div class="alert error">❌ Upload failed: ${err.message}</div>`;
            } finally {
                uploadBtn.disabled = false;
                setTimeout(() => {
                    uploadProgress.style.display = 'none';
                }, 2000);
            }
        });

        // Download file
        async function downloadFile(fileId) {
            try {
                const res = await fetch(`${API_BASE}/api/download/${fileId}`);
                const data = await res.json();
                
                if (data.download_urls && data.download_urls.length > 0) {
                    window.open(data.download_urls[0], '_blank');
                }
            } catch (err) {
                alert('Download failed: ' + err.message);
            }
        }

        // Delete file
        async function deleteFile(fileId) {
            if (!confirm('Are you sure you want to delete this file?')) return;
            
            try {
                const res = await fetch(`${API_BASE}/api/files/${fileId}`, {
                    method: 'DELETE'
                });
                
                if (res.ok) {
                    alert('File deleted successfully!');
                    loadStats();
                    loadFiles();
                } else {
                    alert('Failed to delete file');
                }
            } catch (err) {
                alert('Delete failed: ' + err.message);
            }
        }

        // Force replication check
        async function forceReplication() {
            try {
                const res = await fetch(`${API_BASE}/api/replication/force`, {
                    method: 'POST'
                });
                
                if (res.ok) {
                    alert('Replication check triggered! Check logs for results.');
                    setTimeout(loadStats, 2000);
                } else {
                    alert('Failed to trigger replication');
                }
            } catch (err) {
                alert('Error: ' + err.message);
            }
        }

        // Show recovery details modal
        async function showRecoveryDetails() {
            try {
                const res = await fetch(`${API_BASE}/api/recovery/stats`);
                const data = await res.json();
                
                // Update stats
                let statsHTML = `
                    <p><strong>Total Recoveries:</strong> ${data.stats.total_recoveries}</p>
                    <p><strong>Successful:</strong> ${data.stats.successful_recoveries}</p>
                    <p><strong>Failed:</strong> ${data.stats.failed_recoveries}</p>
                    <p><strong>Success Rate:</strong> ${data.stats.success_rate.toFixed(1)}%</p>
                    <p><strong>Average Recovery Time:</strong> ${data.stats.average_recovery_time.toFixed(2)}s</p>
                    <p><strong>Critical Files Recovered:</strong> ${data.stats.critical_files_recovered}</p>
                `;
                document.getElementById('recoveryStatsDetail').innerHTML = statsHTML;
                
                // Update queue
                const queueRes = await fetch(`${API_BASE}/api/recovery/queue`);
                const queueData = await queueRes.json();
                
                if (queueData.queue.length === 0) {
                    document.getElementById('recoveryQueueDetail').innerHTML = '<p style="color: #999; text-align: center;">Queue is empty</p>';
                } else {
                    let queueHTML = '<table style="width: 100%; border-collapse: collapse;">';
                    queueHTML += '<tr style="background: #f0f0f0;"><th>File</th><th>Priority</th><th>Attempts</th><th>Status</th></tr>';
                    
                    queueData.queue.forEach(item => {
                        queueHTML += `<tr style="border-bottom: 1px solid #e0e0e0;">
                            <td>${item.filename}</td>
                            <td>${item.priority}</td>
                            <td>${item.attempts}</td>
                            <td>${item.status}</td>
                        </tr>`;
                    });
                    
                    queueHTML += '</table>';
                    document.getElementById('recoveryQueueDetail').innerHTML = queueHTML;
                }
                
                // Update history
                if (data.recent_history && data.recent_history.length > 0) {
                    let historyHTML = '<table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">';
                    historyHTML += '<tr style="background: #f0f0f0;"><th>Time</th><th>File</th><th>Result</th><th>Time</th></tr>';
                    
                    data.recent_history.reverse().forEach(item => {
                        const time = new Date(item.timestamp).toLocaleTimeString();
                        const result = item.success ? '✅' : '❌';
                        historyHTML += `<tr style="border-bottom: 1px solid #e0e0e0;">
                            <td>${time}</td>
                            <td>${item.filename}</td>
                            <td>${result}</td>
                            <td>${item.recovery_time.toFixed(2)}s</td>
                        </tr>`;
                    });
                    
                    historyHTML += '</table>';
                    document.getElementById('recoveryHistoryDetail').innerHTML = historyHTML;
                } else {
                    document.getElementById('recoveryHistoryDetail').innerHTML = '<p style="color: #999; text-align: center;">No recent history</p>';
                }
                
                // Show modal
                document.getElementById('recoveryModal').style.display = 'block';
                
            } catch (err) {
                alert('Error loading recovery details: ' + err.message);
            }
        }

        // Close recovery details modal
        function closeRecoveryDetails() {
            document.getElementById('recoveryModal').style.display = 'none';
        }

        // Auto refresh every 5 seconds
        setInterval(() => {
            loadStats();
            loadNodes();
            loadFiles();
        }, 5000);

        // Initial load
        loadStats();
        loadNodes();
        loadFiles();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    # Start health check thread
    health_thread = threading.Thread(target=health_check_loop, daemon=True)
    health_thread.start()
    
    print("=" * 60)
    print("🚀 Distributed File System - Naming Service (Database)")
    print("=" * 60)
    print("📍 Server running on: http://localhost:5000")
    print("🌐 Web UI: http://localhost:5000")
    print("📊 API Endpoints:")
    print("   - POST /api/nodes/register")
    print("   - POST /api/nodes/heartbeat")
    print("   - POST /api/upload/request")
    print("   - GET  /api/download/<file_id>")
    print("   - GET  /api/files")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
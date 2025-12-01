"""
Distributed File System - Replication Manager
Handles automatic replication, verification, and recovery
"""

import threading
import time
import requests
from datetime import datetime
import logging
from database_schema import DFSDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReplicationManager:
    def __init__(self, db, min_replicas=2):
        self.db = db
        self.min_replicas = min_replicas
        self.running = False
        self.check_interval = 30  # Check every 30 seconds
        self.verification_interval = 300  # Verify every 5 minutes
        
        # Statistics
        self.stats = {
            'replications_performed': 0,
            'verifications_performed': 0,
            'recoveries_performed': 0,
            'failed_nodes_detected': 0,
            'last_check': None,
            'last_verification': None,
            'under_replicated_files': 0
        }
    
    def start(self):
        """Start replication manager background threads"""
        self.running = True
        
        # Thread for checking under-replicated files
        self.replication_thread = threading.Thread(
            target=self._replication_loop,
            daemon=True
        )
        self.replication_thread.start()
        logger.info("✅ Replication Manager started")
        
        # Thread for verification
        self.verification_thread = threading.Thread(
            target=self._verification_loop,
            daemon=True
        )
        self.verification_thread.start()
        logger.info("✅ Verification Manager started")
    
    def stop(self):
        """Stop replication manager"""
        self.running = False
        logger.info("🛑 Replication Manager stopped")
    
    def _replication_loop(self):
        """Main loop for checking and fixing under-replicated files"""
        while self.running:
            try:
                self._check_and_replicate()
                self.stats['last_check'] = datetime.now().isoformat()
            except Exception as e:
                logger.error(f"Error in replication loop: {e}")
            
            time.sleep(self.check_interval)
    
    def _verification_loop(self):
        """Main loop for verifying replica integrity"""
        while self.running:
            try:
                self._verify_replicas()
                self.stats['last_verification'] = datetime.now().isoformat()
            except Exception as e:
                logger.error(f"Error in verification loop: {e}")
            
            time.sleep(self.verification_interval)
    
    def _check_and_replicate(self):
        """Check for under-replicated files and create new replicas"""
        logger.info("🔍 Checking for under-replicated files...")
        
        # Get all files
        files_data = self.db.list_files(limit=1000)
        files = files_data['files']
        
        active_nodes = self.db.get_active_nodes()
        
        if len(active_nodes) < self.min_replicas:
            logger.warning(f"⚠️  Not enough active nodes ({len(active_nodes)}) for replication")
            return
        
        under_replicated = []
        
        for file in files:
            file_id = file['file_id']
            active_replicas = file.get('active_replicas', 0)
            
            if active_replicas < self.min_replicas:
                under_replicated.append(file)
                logger.warning(f"⚠️  Under-replicated: {file['filename']} ({active_replicas}/{self.min_replicas} replicas)")
        
        self.stats['under_replicated_files'] = len(under_replicated)
        
        # Replicate under-replicated files
        for file in under_replicated:
            try:
                self._replicate_file(file, active_nodes)
            except Exception as e:
                logger.error(f"Failed to replicate {file['filename']}: {e}")
    
    def _replicate_file(self, file, active_nodes):
        """Replicate a file to additional nodes"""
        file_id = file['file_id']
        filename = file['filename']
        
        # Get existing replicas
        replicas = self.db.get_replicas(file_id)
        existing_node_ids = [r['node_id'] for r in replicas if r['status'] == 'active']
        
        # Find nodes that don't have this file
        available_nodes = [
            node for node in active_nodes
            if node['node_id'] not in existing_node_ids
        ]
        
        if not available_nodes:
            logger.warning(f"No available nodes to replicate {filename}")
            return
        
        # Find a source node with the file
        source_node = None
        source_replica = None
        
        for replica in replicas:
            if replica['status'] == 'active':
                # Check if node is still active
                node_active = any(
                    n['node_id'] == replica['node_id'] 
                    for n in active_nodes
                )
                if node_active:
                    source_node = replica['node_address']
                    source_replica = replica
                    break
        
        if not source_node:
            logger.error(f"No active source node found for {filename}")
            return
        
        # Calculate how many more replicas we need
        needed_replicas = self.min_replicas - len(existing_node_ids)
        
        # Select target nodes
        target_nodes = available_nodes[:needed_replicas]
        
        logger.info(f"🔄 Replicating {filename} to {len(target_nodes)} node(s)")
        
        # Perform replication
        for target_node in target_nodes:
            try:
                success = self._copy_file_between_nodes(
                    file_id,
                    source_node,
                    target_node['node_address']
                )
                
                if success:
                    # Add replica record
                    self.db.add_replica(
                        file_id,
                        target_node['node_id'],
                        target_node['node_address'],
                        'active'
                    )
                    
                    self.stats['replications_performed'] += 1
                    logger.info(f"✅ Replicated {filename} to {target_node['node_id']}")
                else:
                    logger.error(f"❌ Failed to replicate {filename} to {target_node['node_id']}")
                    
            except Exception as e:
                logger.error(f"Error replicating to {target_node['node_id']}: {e}")
    
    def _copy_file_between_nodes(self, file_id, source_address, target_address):
        """Copy file from source node to target node"""
        try:
            # Download from source
            response = requests.get(
                f"{source_address}/download/{file_id}",
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to download from source: {response.status_code}")
                return False
            
            file_data = response.content
            
            # Upload to target
            files = {'file': ('replicated_file', file_data)}
            response = requests.post(
                f"{target_address}/upload/{file_id}",
                files=files,
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to upload to target: {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False
    
    def _verify_replicas(self):
        """Verify integrity of all replicas"""
        logger.info("🔍 Verifying replica integrity...")
        
        files_data = self.db.list_files(limit=1000)
        files = files_data['files']
        
        verified = 0
        corrupted = 0
        
        for file in files:
            file_id = file['file_id']
            expected_checksum = file.get('checksum')
            
            if not expected_checksum:
                continue
            
            replicas = self.db.get_replicas(file_id)
            
            for replica in replicas:
                if replica['status'] != 'active':
                    continue
                
                try:
                    # Verify checksum
                    response = requests.get(
                        f"{replica['node_address']}/verify/{file_id}",
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        actual_checksum = data.get('checksum')
                        
                        if actual_checksum == expected_checksum:
                            # Update verification timestamp
                            self.db.update_replica_status(file_id, replica['node_id'], 'active')
                            verified += 1
                        else:
                            # Checksum mismatch - mark as corrupted
                            logger.error(f"❌ Checksum mismatch for {file['filename']} on {replica['node_id']}")
                            self.db.update_replica_status(file_id, replica['node_id'], 'corrupted')
                            corrupted += 1
                    else:
                        # File not found or error
                        logger.warning(f"⚠️  Replica verification failed for {file['filename']} on {replica['node_id']}")
                        
                except Exception as e:
                    logger.error(f"Error verifying replica: {e}")
        
        self.stats['verifications_performed'] += verified
        
        logger.info(f"✅ Verification complete: {verified} verified, {corrupted} corrupted")
    
    def get_stats(self):
        """Get replication manager statistics"""
        return self.stats
    
    def force_check(self):
        """Force immediate replication check"""
        logger.info("🔄 Forcing replication check...")
        self._check_and_replicate()
    
    def force_verification(self):
        """Force immediate verification"""
        logger.info("🔍 Forcing verification...")
        self._verify_replicas()

# Health Monitor for node failure detection
class HealthMonitor:
    def __init__(self, db):
        self.db = db
        self.running = False
        self.check_interval = 10  # Check every 10 seconds
        self.failure_threshold = 30  # Mark as failed after 30 seconds
        
        self.stats = {
            'checks_performed': 0,
            'nodes_failed': 0,
            'nodes_recovered': 0,
            'last_check': None
        }
    
    def start(self):
        """Start health monitor"""
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("✅ Health Monitor started")
    
    def stop(self):
        """Stop health monitor"""
        self.running = False
        logger.info("🛑 Health Monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_node_health()
                self.stats['last_check'] = datetime.now().isoformat()
                self.stats['checks_performed'] += 1
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
            
            time.sleep(self.check_interval)
    
    def _check_node_health(self):
        """Check health of all nodes"""
        nodes = self.db.get_all_nodes()
        current_time = datetime.now()
        
        for node in nodes:
            node_id = node['node_id']
            last_heartbeat = datetime.fromisoformat(node['last_heartbeat'])
            time_diff = (current_time - last_heartbeat).total_seconds()
            
            previous_status = node['status']
            
            if time_diff > self.failure_threshold:
                # Node failed
                if previous_status == 'active':
                    logger.warning(f"💀 Node {node_id} FAILED (no heartbeat for {time_diff:.0f}s)")
                    self.db.mark_node_inactive(node_id)
                    self.stats['nodes_failed'] += 1
                    
                    # Mark all replicas on this node as inactive
                    self._mark_node_replicas_inactive(node_id)
            else:
                # Node is healthy
                if previous_status == 'inactive':
                    logger.info(f"💚 Node {node_id} RECOVERED")
                    self.stats['nodes_recovered'] += 1
    
    def _mark_node_replicas_inactive(self, node_id):
        """Mark all replicas on a failed node as inactive"""
        # This would require a new DB method to get replicas by node
        # For now, we log it
        logger.info(f"Marking replicas on {node_id} as inactive")
    
    def get_stats(self):
        """Get health monitor statistics"""
        return self.stats

# Recovery Manager for automatic recovery
class RecoveryManager:
    def __init__(self, db, replication_manager):
        self.db = db
        self.replication_manager = replication_manager
        self.running = False
        self.check_interval = 60  # Check every minute
        
        self.stats = {
            'recovery_attempts': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'last_recovery': None
        }
    
    def start(self):
        """Start recovery manager"""
        self.running = True
        self.recovery_thread = threading.Thread(
            target=self._recovery_loop,
            daemon=True
        )
        self.recovery_thread.start()
        logger.info("✅ Recovery Manager started")
    
    def stop(self):
        """Stop recovery manager"""
        self.running = False
        logger.info("🛑 Recovery Manager stopped")
    
    def _recovery_loop(self):
        """Main recovery loop"""
        while self.running:
            try:
                self._attempt_recovery()
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")
            
            time.sleep(self.check_interval)
    
    def _attempt_recovery(self):
        """Attempt to recover under-replicated files"""
        logger.info("🔧 Checking for recovery opportunities...")
        
        # Trigger replication check
        self.replication_manager.force_check()
        
        self.stats['recovery_attempts'] += 1
        self.stats['last_recovery'] = datetime.now().isoformat()
    
    def get_stats(self):
        """Get recovery manager statistics"""
        return self.stats
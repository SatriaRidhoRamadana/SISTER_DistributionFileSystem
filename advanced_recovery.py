"""
Advanced Recovery System for DFS
Handles intelligent recovery, disaster recovery, and data restoration
"""

import threading
import time
import requests
import logging
from datetime import datetime, timedelta
from database_schema import DFSDatabase
import json
import os
import hashlib

logger = logging.getLogger(__name__)

class RecoveryStrategy:
    """Different recovery strategies"""
    IMMEDIATE = "immediate"      # Recover immediately
    SCHEDULED = "scheduled"      # Recover during off-peak hours
    PRIORITY = "priority"        # Priority-based recovery
    CONSERVATIVE = "conservative" # Conservative recovery (verify first)

class FileRecoveryRecord:
    """Track file recovery operations"""
    def __init__(self, file_id, filename, strategy, priority=0):
        self.file_id = file_id
        self.filename = filename
        self.strategy = strategy
        self.priority = priority
        self.attempts = 0
        self.max_attempts = 3
        self.last_attempt = None
        self.status = "pending"
        self.error_message = None
        self.created_at = datetime.now()

class AdvancedRecoveryManager:
    """Advanced recovery management with multiple strategies"""
    
    def __init__(self, db, replication_manager):
        self.db = db
        self.replication_manager = replication_manager
        self.running = False
        
        # Recovery queue with priority
        self.recovery_queue = []
        self.queue_lock = threading.Lock()
        
        # Configuration
        self.check_interval = 45  # Check every 45 seconds
        self.max_concurrent_recoveries = 3
        self.retry_delay = 300  # 5 minutes between retries
        
        # Statistics
        self.stats = {
            'total_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'pending_recoveries': 0,
            'average_recovery_time': 0,
            'last_recovery': None,
            'critical_files_recovered': 0,
            'total_data_recovered_mb': 0
        }
        
        # Recovery history
        self.recovery_history = []
        self.max_history = 100
    
    def start(self):
        """Start advanced recovery manager"""
        self.running = True
        
        # Main recovery thread
        self.recovery_thread = threading.Thread(
            target=self._recovery_loop,
            daemon=True
        )
        self.recovery_thread.start()
        
        # Priority recovery thread
        self.priority_thread = threading.Thread(
            target=self._priority_recovery_loop,
            daemon=True
        )
        self.priority_thread.start()
        
        # Health check thread
        self.health_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_thread.start()
        
        logger.info("✅ Advanced Recovery Manager started")
    
    def stop(self):
        """Stop recovery manager"""
        self.running = False
        logger.info("🛑 Advanced Recovery Manager stopped")
    
    def _recovery_loop(self):
        """Main recovery loop"""
        while self.running:
            try:
                self._process_recovery_queue()
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")
            
            time.sleep(self.check_interval)
    
    def _priority_recovery_loop(self):
        """Handle high-priority recoveries immediately"""
        while self.running:
            try:
                self._process_priority_recoveries()
            except Exception as e:
                logger.error(f"Error in priority recovery: {e}")
            
            time.sleep(10)  # Check more frequently
    
    def _health_check_loop(self):
        """Periodic health check and proactive recovery"""
        while self.running:
            try:
                self._proactive_health_check()
            except Exception as e:
                logger.error(f"Error in health check: {e}")
            
            time.sleep(60)  # Check every minute
    
    def _proactive_health_check(self):
        """Proactively check for issues and queue recoveries"""
        logger.info("🔍 Proactive health check...")
        
        # Check for under-replicated files
        files_data = self.db.list_files(limit=1000)
        files = files_data['files']
        
        for file in files:
            active_replicas = file.get('active_replicas', 0)
            
            if active_replicas < 2:
                priority = 10  # High priority
                if active_replicas == 0:
                    priority = 20  # Critical priority
                
                self.add_to_recovery_queue(
                    file['file_id'],
                    file['filename'],
                    strategy=RecoveryStrategy.PRIORITY,
                    priority=priority
                )
        
        # Check for corrupted replicas
        self._check_corrupted_replicas()
    
    def _check_corrupted_replicas(self):
        """Check and queue recovery for corrupted replicas"""
        files_data = self.db.list_files(limit=1000)
        files = files_data['files']
        
        for file in files:
            file_id = file['file_id']
            replicas = self.db.get_replicas(file_id)
            
            corrupted_count = sum(1 for r in replicas if r['status'] == 'corrupted')
            
            if corrupted_count > 0:
                logger.warning(f"Found {corrupted_count} corrupted replicas for {file['filename']}")
                self.add_to_recovery_queue(
                    file_id,
                    file['filename'],
                    strategy=RecoveryStrategy.IMMEDIATE,
                    priority=15
                )
    
    def add_to_recovery_queue(self, file_id, filename, strategy=RecoveryStrategy.IMMEDIATE, priority=0):
        """Add file to recovery queue"""
        with self.queue_lock:
            # Check if already in queue
            if any(r.file_id == file_id for r in self.recovery_queue):
                return
            
            record = FileRecoveryRecord(file_id, filename, strategy, priority)
            self.recovery_queue.append(record)
            
            # Sort by priority (higher first)
            self.recovery_queue.sort(key=lambda x: x.priority, reverse=True)
            
            self.stats['pending_recoveries'] = len(self.recovery_queue)
            
            logger.info(f"📋 Added to recovery queue: {filename} (priority: {priority})")
    
    def _process_recovery_queue(self):
        """Process recovery queue"""
        with self.queue_lock:
            if not self.recovery_queue:
                return
            
            # Get items to process
            to_process = self.recovery_queue[:self.max_concurrent_recoveries]
        
        for record in to_process:
            self._attempt_recovery(record)
    
    def _process_priority_recoveries(self):
        """Process high-priority recoveries immediately"""
        with self.queue_lock:
            priority_items = [r for r in self.recovery_queue if r.priority >= 15]
        
        for record in priority_items:
            self._attempt_recovery(record)
    
    def _attempt_recovery(self, record):
        """Attempt to recover a file"""
        # Check if should retry
        if record.last_attempt:
            time_since_last = (datetime.now() - record.last_attempt).total_seconds()
            if time_since_last < self.retry_delay:
                return
        
        # Check max attempts
        if record.attempts >= record.max_attempts:
            logger.error(f"❌ Max recovery attempts reached for {record.filename}")
            self._mark_recovery_failed(record, "Max attempts exceeded")
            return
        
        record.attempts += 1
        record.last_attempt = datetime.now()
        
        logger.info(f"🔧 Attempting recovery for {record.filename} (attempt {record.attempts}/{record.max_attempts})")
        
        start_time = time.time()
        
        try:
            # Get file info
            file_info = self.db.get_file(record.file_id)
            
            if not file_info:
                self._mark_recovery_failed(record, "File not found in database")
                return
            
            # Get current replicas
            replicas = file_info['replicas']
            active_replicas = [r for r in replicas if r['status'] == 'active']
            corrupted_replicas = [r for r in replicas if r['status'] == 'corrupted']
            
            # Determine recovery action
            if len(active_replicas) == 0:
                # Critical: No active replicas
                success = self._recover_from_backup(record, file_info)
            elif len(active_replicas) < 2:
                # Need more replicas
                success = self._create_additional_replicas(record, file_info, active_replicas)
            elif len(corrupted_replicas) > 0:
                # Replace corrupted replicas
                success = self._replace_corrupted_replicas(record, file_info, corrupted_replicas)
            else:
                # Already healthy
                success = True
            
            if success:
                recovery_time = time.time() - start_time
                self._mark_recovery_successful(record, recovery_time)
            else:
                self._mark_recovery_failed(record, "Recovery operation failed")
                
        except Exception as e:
            logger.error(f"Recovery error for {record.filename}: {e}")
            self._mark_recovery_failed(record, str(e))
    
    def _create_additional_replicas(self, record, file_info, active_replicas):
        """Create additional replicas to meet minimum requirement"""
        file_id = file_info['file_id']
        needed = 2 - len(active_replicas)
        
        logger.info(f"Creating {needed} additional replica(s) for {record.filename}")
        
        # Get available nodes
        active_nodes = self.db.get_active_nodes()
        existing_node_ids = [r['node_id'] for r in active_replicas]
        available_nodes = [n for n in active_nodes if n['node_id'] not in existing_node_ids]
        
        if len(available_nodes) < needed:
            logger.warning(f"Not enough available nodes ({len(available_nodes)} < {needed})")
            return False
        
        # Find source node
        if not active_replicas:
            return False
        
        source_replica = active_replicas[0]
        source_address = source_replica['node_address']
        
        # Create replicas
        success_count = 0
        for i in range(needed):
            if i >= len(available_nodes):
                break
            
            target_node = available_nodes[i]
            
            try:
                # Copy file
                success = self._copy_file_between_nodes(
                    file_id,
                    source_address,
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
                    success_count += 1
                    logger.info(f"✅ Created replica on {target_node['node_id']}")
                    
            except Exception as e:
                logger.error(f"Failed to create replica: {e}")
        
        return success_count > 0
    
    def _replace_corrupted_replicas(self, record, file_info, corrupted_replicas):
        """Replace corrupted replicas with fresh copies"""
        file_id = file_info['file_id']
        
        logger.info(f"Replacing {len(corrupted_replicas)} corrupted replica(s)")
        
        # Get healthy replica as source
        active_replicas = [r for r in file_info['replicas'] if r['status'] == 'active']
        
        if not active_replicas:
            logger.error("No active replica to copy from")
            return False
        
        source_address = active_replicas[0]['node_address']
        
        # Replace each corrupted replica
        for corrupted in corrupted_replicas:
            try:
                # Copy fresh file
                success = self._copy_file_between_nodes(
                    file_id,
                    source_address,
                    corrupted['node_address']
                )
                
                if success:
                    # Update status
                    self.db.update_replica_status(
                        file_id,
                        corrupted['node_id'],
                        'active'
                    )
                    logger.info(f"✅ Replaced corrupted replica on {corrupted['node_id']}")
                    
            except Exception as e:
                logger.error(f"Failed to replace corrupted replica: {e}")
        
        return True
    
    def _recover_from_backup(self, record, file_info):
        """Attempt to recover file from backup (if available)"""
        logger.warning(f"⚠️  No active replicas for {record.filename}")
        logger.info("Attempting backup recovery...")
        
        # Check if we have any inactive replicas that might still have data
        all_replicas = file_info['replicas']
        inactive_replicas = [r for r in all_replicas if r['status'] == 'inactive']
        
        for replica in inactive_replicas:
            try:
                # Try to download from inactive node
                response = requests.get(
                    f"{replica['node_address']}/download/{file_info['file_id']}",
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Found file on inactive node {replica['node_id']}")
                    
                    # Verify checksum
                    file_data = response.content
                    checksum = hashlib.sha256(file_data).hexdigest()
                    
                    if checksum == file_info['checksum']:
                        # File is valid, restore to active nodes
                        return self._restore_from_data(file_info['file_id'], file_data)
                    else:
                        logger.warning(f"Checksum mismatch on {replica['node_id']}")
                        
            except Exception as e:
                logger.debug(f"Could not recover from {replica['node_id']}: {e}")
        
        logger.error(f"❌ Unable to recover {record.filename} - all replicas lost")
        return False
    
    def _restore_from_data(self, file_id, file_data):
        """Restore file from raw data to active nodes"""
        active_nodes = self.db.get_active_nodes()
        
        if len(active_nodes) < 2:
            logger.error("Not enough active nodes for restoration")
            return False
        
        # Upload to 2 nodes
        success_count = 0
        for i in range(min(2, len(active_nodes))):
            node = active_nodes[i]
            
            try:
                files = {'file': ('restored_file', file_data)}
                response = requests.post(
                    f"{node['node_address']}/upload/{file_id}",
                    files=files,
                    timeout=60
                )
                
                if response.status_code == 200:
                    # Add replica record
                    self.db.add_replica(
                        file_id,
                        node['node_id'],
                        node['node_address'],
                        'active'
                    )
                    success_count += 1
                    logger.info(f"✅ Restored to {node['node_id']}")
                    
            except Exception as e:
                logger.error(f"Failed to restore to {node['node_id']}: {e}")
        
        return success_count >= 2
    
    def _copy_file_between_nodes(self, file_id, source_address, target_address):
        """Copy file from source to target node"""
        try:
            # Download from source
            response = requests.get(
                f"{source_address}/download/{file_id}",
                timeout=60
            )
            
            if response.status_code != 200:
                return False
            
            file_data = response.content
            
            # Upload to target
            files = {'file': ('replicated_file', file_data)}
            response = requests.post(
                f"{target_address}/upload/{file_id}",
                files=files,
                timeout=60
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False
    
    def _mark_recovery_successful(self, record, recovery_time):
        """Mark recovery as successful"""
        record.status = "success"
        
        with self.queue_lock:
            if record in self.recovery_queue:
                self.recovery_queue.remove(record)
            
            self.stats['pending_recoveries'] = len(self.recovery_queue)
        
        self.stats['successful_recoveries'] += 1
        self.stats['total_recoveries'] += 1
        self.stats['last_recovery'] = datetime.now().isoformat()
        
        if record.priority >= 15:
            self.stats['critical_files_recovered'] += 1
        
        # Update average recovery time
        total_time = self.stats['average_recovery_time'] * (self.stats['successful_recoveries'] - 1)
        self.stats['average_recovery_time'] = (total_time + recovery_time) / self.stats['successful_recoveries']
        
        # Add to history
        self._add_to_history(record, recovery_time, True)
        
        logger.info(f"✅ Recovery successful for {record.filename} in {recovery_time:.2f}s")
    
    def _mark_recovery_failed(self, record, error):
        """Mark recovery as failed"""
        record.status = "failed"
        record.error_message = error
        
        with self.queue_lock:
            if record in self.recovery_queue:
                self.recovery_queue.remove(record)
            
            self.stats['pending_recoveries'] = len(self.recovery_queue)
        
        self.stats['failed_recoveries'] += 1
        self.stats['total_recoveries'] += 1
        
        # Add to history
        self._add_to_history(record, 0, False)
        
        logger.error(f"❌ Recovery failed for {record.filename}: {error}")
    
    def _add_to_history(self, record, recovery_time, success):
        """Add recovery attempt to history"""
        history_entry = {
            'file_id': record.file_id,
            'filename': record.filename,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'recovery_time': recovery_time,
            'attempts': record.attempts,
            'priority': record.priority,
            'strategy': record.strategy,
            'error': record.error_message if not success else None
        }
        
        self.recovery_history.append(history_entry)
        
        # Keep only recent history
        if len(self.recovery_history) > self.max_history:
            self.recovery_history = self.recovery_history[-self.max_history:]
    
    def get_stats(self):
        """Get recovery statistics"""
        with self.queue_lock:
            pending = len(self.recovery_queue)
        
        return {
            **self.stats,
            'pending_recoveries': pending,
            'queue_size': pending,
            'success_rate': (
                self.stats['successful_recoveries'] / self.stats['total_recoveries'] * 100
                if self.stats['total_recoveries'] > 0 else 0
            )
        }
    
    def get_recovery_queue(self):
        """Get current recovery queue"""
        with self.queue_lock:
            return [
                {
                    'file_id': r.file_id,
                    'filename': r.filename,
                    'priority': r.priority,
                    'attempts': r.attempts,
                    'status': r.status,
                    'strategy': r.strategy
                }
                for r in self.recovery_queue
            ]
    
    def get_recovery_history(self, limit=50):
        """Get recovery history"""
        return self.recovery_history[-limit:]
    
    def force_recovery(self, file_id):
        """Force immediate recovery for specific file"""
        file_info = self.db.get_file(file_id)
        
        if not file_info:
            return False
        
        self.add_to_recovery_queue(
            file_id,
            file_info['filename'],
            strategy=RecoveryStrategy.IMMEDIATE,
            priority=100  # Highest priority
        )
        
        return True
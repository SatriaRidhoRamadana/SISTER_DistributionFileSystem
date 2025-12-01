# Advanced Recovery System Documentation

## 🚀 Overview

Advanced Recovery System adalah lapisan recovery yang intelligent dan otomatis untuk DFS. System ini menggunakan multiple strategies untuk memastikan data availability maksimal.

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────┐
│         Advanced Recovery Manager               │
│  ┌──────────────┬──────────────┬─────────────┐ │
│  │   Priority   │  Intelligent │  Disaster   │ │
│  │   Recovery   │   Strategy   │  Recovery   │ │
│  └──────────────┴──────────────┴─────────────┘ │
└─────────────────────────────────────────────────┘
         ↓                ↓               ↓
    ┌────────┐      ┌─────────┐     ┌──────────┐
    │Recovery│      │Recovery │     │ Health   │
    │ Queue  │      │ History │     │ Monitor  │
    └────────┘      └─────────┘     └──────────┘
```

### Key Features

#### 1. **Priority-Based Recovery**
- Critical files (0 replicas) get highest priority
- High priority (1 replica)
- Normal priority (2+ replicas but corrupted)

#### 2. **Intelligent Strategy Selection**
- **Immediate**: For critical files
- **Scheduled**: For off-peak recovery
- **Priority**: Based on file importance
- **Conservative**: Verify before action

#### 3. **Recovery Queue Management**
- Prioritized queue with configurable max concurrent operations
- Retry mechanism with exponential backoff
- Automatic queue optimization

#### 4. **Disaster Recovery**
- Attempt recovery from inactive nodes
- Restore from backup data
- Multiple recovery paths

---

## 📊 Recovery Strategies

### Strategy 1: Create Additional Replicas

**When**: File has < 2 active replicas

**Process**:
```
1. Identify under-replicated file
2. Find healthy source replica
3. Select available target nodes
4. Copy file to new nodes
5. Update database
6. Verify integrity
```

**Example**:
```python
File: document.pdf
Active Replicas: 1 (node-1)
Needed: 1 more replica

Action:
- Copy from node-1 to node-3
- Create replica record
- Update status to 'active'
Result: 2 active replicas ✅
```

### Strategy 2: Replace Corrupted Replicas

**When**: File has corrupted replicas

**Process**:
```
1. Detect corrupted replica (checksum mismatch)
2. Mark as 'corrupted' in database
3. Find healthy source replica
4. Replace corrupted file
5. Re-verify checksum
6. Update status to 'active'
```

**Example**:
```python
File: image.jpg
Active: 2 replicas
Corrupted: 1 replica (node-2)

Action:
- Copy from node-1 to node-2
- Verify checksum matches
- Mark node-2 as 'active'
Result: All replicas healthy ✅
```

### Strategy 3: Recover from Backup

**When**: All active replicas lost (disaster scenario)

**Process**:
```
1. Check inactive nodes for file
2. Attempt download from each
3. Verify checksum if found
4. Restore to active nodes
5. Create new replica records
```

**Example**:
```python
File: critical.db
Active Replicas: 0 ❌
Inactive Nodes: node-2 (inactive)

Action:
- Try download from node-2
- File found! Checksum valid ✅
- Upload to node-3 and node-4
- Create new replicas
Result: 2 active replicas restored ✅
```

---

## 🎯 Priority System

### Priority Levels

```
Priority 20+  : CRITICAL (0 active replicas)
Priority 15-19: HIGH (1 active replica)
Priority 10-14: MEDIUM (corrupted replicas)
Priority 0-9  : NORMAL (optimization)
```

### Priority Assignment

```python
def calculate_priority(file_info):
    active_replicas = count_active_replicas(file_info)
    corrupted_replicas = count_corrupted_replicas(file_info)
    
    if active_replicas == 0:
        return 20  # Critical
    elif active_replicas == 1:
        return 15  # High
    elif corrupted_replicas > 0:
        return 12  # Medium
    else:
        return 5   # Normal
```

---

## 🔄 Recovery Workflow

### Automatic Recovery Loop

```
Every 45 seconds:
  1. Check recovery queue
  2. Sort by priority (highest first)
  3. Process up to 3 concurrent recoveries
  4. Update statistics
  5. Log results
```

### Priority Recovery Loop

```
Every 10 seconds:
  1. Find priority >= 15 items
  2. Process immediately
  3. Bypass normal queue
  4. Update statistics
```

### Health Check Loop

```
Every 60 seconds:
  1. Proactive health check
  2. Detect under-replicated files
  3. Check for corrupted replicas
  4. Add to recovery queue automatically
```

---

## 📈 Statistics & Monitoring

### Key Metrics

```json
{
  "total_recoveries": 42,
  "successful_recoveries": 40,
  "failed_recoveries": 2,
  "success_rate": 95.2,
  "average_recovery_time": 12.5,
  "critical_files_recovered": 3,
  "pending_recoveries": 0
}
```

### Queue Summary

```json
{
  "total": 5,
  "critical": 1,
  "high": 2,
  "normal": 2
}
```

### Recovery History

```json
{
  "file_id": "abc-123",
  "filename": "important.pdf",
  "timestamp": "2025-11-25T10:30:00",
  "success": true,
  "recovery_time": 15.2,
  "attempts": 1,
  "priority": 20,
  "strategy": "immediate"
}
```

---

## 🛠️ Configuration

### Basic Configuration

```python
# In advanced_recovery.py
class AdvancedRecoveryManager:
    def __init__(self, db, replication_manager):
        self.check_interval = 45              # Main loop interval
        self.max_concurrent_recoveries = 3    # Concurrent operations
        self.retry_delay = 300                # 5 minutes between retries
        self.max_history = 100                # History entries to keep
```

### Tuning for Different Scenarios

#### High Traffic (Production)
```python
check_interval = 30           # Check more frequently
max_concurrent_recoveries = 5 # More concurrent ops
retry_delay = 180            # Retry faster (3 min)
```

#### Low Resources (Development)
```python
check_interval = 60           # Check less frequently
max_concurrent_recoveries = 2 # Fewer concurrent ops
retry_delay = 600            # Retry slower (10 min)
```

#### Critical Systems
```python
check_interval = 15           # Very frequent checks
max_concurrent_recoveries = 10 # Maximum concurrency
retry_delay = 60             # Aggressive retries (1 min)
```

---

## 🔍 API Endpoints

### Get Recovery Stats
```bash
GET /api/recovery/stats

Response:
{
  "stats": {
    "total_recoveries": 42,
    "successful_recoveries": 40,
    "success_rate": 95.2
  },
  "queue_summary": {
    "total": 5,
    "critical": 1
  },
  "recent_history": [...]
}
```

### Get Recovery Queue
```bash
GET /api/recovery/queue

Response:
{
  "queue": [
    {
      "file_id": "abc",
      "filename": "critical.pdf",
      "priority": 20,
      "attempts": 1,
      "status": "pending"
    }
  ]
}
```

### Force Recovery
```bash
POST /api/recovery/force/<file_id>

Response:
{
  "status": "success",
  "message": "Recovery queued"
}
```

### Get Recovery History
```bash
GET /api/recovery/history?limit=50

Response:
{
  "history": [
    {
      "timestamp": "2025-11-25T10:30:00",
      "filename": "file.pdf",
      "success": true,
      "recovery_time": 12.5
    }
  ]
}
```

---

## 🧪 Testing

### Run Advanced Recovery Tests

```bash
python test_advanced_recovery.py

Tests:
1. ✅ Priority-Based Recovery
2. ✅ Disaster Recovery Scenarios
3. ✅ Intelligent Recovery Strategies
4. ✅ Recovery Queue Management
5. ✅ Recovery History Tracking
```

### Manual Testing Scenarios

#### Scenario 1: Priority Recovery

```bash
# 1. Upload file
python dfs_client.py upload critical.pdf

# 2. Simulate loss of replicas
# (stop storage nodes)

# 3. Force recovery
curl -X POST http://localhost:5000/api/recovery/force/<file_id>

# 4. Monitor queue
curl http://localhost:5000/api/recovery/queue

# 5. Check recovery happens
# Watch logs for recovery messages
```

#### Scenario 2: Multiple File Recovery

```bash
# 1. Upload multiple files
for i in {1..5}; do
  python dfs_client.py upload test_$i.pdf
done

# 2. Simulate various issues
# (stop nodes, corrupt files, etc.)

# 3. Wait for automatic recovery
# System detects and recovers automatically

# 4. Check stats
curl http://localhost:5000/api/recovery/stats
```

---

## 📊 Web UI Features

### Recovery Dashboard

**Access**: Click "View Details" button in Recovery Queue panel

**Shows**:
- ✅ Complete recovery statistics
- ✅ Current recovery queue with priorities
- ✅ Recent recovery history
- ✅ Success/failure breakdown
- ✅ Average recovery times

### Real-time Monitoring

Dashboard updates every 5 seconds showing:
- Total recoveries performed
- Success rate percentage
- Pending queue count
- Critical/high priority items

---

## 🎯 Best Practices

### For Development
✅ Set `check_interval = 30` for faster testing  
✅ Monitor logs actively during tests  
✅ Use `force_recovery` for immediate testing  
✅ Check queue and history regularly  

### For Production
✅ Set `check_interval = 45` for balance  
✅ Configure alerting on failed recoveries  
✅ Monitor success rate (should be >95%)  
✅ Review history for patterns  
✅ Keep max_concurrent low to avoid overload  

### For High Availability
✅ Multiple naming services (future)  
✅ External backup integration  
✅ Disaster recovery drills  
✅ Regular integrity checks  

---

## 🚨 Troubleshooting

### Problem: Low success rate

**Possible Causes**:
- Not enough available nodes
- Network issues
- Insufficient storage space

**Solutions**:
1. Add more storage nodes
2. Check network connectivity
3. Clean up space on nodes
4. Review error logs

### Problem: High queue size

**Possible Causes**:
- Too many concurrent failures
- Recovery too slow
- Insufficient resources

**Solutions**:
1. Increase `max_concurrent_recoveries`
2. Add more nodes
3. Reduce `check_interval`
4. Check node performance

### Problem: Failed recoveries

**Check**:
1. Recovery history for error messages
2. Source node availability
3. Target node space
4. File checksums

**Fix**:
1. Manually verify file integrity
2. Force recovery again
3. Check logs for specific errors
4. Ensure nodes are healthy

---

## 📈 Performance Characteristics

### Expected Performance

```
Metric                    | Target    | Typical
--------------------------|-----------|----------
Recovery Detection        | <60s      | 30-45s
Single File Recovery      | <30s      | 15-25s
Concurrent Recoveries     | 3-5       | 3
Success Rate             | >95%      | 97-99%
Queue Processing Time    | <2min     | 1-1.5min
```

### Scalability

```
Configuration              | Max Files  | Recovery/Hour
---------------------------|------------|---------------
Small (2 nodes)           | 100        | 30
Medium (3-5 nodes)        | 500        | 100
Large (5+ nodes)          | 1000+      | 200+
```

---

## 🎓 Advanced Concepts

### 1. Recovery Strategy Selection

System automatically chooses best strategy based on:
- File priority
- Available resources
- Current system load
- Historical success rate

### 2. Adaptive Retry Mechanism

```python
retry_delay = base_delay * (2 ** attempt)
max_delay = 3600  # 1 hour

Example:
Attempt 1: Wait 5 minutes
Attempt 2: Wait 10 minutes
Attempt 3: Wait 20 minutes
```

### 3. Resource Aware Recovery

System monitors:
- Available storage space
- Network bandwidth
- CPU usage
- Active connections

Adjusts recovery rate accordingly.

---

## 🔮 Future Enhancements

Planned features:
- [ ] External backup integration (S3, Google Cloud)
- [ ] Machine learning for pattern detection
- [ ] Predictive failure prevention
- [ ] Cross-datacenter recovery
- [ ] Automated disaster recovery drills
- [ ] Recovery simulation mode
- [ ] Advanced analytics dashboard

---

## 📚 Related Documentation

- [README.md](README.md) - Main documentation
- [recovery_guide.md](recovery_guide.md) - Basic recovery
- [QUICKSTART.md](QUICKSTART.md) - Quick start

---

**🎉 Conclusion**

Advanced Recovery System provides:
✅ Intelligent, priority-based recovery  
✅ Multiple recovery strategies  
✅ Automatic disaster recovery  
✅ Comprehensive monitoring  
✅ High success rates  
✅ Minimal manual intervention  

Your data is safe with DFS Advanced Recovery! 🚀